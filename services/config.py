"""
services/config.py
==================
Centralized configuration management for the applyforge project.

All tuneable values are read from environment variables so that behaviour can
be changed via GitHub Actions Variables / Secrets or a local .env file without
touching any business-logic code.

Usage
-----
    from services.config import get_config

    cfg = get_config()          # returns a singleton Config instance
    cfg.validate()              # raises ValueError if required secrets are missing
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from utils.constants import (
    STATUS_DRAFT_GENERATED,
    STATUS_FAILED,
    STATUS_NOT_APPLIED,
    STATUS_PROCESSING,
)


@dataclass
class Config:
    """
    Single source of truth for every configurable value in the project.

    Environment variables → dataclass fields (with sensible defaults).
    Call validate() early in main() to surface missing secrets fast.
    """

    # ------------------------------------------------------------------ #
    # Required secrets — no defaults; must be supplied at runtime         #
    # ------------------------------------------------------------------ #
    openai_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    google_service_account: str = field(
        # Full JSON of the GCP service-account key, stored as a single secret
        default_factory=lambda: os.environ.get("GOOGLE_SERVICE_ACCOUNT", "")
    )

    # ------------------------------------------------------------------ #
    # Google Workspace targets                                            #
    # ------------------------------------------------------------------ #
    google_sheet_id: str = field(
        # Spreadsheet ID from the URL: docs.google.com/spreadsheets/d/<ID>/edit
        default_factory=lambda: os.environ.get("GOOGLE_SHEET_ID", "")
    )
    google_drive_parent_folder: str = field(
        # Top-level Drive folder name (used only if google_drive_folder_id is not set)
        default_factory=lambda: os.environ.get("GOOGLE_DRIVE_PARENT_FOLDER", "Applications")
    )
    google_drive_folder_id: str = field(
        # Preferred: explicit folder ID from Drive URL.
        # Get it from the URL: drive.google.com/drive/folders/<ID>
        default_factory=lambda: os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
    )

    # ------------------------------------------------------------------ #
    # OAuth2 user credentials (preferred over service account for Drive)  #
    # ------------------------------------------------------------------ #
    # When these three are set, Drive uploads run as the real Google user.
    # Files are owned by the user → charged to user's Drive quota → no 403.
    # Generate once with: python scripts/generate_refresh_token.py
    google_oauth_client_id: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    )
    google_oauth_client_secret: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    )
    google_oauth_refresh_token: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
    )

    # ------------------------------------------------------------------ #
    # OpenAI generation settings                                          #
    # ------------------------------------------------------------------ #
    openai_model: str = field(
        # gpt-4o-mini keeps costs low while maintaining quality
        default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    )
    openai_temperature: float = field(
        default_factory=lambda: float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
    )

    # ------------------------------------------------------------------ #
    # Scheduling metadata (informational; actual cron lives in the YAML)  #
    # ------------------------------------------------------------------ #
    app_timezone: str = field(
        default_factory=lambda: os.environ.get("APP_TIMEZONE", "Asia/Dhaka")
    )
    cron_schedule: str = field(
        # UTC cron: "0 19 * * *" = 01:00 AM Bangladesh Standard Time (UTC+6)
        default_factory=lambda: os.environ.get("CRON_SCHEDULE", "0 19 * * *")
    )

    # ------------------------------------------------------------------ #
    # Processing limits                                                   #
    # ------------------------------------------------------------------ #
    max_jobs_per_run: int = field(
        # Hard cap — prevents accidental runaway API spend in one execution
        default_factory=lambda: int(os.environ.get("MAX_JOBS_PER_RUN", "10"))
    )
    rate_limit_delay: float = field(
        # Seconds to sleep between jobs; reduces chance of hitting API rate limits
        default_factory=lambda: float(os.environ.get("RATE_LIMIT_DELAY", "2"))
    )

    # ------------------------------------------------------------------ #
    # Network timeouts (seconds)                                          #
    # ------------------------------------------------------------------ #
    request_timeout: int = field(
        default_factory=lambda: int(os.environ.get("REQUEST_TIMEOUT", "20"))
    )
    scrape_timeout: int = field(
        # Separate, longer timeout for job-page scraping
        default_factory=lambda: int(os.environ.get("SCRAPE_TIMEOUT", "30"))
    )

    # ------------------------------------------------------------------ #
    # Retry counts per service                                            #
    # ------------------------------------------------------------------ #
    openai_retries: int = field(
        default_factory=lambda: int(os.environ.get("OPENAI_RETRIES", "3"))
    )
    google_retries: int = field(
        default_factory=lambda: int(os.environ.get("GOOGLE_RETRIES", "3"))
    )
    scrape_retries: int = field(
        default_factory=lambda: int(os.environ.get("SCRAPE_RETRIES", "2"))
    )

    # ------------------------------------------------------------------ #
    # Logging                                                             #
    # ------------------------------------------------------------------ #
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )

    # ------------------------------------------------------------------ #
    # File-system paths                                                   #
    # ------------------------------------------------------------------ #
    output_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("OUTPUT_DIR", "output"))
    )
    logs_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("LOGS_DIR", "logs"))
    )
    resumes_dir: Path = field(
        # Optimized .txt profiles live here — NOT raw PDFs
        default_factory=lambda: Path(os.environ.get("RESUMES_DIR", "resumes"))
    )
    raw_resumes_dir: Path = field(
        # Source PDFs for the one-time process_resume.py script
        default_factory=lambda: Path(os.environ.get("RAW_RESUMES_DIR", "raw_resumes"))
    )

    # ------------------------------------------------------------------ #
    # Spreadsheet status vocabulary                                       #
    # ------------------------------------------------------------------ #
    status_not_applied: str = STATUS_NOT_APPLIED
    status_processing: str = STATUS_PROCESSING
    status_draft_generated: str = STATUS_DRAFT_GENERATED
    status_failed: str = STATUS_FAILED

    # Statuses that qualify a row for processing (case-insensitive match)
    allowed_statuses: list = field(default_factory=lambda: [STATUS_NOT_APPLIED])

    # ------------------------------------------------------------------ #
    # Lifecycle hooks                                                     #
    # ------------------------------------------------------------------ #

    def __post_init__(self) -> None:
        """Create required directories so the rest of the code can assume they exist."""
        for directory in (self.output_dir, self.logs_dir, self.resumes_dir, self.raw_resumes_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def validate(self) -> Config:
        """
        Validate that all required secrets are present.

        Raises
        ------
        ValueError
            If one or more required environment variables are empty.

        Returns
        -------
        Config
            Self, to allow chaining: ``get_config().validate()``.
        """
        errors: list[str] = []

        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        if not self.google_service_account:
            errors.append("GOOGLE_SERVICE_ACCOUNT is required (full service-account JSON)")
        if not self.google_sheet_id:
            errors.append("GOOGLE_SHEET_ID is required")

        if errors:
            raise ValueError(f"Missing configuration: {'; '.join(errors)}")

        return self


# Module-level singleton — avoids re-parsing env vars on every call
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Return the shared Config singleton.

    Instantiates once on first call; subsequent calls return the cached instance.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
