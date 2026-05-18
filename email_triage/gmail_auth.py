"""
Gmail OAuth2 helper for Rinata email triage.

FIRST-TIME SETUP (run once per machine):
    1. Go to console.cloud.google.com → APIs & Services → Credentials
    2. Enable the Gmail API for the project
    3. Create OAuth 2.0 Client ID (Desktop app type)
    4. Download credentials.json → save to email_triage/credentials.json
    5. Run: python email_triage/gmail_auth.py
    6. A browser window opens → sign in with the RESTAURANT Google account
    7. token.json is saved — you won't need to re-authenticate until it expires

After setup, all other scripts call get_gmail_service() silently.
"""

from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",   # for draft replies later
]

AUTH_DIR   = Path(__file__).parent
CREDS_FILE = AUTH_DIR / "credentials.json"
TOKEN_FILE = AUTH_DIR / "token.json"


def get_gmail_service():
    """Return an authenticated Gmail API service object."""
    if not CREDS_FILE.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {CREDS_FILE}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials.\n"
            "See the docstring in gmail_auth.py for full setup steps."
        )

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


if __name__ == "__main__":
    print("Authenticating with Gmail...")
    service = get_gmail_service()
    profile = service.users().getProfile(userId="me").execute()
    print(f"\n✓ Authenticated as: {profile['emailAddress']}")
    print(f"  Total messages: {profile.get('messagesTotal', 'unknown')}")
    print(f"\ntoken.json saved to {TOKEN_FILE}")
    print("Setup complete — you won't need to re-authenticate.")
