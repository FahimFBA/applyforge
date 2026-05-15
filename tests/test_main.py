import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

for module_name in ("google", "google.oauth2", "google.oauth2.service_account"):
    sys.modules.pop(module_name, None)

import main


class ProcessJobTests(unittest.TestCase):
    def _build_job(self, **overrides):
        base = dict(
            row_index=2,
            status="not applied",
            company="Acme",
            role="Engineer",
            job_id="JOB-1",
            link="https://example.com/job",
            description="Job description",
            job_full_desc=None,
            resume_type="default",
            will_ai_generate_email_draft_md=True,
            will_ai_generate_email_draft_docs=True,
            will_ai_generate_coverletter_md=True,
            will_ai_generate_coverletter_docs=True,
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def _build_config(self, output_dir: Path):
        return SimpleNamespace(
            status_processing="processing",
            status_draft_generated="draft generated",
            resumes_dir=Path("resumes"),
            output_dir=output_dir,
        )

    def test_process_job_generates_only_requested_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir))
            job = self._build_job(
                will_ai_generate_email_draft_md=False,
                will_ai_generate_email_draft_docs=True,
                will_ai_generate_coverletter_md=True,
                will_ai_generate_coverletter_docs=False,
            )
            sheets = Mock()
            drive = Mock()
            openai = Mock()
            scraper = Mock()
            logger = Mock()
            openai.generate.side_effect = ["cover body", "email body"]

            with patch("main.load_resume_profile", return_value="resume profile"), patch(
                "main.save_markdown"
            ) as save_markdown, patch("main.save_docx") as save_docx:
                main.process_job(job, config, sheets, drive, openai, scraper, logger)

            self.assertEqual(openai.generate.call_count, 2)
            save_markdown.assert_called_once()
            self.assertIn("cover body", save_markdown.call_args.args[0])
            self.assertEqual(save_markdown.call_args.args[1].name, "Acme_JOB-1_cover_letter.md")

            save_docx.assert_called_once()
            self.assertEqual(save_docx.call_args.kwargs["content"], "email body")
            self.assertEqual(save_docx.call_args.kwargs["file_path"].name, "Acme_JOB-1_recruiter_email.docx")

            uploaded_names = [call_args.kwargs["company_name"] for call_args in drive.upload_file.call_args_list]
            self.assertEqual(uploaded_names, ["Acme", "Acme"])
            uploaded_files = [call_args.args[0].name for call_args in drive.upload_file.call_args_list]
            self.assertEqual(
                uploaded_files,
                ["Acme_JOB-1_recruiter_email.docx", "Acme_JOB-1_cover_letter.md"],
            )
            sheets.update_status.assert_has_calls(
                [call(2, "processing"), call(2, "draft generated")]
            )

    def test_process_job_uses_valid_job_full_desc_without_scraping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir))
            job = self._build_job(
                description=None,
                job_full_desc="one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty",
            )
            sheets = Mock()
            drive = Mock()
            openai = Mock()
            scraper = Mock()
            logger = Mock()
            openai.generate.side_effect = ["cover body", "email body"]

            with patch("main.load_resume_profile", return_value="resume profile"), patch(
                "main.save_markdown"
            ), patch("main.save_docx"):
                main.process_job(job, config, sheets, drive, openai, scraper, logger)

            scraper.fetch_job_description.assert_not_called()

    def test_process_job_ignores_short_job_full_desc_and_scrapes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir))
            job = self._build_job(
                description=None,
                job_full_desc="too short for full desc",
            )
            sheets = Mock()
            drive = Mock()
            openai = Mock()
            scraper = Mock()
            logger = Mock()
            openai.generate.side_effect = ["cover body", "email body"]
            scraper.fetch_job_description.return_value = "scraped description"

            with patch("main.load_resume_profile", return_value="resume profile"), patch(
                "main.save_markdown"
            ), patch("main.save_docx"):
                main.process_job(job, config, sheets, drive, openai, scraper, logger)

            scraper.fetch_job_description.assert_called_once_with("https://example.com/job")

    def test_process_job_skips_ai_when_all_output_flags_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir))
            job = self._build_job(
                will_ai_generate_email_draft_md=False,
                will_ai_generate_email_draft_docs=False,
                will_ai_generate_coverletter_md=False,
                will_ai_generate_coverletter_docs=False,
            )
            sheets = Mock()
            drive = Mock()
            openai = Mock()
            scraper = Mock()
            logger = Mock()

            with patch("main.load_resume_profile", return_value="resume profile"), patch(
                "main.save_markdown"
            ) as save_markdown, patch("main.save_docx") as save_docx:
                main.process_job(job, config, sheets, drive, openai, scraper, logger)

            openai.generate.assert_not_called()
            save_markdown.assert_not_called()
            save_docx.assert_not_called()
            drive.upload_file.assert_not_called()
            sheets.update_status.assert_has_calls(
                [call(2, "processing"), call(2, "draft generated")]
            )


if __name__ == "__main__":
    unittest.main()
