"""OAuth helper for Gmail + Calendar (these need YOUR Google account's consent,
unlike Drive/Sheets which use the service account).

One-time: run  python get_token.py  on your laptop → produces token.json.
Copy token.json to the server next to the code. It auto-refreshes forever after.
"""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
]
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")


def get_user_creds():
    """Load token.json, refreshing if expired. Returns None if missing."""
    if not os.path.exists(TOKEN_FILE):
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds
