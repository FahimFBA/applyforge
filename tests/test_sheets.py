import importlib
import sys
import types
import unittest
from types import SimpleNamespace

fake_gspread = types.ModuleType("gspread")
fake_gspread.Client = object
fake_gspread.Worksheet = object
fake_gspread.authorize = lambda creds: None
sys.modules.setdefault("gspread", fake_gspread)

fake_gspread_exceptions = types.ModuleType("gspread.exceptions")
fake_gspread_exceptions.APIError = Exception
sys.modules.setdefault("gspread.exceptions", fake_gspread_exceptions)

fake_google = types.ModuleType("google")
fake_google_oauth2 = types.ModuleType("google.oauth2")
fake_google_service_account = types.ModuleType("google.oauth2.service_account")


class FakeCredentials:
    @classmethod
    def from_service_account_info(cls, info, scopes=None):
        return cls()


fake_google_service_account.Credentials = FakeCredentials
sys.modules.setdefault("google", fake_google)
sys.modules.setdefault("google.oauth2", fake_google_oauth2)
sys.modules.setdefault("google.oauth2.service_account", fake_google_service_account)

sheets_module = importlib.import_module("services.sheets")
SheetsService = sheets_module.SheetsService


class FakeSheet:
    def __init__(self, records):
        self._records = records

    def get_all_records(self):
        return self._records


class SheetsServiceTests(unittest.TestCase):
    def test_get_pending_jobs_parses_yes_no_flags_and_defaults_blank_to_yes(self) -> None:
        config = SimpleNamespace(
            google_service_account="{}",
            google_sheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
            allowed_statuses=["not applied"],
            max_jobs_per_run=10,
        )
        service = SheetsService(config)
        service._sheet = FakeSheet(
            [
                {
                    "status": "not applied",
                    "company": "Acme",
                    "role": "Engineer",
                    "job_id": "JOB-1",
                    "link": "https://example.com/job",
                    "description": "",
                    "job_full_desc": "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty",
                    "resume_type": "backend",
                    "will_ai_generate_email_draft_md": "",
                    "will_ai_generate_email_draft_docs": "no",
                    "will_ai_generate_coverletter_md": "yes",
                    "will_ai_generate_coverletter_docs": "",
                }
            ]
        )

        jobs = service.get_pending_jobs()

        self.assertEqual(len(jobs), 1)
        self.assertIsNotNone(jobs[0].job_full_desc)
        self.assertTrue(jobs[0].will_ai_generate_email_draft_md)
        self.assertFalse(jobs[0].will_ai_generate_email_draft_docs)
        self.assertTrue(jobs[0].will_ai_generate_coverletter_md)
        self.assertTrue(jobs[0].will_ai_generate_coverletter_docs)


if __name__ == "__main__":
    unittest.main()
