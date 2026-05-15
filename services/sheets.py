"""
services/sheets.py
==================
Google Sheets integration for the applyforge project.

Responsibilities
----------------
* Authenticate with Google Sheets API using a service-account JSON secret.
* Read all rows and return those whose ``status`` matches an allowed value.
* Update individual row status cells with exponential-backoff retry.

Expected spreadsheet columns (order-independent, matched by header name):
    status | company | role | job_id | link | description | job_full_desc | resume_type
    | will_ai_generate_email_draft_md | will_ai_generate_email_draft_docs
    | will_ai_generate_coverletter_md | will_ai_generate_coverletter_docs

Usage
-----
    from services.sheets import SheetsService
    from services.config import get_config

    svc = SheetsService(get_config())
    jobs = svc.get_pending_jobs()
    svc.update_status(row_index=3, status="processing")
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

from services.config import Config
from services.logger import setup_logger
from utils.constants import (
    COL_COMPANY,
    COL_COVERLETTER_DOCS,
    COL_COVERLETTER_MD,
    COL_DESCRIPTION,
    COL_EMAIL_DRAFT_DOCS,
    COL_EMAIL_DRAFT_MD,
    COL_JOB_FULL_DESC,
    COL_JOB_ID,
    COL_LINK,
    COL_RESUME_TYPE,
    COL_ROLE,
    COL_STATUS,
    FLAG_NO,
    FLAG_YES,
    RESUME_TYPE_DEFAULT,
)

# OAuth scopes required for read + write access to Sheets (and Drive for auth)
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

logger = setup_logger(__name__)


@dataclass
class JobRow:
    """
    Immutable data transfer object representing one spreadsheet row.

    Attributes
    ----------
    row_index:
        1-based row index in the sheet (row 1 = header, row 2 = first data row).
        Used to call update_cell() without re-fetching the entire sheet.
    status:
        Raw status string from the sheet (e.g. "not applied").
    company:
        Hiring company name.
    role:
        Job title / role being applied for.
    job_id:
        Unique identifier for the posting (used in output file names).
    link:
        URL of the job posting — scraped when ``description`` is empty.
    description:
        Optional pre-filled job description.  When None the scraper fetches it.
    job_full_desc:
        Optional complete job description from spreadsheet. When sufficiently
        detailed, this should be used instead of visiting the job link.
    resume_type:
        Key that maps to an optimized resume profile in resumes/ (e.g. "backend").
    will_ai_generate_email_draft_md:
        Whether to save recruiter email as Markdown.
    will_ai_generate_email_draft_docs:
        Whether to save recruiter email as DOCX.
    will_ai_generate_coverletter_md:
        Whether to save cover letter as Markdown.
    will_ai_generate_coverletter_docs:
        Whether to save cover letter as DOCX.
    """

    row_index: int
    status: str
    company: str
    role: str
    job_id: str
    link: str
    description: Optional[str]
    job_full_desc: Optional[str]
    resume_type: str
    will_ai_generate_email_draft_md: bool
    will_ai_generate_email_draft_docs: bool
    will_ai_generate_coverletter_md: bool
    will_ai_generate_coverletter_docs: bool


class SheetsService:
    """
    Thin wrapper around the gspread client for this project's specific needs.

    The service authenticates lazily on first use so that import-time errors
    (e.g. bad JSON) surface during the actual operation, not at module load.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._client: Optional[gspread.Client] = None
        self._sheet: Optional[gspread.Worksheet] = None

    # ------------------------------------------------------------------ #
    # Authentication                                                       #
    # ------------------------------------------------------------------ #

    def _build_credentials(self) -> Credentials:
        """
        Parse the GOOGLE_SERVICE_ACCOUNT secret and return OAuth2 credentials.

        The secret is a full service-account JSON stored as a single string
        (never as a file on disk) so it is safe to pass via GitHub Secrets.
        """
        sa_info = json.loads(self.config.google_service_account)
        return Credentials.from_service_account_info(sa_info, scopes=_SCOPES)

    def connect(self) -> None:
        """Open the configured spreadsheet and cache the first worksheet."""
        creds = self._build_credentials()
        self._client = gspread.authorize(creds)
        spreadsheet = self._client.open_by_key(self.config.google_sheet_id)
        # Always work on the first (leftmost) sheet
        self._sheet = spreadsheet.sheet1
        logger.info(f"Connected to Google Sheet ID: '{self.config.google_sheet_id}'")

    def _ensure_connected(self) -> None:
        """Connect on first use (lazy initialisation pattern)."""
        if self._sheet is None:
            self.connect()

    # ------------------------------------------------------------------ #
    # Read operations                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_yes_no_flag(record: dict, column_name: str) -> bool:
        """
        Parse spreadsheet yes/no flag with blank defaulting to ``True``.

        Supported values are case-insensitive ``yes`` and ``no``.
        Any unexpected value is treated as ``True`` to preserve current
        generate-by-default behaviour.
        """
        raw_value = str(record.get(column_name, "")).strip().lower()
        if not raw_value:
            return True
        if raw_value == FLAG_YES:
            return True
        if raw_value == FLAG_NO:
            return False

        logger.warning(
            f"Unexpected value '{record.get(column_name)}' in column '{column_name}' "
            "— defaulting to 'yes'"
        )
        return True

    @staticmethod
    def _normalize_optional_text(record: dict, column_name: str) -> Optional[str]:
        """Return stripped cell text or ``None`` when blank."""
        return str(record.get(column_name, "")).strip() or None

    def get_pending_jobs(self) -> list[JobRow]:
        """
        Fetch all rows whose status is in ``config.allowed_statuses``.

        Returns
        -------
        list[JobRow]
            At most ``config.max_jobs_per_run`` rows, preserving sheet order.
        """
        self._ensure_connected()

        # get_all_records() returns a list of dicts keyed by the header row
        records = self._sheet.get_all_records()
        jobs: list[JobRow] = []

        for i, record in enumerate(records, start=2):  # row 2 = first data row (header is row 1)
            raw_status = str(record.get("status", "")).strip().lower()
            allowed = [s.lower() for s in self.config.allowed_statuses]

            if raw_status not in allowed:
                continue

            jobs.append(
                JobRow(
                    row_index=i,
                    status=str(record.get(COL_STATUS, "")).strip(),
                    company=str(record.get(COL_COMPANY, "")).strip(),
                    role=str(record.get(COL_ROLE, "")).strip(),
                    job_id=str(record.get(COL_JOB_ID, "")).strip(),
                    link=str(record.get(COL_LINK, "")).strip(),
                    description=self._normalize_optional_text(record, COL_DESCRIPTION),
                    job_full_desc=self._normalize_optional_text(record, COL_JOB_FULL_DESC),
                    resume_type=(
                        str(record.get(COL_RESUME_TYPE, "")).strip().lower()
                        or RESUME_TYPE_DEFAULT
                    ),
                    will_ai_generate_email_draft_md=self._parse_yes_no_flag(
                        record, COL_EMAIL_DRAFT_MD
                    ),
                    will_ai_generate_email_draft_docs=self._parse_yes_no_flag(
                        record, COL_EMAIL_DRAFT_DOCS
                    ),
                    will_ai_generate_coverletter_md=self._parse_yes_no_flag(
                        record, COL_COVERLETTER_MD
                    ),
                    will_ai_generate_coverletter_docs=self._parse_yes_no_flag(
                        record, COL_COVERLETTER_DOCS
                    ),
                )
            )

        logger.info(f"Found {len(jobs)} pending job(s) in sheet")

        # Honour the per-run cap to avoid runaway API spend
        return jobs[: self.config.max_jobs_per_run]

    # ------------------------------------------------------------------ #
    # Write operations                                                     #
    # ------------------------------------------------------------------ #

    def update_status(self, row_index: int, status: str) -> None:
        """
        Write a new status value to the ``status`` column of a specific row.

        Uses exponential backoff (1 s, 2 s, 4 s …) on Sheets API errors.

        Parameters
        ----------
        row_index:
            1-based row number (as stored in JobRow.row_index).
        status:
            New status string, e.g. "processing" or "draft generated".
        """
        self._ensure_connected()

        # Locate the status column dynamically so column order doesn't matter
        header = self._sheet.row_values(1)
        try:
            status_col = header.index(COL_STATUS) + 1  # gspread uses 1-based column indices
        except ValueError:
            logger.error(f"Column '{COL_STATUS}' not found in sheet header row — cannot update")
            return

        retries = self.config.google_retries
        for attempt in range(retries):
            try:
                self._sheet.update_cell(row_index, status_col, status)
                logger.info(f"Row {row_index} → status='{status}'")
                return
            except APIError as exc:
                if attempt < retries - 1:
                    wait = 2 ** attempt  # 1 s, 2 s, 4 s
                    logger.warning(
                        f"Sheets API error on update (attempt {attempt + 1}/{retries}), "
                        f"retrying in {wait}s: {exc}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"Failed to update row {row_index} after {retries} attempts: {exc}"
                    )
                    raise
