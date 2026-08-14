"""One-time, run on your LAPTOP (needs a browser):  python get_token.py

Prereq: in your Google Cloud project (same one as the service account):
  1. Enable Gmail API and Google Calendar API.
  2. APIs & Services -> OAuth consent screen -> External -> add yourself as test user.
  3. Credentials -> Create credentials -> OAuth client ID -> Desktop app.
     Download the JSON, save as  oauth_client.json  next to this script.

Produces token.json — copy it to the server. Never share it; it is access to
your Gmail and Calendar.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

from google_auth import SCOPES

flow = InstalledAppFlow.from_client_secrets_file("oauth_client.json", SCOPES)
creds = flow.run_local_server(port=0)
with open("token.json", "w") as f:
    f.write(creds.to_json())
print("token.json written. Copy it to the server next to atlas_bot.py.")
