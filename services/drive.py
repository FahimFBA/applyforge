"""
services/drive.py
=================
Google Drive integration for the applyforge project.

Responsibilities
----------------
* Authenticate with Google Drive API via OAuth2 user credentials (preferred)
  or a service-account JSON secret (fallback, requires Shared Drive).
* Resolve (or lazily create) the top-level parent folder and per-company sub-folders.
* Upload generated documents (.md, .docx) into the correct company folder.
* Return the shareable web-view link for each uploaded file.

Authentication modes
--------------------
OAuth2 (recommended for personal Google Drive):
    Set GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, and
    GOOGLE_OAUTH_REFRESH_TOKEN.  Files are uploaded as the real Google user
    so they count against the user's Drive quota — no service-account
    storage-quota errors.  Generate the refresh token once with:
        python scripts/generate_refresh_token.py

Service account (fallback):
    Set GOOGLE_SERVICE_ACCOUNT (full JSON string).  Only works when uploading
    to a Shared Drive folder — service accounts have zero personal Drive quota.

Folder hierarchy created in Drive
----------------------------------
    Applications/           ← GOOGLE_DRIVE_FOLDER_ID  (or GOOGLE_DRIVE_PARENT_FOLDER)
        CompanyName/        ← created automatically per company
            file.md
            file.docx

Usage
-----
    from services.drive import DriveService
    from services.config import get_config

    svc = DriveService(get_config())
    link = svc.upload_file(Path("output/Acme/Acme_123_cover_letter.docx"), "Acme")
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from services.config import Config
from services.logger import setup_logger

# Drive scope — full access needed to create folders and upload files
_SCOPES = ["https://www.googleapis.com/auth/drive"]

# MIME type lookup for the file formats this project produces
_MIME_MAP: dict[str, str] = {
    ".md": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}

logger = setup_logger(__name__)


class DriveService:
    """
    Wrapper around the Google Drive v3 REST API.

    Authenticates lazily on first use via OAuth2 user credentials (preferred)
    or service-account JSON (fallback).  Caches the parent folder ID to avoid
    redundant API calls across multiple uploads in the same run.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._service = None                           # googleapiclient Resource object
        self._parent_folder_id: Optional[str] = None  # cached ID of the top-level folder

    # ------------------------------------------------------------------ #
    # Authentication                                                       #
    # ------------------------------------------------------------------ #

    def _build_credentials(self):
        """
        Return Drive credentials, preferring OAuth2 user credentials over
        service-account credentials.

        OAuth2 mode (GOOGLE_OAUTH_REFRESH_TOKEN is set):
            Uploads run as the real Google user.  Files are owned by the user
            and charged to the user's Drive quota — works with personal Drive.

        Service-account mode (fallback):
            Uploads run as the service account.  Service accounts have no
            personal Drive storage quota — only works with Shared Drives.

        Returns
        -------
        google.auth.credentials.Credentials
        """
        if self.config.google_oauth_refresh_token:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials as OAuthCredentials

            creds = OAuthCredentials(
                token=None,
                refresh_token=self.config.google_oauth_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.config.google_oauth_client_id,
                client_secret=self.config.google_oauth_client_secret,
                scopes=_SCOPES,
            )
            creds.refresh(Request())
            logger.debug("Drive auth: OAuth2 user credentials")
            return creds

        # Fallback — service account (Shared Drive only)
        from google.oauth2.service_account import Credentials as SACredentials

        sa_info = json.loads(self.config.google_service_account)
        logger.debug("Drive auth: service-account credentials")
        return SACredentials.from_service_account_info(sa_info, scopes=_SCOPES)

    def connect(self) -> None:
        """Build the Drive API client and resolve the top-level parent folder."""
        creds = self._build_credentials()
        self._service = build("drive", "v3", credentials=creds)

        if self.config.google_drive_folder_id:
            # Use explicit folder ID — most reliable, avoids name-collision issues
            self._parent_folder_id = self.config.google_drive_folder_id
            logger.info(
                f"Drive connected. Using folder id={self._parent_folder_id} "
                "(from GOOGLE_DRIVE_FOLDER_ID)"
            )
        else:
            # Search by name — works when authenticated as the folder owner
            self._parent_folder_id = self._get_or_create_folder(
                name=self.config.google_drive_parent_folder,
                parent_id=None,
            )
            logger.info(
                f"Drive connected. Parent folder '{self.config.google_drive_parent_folder}' "
                f"→ id={self._parent_folder_id}"
            )

    def _ensure_connected(self) -> None:
        """Connect on first use (lazy initialisation pattern)."""
        if self._service is None:
            self.connect()

    # ------------------------------------------------------------------ #
    # Folder management                                                    #
    # ------------------------------------------------------------------ #

    def _get_or_create_folder(self, name: str, parent_id: Optional[str]) -> str:
        """
        Return the Drive folder ID for ``name``, creating it if necessary.

        Parameters
        ----------
        name:
            Display name of the folder.
        parent_id:
            Parent folder ID, or None to search/create at Drive root.

        Returns
        -------
        str
            The Google Drive file ID of the folder.
        """
        query = (
            f"name='{name}' "
            f"and mimeType='application/vnd.google-apps.folder' "
            f"and trashed=false"
        )
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = (
            self._service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        files = results.get("files", [])
        if files:
            return files[0]["id"]

        metadata: dict = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        folder = (
            self._service.files()
            .create(body=metadata, fields="id", supportsAllDrives=True)
            .execute()
        )
        logger.info(f"Created Drive folder: '{name}'")
        return folder["id"]

    # ------------------------------------------------------------------ #
    # Upload                                                               #
    # ------------------------------------------------------------------ #

    def upload_file(self, file_path: Path, company_name: str) -> str:
        """
        Upload a local file to Drive under Applications/CompanyName/.

        Creates the company sub-folder automatically on first upload for that
        company.  Uses exponential backoff on HTTP errors.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the local file.
        company_name:
            Company name used as the sub-folder name in Drive.

        Returns
        -------
        str
            The webViewLink of the uploaded file, or an empty string on failure.
        """
        self._ensure_connected()

        company_folder_id = self._get_or_create_folder(
            name=company_name,
            parent_id=self._parent_folder_id,
        )

        mime_type = _MIME_MAP.get(file_path.suffix, "application/octet-stream")

        file_metadata: dict = {
            "name": file_path.name,
            "parents": [company_folder_id],
        }
        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

        retries = self.config.google_retries
        for attempt in range(retries):
            try:
                uploaded = (
                    self._service.files()
                    .create(
                        body=file_metadata,
                        media_body=media,
                        fields="id,webViewLink",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
                link = uploaded.get("webViewLink", "")
                logger.info(
                    f"Uploaded '{file_path.name}' → Drive/{company_name}/ | {link}"
                )
                return link

            except HttpError as exc:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        f"Drive upload failed (attempt {attempt + 1}/{retries}), "
                        f"retrying in {wait}s: {exc}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"Drive upload failed for '{file_path.name}' after {retries} attempts: {exc}"
                    )
                    raise

        return ""
