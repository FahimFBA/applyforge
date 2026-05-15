"""
scripts/process_resume.py
==========================
One-time resume preprocessing pipeline.

What it does
------------
1. Reads every PDF from ``raw_resumes/``.
2. Extracts raw text using PyMuPDF.
3. Calls OpenAI to generate a compact, structured resume profile.
4. Saves the profile as a plain-text file in ``resumes/``.

The resulting ``resumes/*.txt`` files are then used by the main automation
instead of raw PDFs — reducing token usage by ~75 % per job application.

When to run
-----------
* Once when you add or update a resume PDF.
* Not needed on every GitHub Actions run (profiles are committed to the repo
  or persisted elsewhere).

File naming convention
----------------------
The output filename mirrors the PDF stem (lowercased, spaces → underscores):
    raw_resumes/Backend Developer.pdf  →  resumes/backend_developer.txt

Recommended: rename PDFs to match your resume_type column values:
    raw_resumes/backend.pdf   →  resumes/backend.txt
    raw_resumes/ai.pdf        →  resumes/ai.txt
    raw_resumes/default.pdf   →  resumes/default.txt

Usage
-----
    # From project root with virtualenv active:
    python scripts/process_resume.py

Prerequisites
-------------
    OPENAI_API_KEY must be set (in .env or environment).
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---- Ensure project root is on sys.path so ``services.*`` imports work ----
# This is necessary when running the script directly (not as a module).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

# Load .env before importing services that read env vars at import time
load_dotenv(_PROJECT_ROOT / ".env")

from services.config import get_config
from services.logger import setup_logger
from services.openai_client import OpenAIClient
from services.prompts import RESUME_OPTIMIZER_SYSTEM, RESUME_OPTIMIZER_USER
from services.resume_optimizer import extract_pdf_text

logger = setup_logger(__name__)


# ======================================================================== #
# Core processing function                                                   #
# ======================================================================== #

def process_resume(pdf_path: Path, output_dir: Path, client: OpenAIClient) -> None:
    """
    Extract, optimize, and save a single resume PDF.

    Parameters
    ----------
    pdf_path:
        Path to the source PDF file.
    output_dir:
        Directory where the optimized .txt profile will be saved (``resumes/``).
    client:
        Initialized OpenAI client for the optimization call.
    """
    logger.info(f"Processing: {pdf_path.name}")

    # --- Step 1: Extract raw text from PDF ---
    raw_text = extract_pdf_text(pdf_path)
    if not raw_text.strip():
        logger.warning(f"No extractable text in '{pdf_path.name}' — is it image-only? Skipping.")
        return

    logger.debug(f"Extracted {len(raw_text)} chars from '{pdf_path.name}'")

    # Truncate to ~6 000 chars before sending to OpenAI to stay within token budget.
    # A typical 2-page resume is well under this limit.
    truncated_text = raw_text[:6_000]

    # --- Step 2: Send to OpenAI for structured compression ---
    user_prompt = RESUME_OPTIMIZER_USER.format(resume_text=truncated_text)

    optimized_profile = client.generate(
        system_prompt=RESUME_OPTIMIZER_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.3,   # low temperature → consistent, structured output
        max_tokens=600,
    )

    if not optimized_profile.strip():
        logger.warning(f"OpenAI returned empty profile for '{pdf_path.name}' — skipping save")
        return

    # --- Step 3: Save the optimized profile ---
    # Filename mirrors the PDF stem (lowercase, spaces → underscores)
    stem = pdf_path.stem.lower().replace(" ", "_")
    output_path = output_dir / f"{stem}.txt"
    output_path.write_text(optimized_profile, encoding="utf-8")

    token_estimate_raw = len(raw_text.split())
    token_estimate_opt = len(optimized_profile.split())
    reduction_pct = round((1 - token_estimate_opt / max(token_estimate_raw, 1)) * 100)

    logger.info(
        f"Saved: {output_path.name} | "
        f"~{token_estimate_raw} words → ~{token_estimate_opt} words "
        f"({reduction_pct}% reduction)"
    )


# ======================================================================== #
# Entry point                                                                #
# ======================================================================== #

def main() -> None:
    """
    Scan raw_resumes/ for PDFs and process each one.

    Errors on individual files are logged and skipped — the script continues
    processing remaining files rather than aborting on the first failure.
    """
    config = get_config()
    client = OpenAIClient(config)

    pdf_files = sorted(config.raw_resumes_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in '{config.raw_resumes_dir}/'")
        print(
            "\nNothing to process.\n"
            f"Place your PDF resume(s) in: {config.raw_resumes_dir.resolve()}/\n"
            "Then re-run this script."
        )
        return

    logger.info(f"Found {len(pdf_files)} PDF(s) to process")

    succeeded = 0
    failed = 0

    for pdf_path in pdf_files:
        try:
            process_resume(pdf_path, config.resumes_dir, client)
            succeeded += 1
        except Exception as exc:
            logger.error(f"Failed to process '{pdf_path.name}': {exc}", exc_info=True)
            failed += 1

    print(
        f"\nResume processing complete.\n"
        f"  Succeeded : {succeeded}\n"
        f"  Failed    : {failed}\n"
        f"  Output dir: {config.resumes_dir.resolve()}/\n"
    )


if __name__ == "__main__":
    main()
