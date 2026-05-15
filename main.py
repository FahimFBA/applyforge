"""
main.py
=======
ApplyForge — Automated Email & Cover Letter Generator

Entry point for the daily GitHub Actions workflow.

Automation flow
---------------
1.  Load configuration and validate required secrets.
2.  Connect to Google Sheets and fetch rows with status "not applied".
3.  For each job (up to MAX_JOBS_PER_RUN):
    a.  Mark row as "processing".
    b.  Scrape job description from the link if none is in the sheet.
    c.  Load the matching optimized resume profile from resumes/.
    d.  Generate recruiter email / cover letter only when that row requests them.
    e.  Save requested outputs as .md and/or .docx.
    f.  Upload generated files to Google Drive under Applications/<Company>/.
    g.  Mark row as "draft generated".
4.  On any per-job failure: mark as "failed", log the error, continue.
5.  Log a final summary of successes and failures.

Environment
-----------
All configuration is read from environment variables (see example.env).
Local development: copy example.env → .env and fill in values.
CI/CD: set via GitHub Actions Secrets and Variables.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing services so env vars are available at import time
load_dotenv(Path(__file__).parent / ".env")

from services.config import get_config
from services.document_generator import build_output_paths, save_docx, save_markdown
from services.drive import DriveService
from services.logger import setup_logger
from services.openai_client import OpenAIClient
from services.prompts import (
    COVER_LETTER_SYSTEM,
    COVER_LETTER_USER,
    RECRUITER_EMAIL_SYSTEM,
    RECRUITER_EMAIL_USER,
)
from services.resume_optimizer import load_resume_profile
from services.scraper import ScraperService
from services.sheets import JobRow, SheetsService
from utils.constants import (
    JD_CHAR_LIMIT_COVER_LETTER,
    JD_CHAR_LIMIT_EMAIL,
    JOB_FULL_DESC_MIN_WORDS,
)

# ======================================================================== #
# Per-job processing                                                         #
# ======================================================================== #


def _has_minimum_word_count(text: str | None, minimum_words: int = JOB_FULL_DESC_MIN_WORDS) -> bool:
    """Return ``True`` when text contains at least ``minimum_words`` words."""
    if not text:
        return False
    return len(text.split()) >= minimum_words

def process_job(
    job: JobRow,
    config,
    sheets: SheetsService,
    drive: DriveService,
    openai: OpenAIClient,
    scraper: ScraperService,
    logger,
) -> None:
    """
    Process a single job application end-to-end.

    Marks the row "processing" at the start and "draft generated" on success.
    Raises on failure so the caller can mark the row "failed" and continue.

    Parameters
    ----------
    job:
        Data from one spreadsheet row.
    config:
        Project configuration singleton.
    sheets, drive, openai, scraper:
        Initialized service instances (injected for testability).
    logger:
        Named logger from the calling context.
    """
    logger.info(
        f"--- Processing: {job.company} | {job.role} | ID: {job.job_id or 'N/A'} ---"
    )

    # ---- Step 1: Mark as processing so concurrent runs skip this row ----
    sheets.update_status(job.row_index, config.status_processing)

    # ---- Step 2: Resolve job description ----
    if _has_minimum_word_count(job.job_full_desc):
        logger.info("Using job_full_desc from spreadsheet; skipping scraping")
        job_description = job.job_full_desc
    else:
        if job.job_full_desc:
            logger.info("job_full_desc present but under 20 words; falling back to normal resolution")
        job_description = job.description

        if not job_description:
            if not job.link:
                logger.warning(
                    f"Row {job.row_index}: no description and no link — "
                    f"using minimal fallback context"
                )
                job_description = f"Role: {job.role} at {job.company}."
            else:
                logger.info(f"Description missing — scraping: {job.link}")
                job_description = scraper.fetch_job_description(job.link)

                if not job_description:
                    # Scrape failed — use a minimal stub so generation still runs
                    logger.warning(
                        f"Scrape failed for {job.company} — using fallback description"
                    )
                    job_description = (
                        f"Role: {job.role} at {job.company}. "
                        f"See full details at: {job.link}"
                    )

    # ---- Step 3: Load optimized resume profile ----
    # Truncating is not needed here — optimized profiles are already compact
    resume_profile = load_resume_profile(config.resumes_dir, job.resume_type)

    should_generate_email = (
        job.will_ai_generate_email_draft_md or job.will_ai_generate_email_draft_docs
    )
    should_generate_cover_letter = (
        job.will_ai_generate_coverletter_md or job.will_ai_generate_coverletter_docs
    )

    recruiter_email: str | None = None
    cover_letter: str | None = None

    # ---- Step 4: Generate requested content via OpenAI ----
    if should_generate_cover_letter:
        logger.info("Generating cover letter...")
        cover_letter = openai.generate(
            system_prompt=COVER_LETTER_SYSTEM.format(resume_profile=resume_profile),
            user_prompt=COVER_LETTER_USER.format(
                company=job.company,
                role=job.role,
                # Cap JD to 4 000 chars to stay within a sensible context budget
                job_description=job_description[:JD_CHAR_LIMIT_COVER_LETTER],
            ),
            max_tokens=600,
        )
    else:
        logger.info("Skipping cover letter generation for this row")

    if should_generate_email:
        logger.info("Generating recruiter email...")
        recruiter_email = openai.generate(
            system_prompt=RECRUITER_EMAIL_SYSTEM.format(resume_profile=resume_profile),
            user_prompt=RECRUITER_EMAIL_USER.format(
                company=job.company,
                role=job.role,
                # Slightly shorter cap for the email — it needs less JD context
                job_description=job_description[:JD_CHAR_LIMIT_EMAIL],
            ),
            max_tokens=400,
        )
    else:
        logger.info("Skipping recruiter email generation for this row")

    generated_file_keys: list[str] = []

    if should_generate_email or should_generate_cover_letter:
        # ---- Step 5: Build output file paths ----
        paths = build_output_paths(config.output_dir, job.company, job.job_id)

        # ---- Step 6: Save requested files ----
        if recruiter_email is not None:
            email_md_content = (
                f"# Recruiter Email — {job.company}\n"
                f"**Role:** {job.role}  \n"
                f"**Job ID:** {job.job_id or 'N/A'}  \n"
                f"**Link:** {job.link or 'N/A'}\n\n"
                f"---\n\n"
                f"{recruiter_email}"
            )
            if job.will_ai_generate_email_draft_md:
                save_markdown(email_md_content, paths["email_md"])
                generated_file_keys.append("email_md")
            if job.will_ai_generate_email_draft_docs:
                save_docx(
                    content=recruiter_email,
                    file_path=paths["email_docx"],
                    title=f"Recruiter Email — {job.role} at {job.company}",
                )
                generated_file_keys.append("email_docx")

        if cover_letter is not None:
            cover_md_content = (
                f"# Cover Letter — {job.company}\n"
                f"**Role:** {job.role}  \n"
                f"**Job ID:** {job.job_id or 'N/A'}  \n"
                f"**Link:** {job.link or 'N/A'}\n\n"
                f"---\n\n"
                f"{cover_letter}"
            )
            if job.will_ai_generate_coverletter_md:
                save_markdown(cover_md_content, paths["cover_letter_md"])
                generated_file_keys.append("cover_letter_md")
            if job.will_ai_generate_coverletter_docs:
                save_docx(
                    content=cover_letter,
                    file_path=paths["cover_letter_docx"],
                    title=f"Cover Letter — {job.role} at {job.company}",
                )
                generated_file_keys.append("cover_letter_docx")

        # ---- Step 7: Upload generated files to Google Drive ----
        if generated_file_keys:
            logger.info(f"Uploading files to Drive → Applications/{job.company}/")
            for key in generated_file_keys:
                drive.upload_file(paths[key], company_name=job.company)
    else:
        logger.info("Row requests no AI-generated output files")

    # ---- Step 8: Mark as done ----
    sheets.update_status(job.row_index, config.status_draft_generated)
    logger.info(f"Done: {job.company} | {job.role}")


# ======================================================================== #
# Entry point                                                                #
# ======================================================================== #

def main() -> None:
    """
    Main automation entry point.

    Orchestrates the full workflow:
    fetch → process each job → handle failures → summarize.
    """
    config = get_config()

    # Validate required secrets early — fail fast with a clear message
    try:
        config.validate()
    except ValueError as exc:
        print(f"[FATAL] Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger("main", log_level=config.log_level, logs_dir=config.logs_dir)
    logger.info("=" * 60)
    logger.info("ApplyForge starting")
    logger.info(f"Model: {config.openai_model} | Max jobs: {config.max_jobs_per_run}")
    logger.info("=" * 60)

    # ---- Initialize services ----
    sheets = SheetsService(config)
    drive = DriveService(config)
    openai = OpenAIClient(config)
    scraper = ScraperService(config)

    # ---- Fetch pending jobs ----
    try:
        pending_jobs = sheets.get_pending_jobs()
    except Exception as exc:
        logger.error(f"Failed to fetch jobs from Google Sheets: {exc}", exc_info=True)
        sys.exit(1)

    if not pending_jobs:
        logger.info("No pending jobs found — exiting cleanly")
        return

    logger.info(f"Processing {len(pending_jobs)} job(s)")

    # ---- Process each job ----
    succeeded = 0
    failed = 0

    for job in pending_jobs:
        try:
            process_job(job, config, sheets, drive, openai, scraper, logger)
            succeeded += 1
        except Exception as exc:
            logger.error(
                f"Job failed [{job.company} | {job.role}]: {exc}",
                exc_info=True,
            )
            # Best-effort status update — don't let a secondary failure mask the primary one
            try:
                sheets.update_status(job.row_index, config.status_failed)
            except Exception as update_exc:
                logger.warning(f"Could not mark row {job.row_index} as failed: {update_exc}")
            failed += 1

        # Rate limit: pause between jobs to reduce burst API pressure
        if pending_jobs.index(job) < len(pending_jobs) - 1:
            time.sleep(config.rate_limit_delay)

    # ---- Final summary ----
    logger.info("=" * 60)
    logger.info(
        f"Run complete | Succeeded: {succeeded} | Failed: {failed} | "
        f"Total: {len(pending_jobs)}"
    )
    logger.info("=" * 60)

    # Exit with non-zero code if any job failed (useful for GitHub Actions alerts)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
