# By: Md. Fahim Bin Amin
# One-time script to generate an OAuth2 refresh token for Google Drive access.

"""
Run this locally once.

A browser window will open - log in with the Google account that owns the Drive folder where outputs should be saved.
The refresh token is printed at the end. Copy it to the GitHub Secret.

Prerequisites
-------------
1. GCP Console -> APIs & Services -> Credentials -> + Create Credentials -> OAuth 2.0 Client ID ->
                                                                        Application type: Desktop app -> Download JSON.
2. Save the downloaded file as ``oauth_client.json`` in the project root (it is already listed in .gitignore - never
   commit it).
3. Run this script:
       python scripts/generate_refresh_token.py (Windows)
       python3 scripts/generate_refresh_token.py (Mac/Linux)
4. Authorise in the browser.
5. Copy the printed values into GitHub Secrets:
       GOOGLE_OAUTH_CLIENT_ID
       GOOGLE_OAUTH_CLIENT_SECRET
       GOOGLE_OAUTH_REFRESH_TOKEN
6. Delete ``oauth_client.json`` from your machine.

Alternatively, if you prefer not to save the JSON file, set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in
your .env file and run the script - it will read them from the environment.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running directly from the project root or from the scripts/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive"]
CLIENT_SECRET_FILE = Path(__file__).parent.parent / "oauth_client.json"


def load_flow():
    """
    Build an InstalledAppFlow from the client-secret JSON file or env vars.

    Returns
    -------
    google_auth_oauthlib.flow.InstalledAppFlow
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib is not installed.")
        print("Run:  pip install google-auth-oauthlib")
        sys.exit(1)

    if CLIENT_SECRET_FILE.exists():
        print(f"Using client secret file: {CLIENT_SECRET_FILE}\n")
        return InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)

    # Fall back to env vars
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(f"ERROR: '{CLIENT_SECRET_FILE}' not found.")
        print("Either download it from GCP Console (OAuth 2.0 Client IDs → Desktop app)")
        print("or set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env\n")
        sys.exit(1)

    print("Using GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET from environment.\n")
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    return InstalledAppFlow.from_client_config(client_config, SCOPES)


def main() -> None:
    """Run the OAuth2 flow, print the refresh token, and exit."""
    flow = load_flow()

    print("Opening browser for Google authentication.")
    print("Log in with the account that owns your Drive folder.\n")

    # run_local_server opens a browser and starts a local redirect listener
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print(
            "\nWARNING: No refresh token returned.  This usually means the app was "
            "already authorised previously.\n"
            "Revoke access at https://myaccount.google.com/permissions and rerun.\n"
        )
        sys.exit(1)

    # Extract client credentials from the flow for display
    client_id = getattr(flow, "client_config", {}).get("client_id", "") or (
        read_client_id_from_file()
    )
    client_secret = getattr(flow, "client_config", {}).get("client_secret", "") or (
        read_client_secret_from_file()
    )

    print("\n" + "=" * 65)
    print("SUCCESS - add these three values to GitHub Secrets / .env:\n")
    if client_id:
        print(f"GOOGLE_OAUTH_CLIENT_ID={client_id}")
    if client_secret:
        print(f"GOOGLE_OAUTH_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 65)
    print(
        "\nAlso set GOOGLE_DRIVE_FOLDER_ID to the ID of your Drive folder.\n"
        "Get it from the URL:  drive.google.com/drive/folders/<FOLDER_ID>\n"
    )
    print("IMPORTANT: Delete oauth_client.json after copying the values above.")


def read_client_id_from_file() -> str:
    """Read client_id from oauth_client.json if it exists."""
    return read_field_from_file("client_id")


def read_client_secret_from_file() -> str:
    """Read client_secret from oauth_client.json if it exists."""
    return read_field_from_file("client_secret")


def read_field_from_file(field: str) -> str:
    if not CLIENT_SECRET_FILE.exists():
        return ""
    try:
        data = json.loads(CLIENT_SECRET_FILE.read_text())
        installed = data.get("installed", data.get("web", {}))
        return installed.get(field, "")
    except Exception:
        return ""


if __name__ == "__main__":
    main()
