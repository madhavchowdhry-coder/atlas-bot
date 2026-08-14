"""One-time setup: builds the ATLAS folder tree + Sheets and writes atlas_ids.json.

Before running:
  1. Create a folder named ATLAS in your own Google Drive.
  2. Share it (Editor) with the service-account email from service_account.json.
  3. Copy the folder ID from its URL (the string after /folders/).

Run:
  python setup_drive.py <ATLAS_FOLDER_ID>

Safe to re-run: existing folders/sheets are reused, not duplicated.
"""
import json
import os
import sys

import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
FOLDER_MIME = "application/vnd.google-apps.folder"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"

SHEETS = {
    "case_log": (
        "Case Log",
        ["Date", "Time", "Type", "Region", "View", "Findings",
         "Procedure", "Role", "Notes", "Image"],
    ),
    "health_log": (
        "Health Log",
        ["Date", "Time", "Type", "Value / Note", "Image"],
    ),
    "tracker": (
        "Master Tracker",
        ["Item", "Domain", "Due", "Status", "Notes"],
    ),
    "papers": (
        "Papers Pipeline",
        ["Paper", "Lane", "Stage", "Next action", "Collaborators", "Updated", "Notes"],
    ),
    "nuos": (
        "NuOs Tracker",
        ["Workstream", "Owner", "Status", "Next action", "Due", "Updated", "Notes"],
    ),
    "hospital": (
        "Hospital Projects",
        ["Project", "Status", "Next action", "Blocker", "Updated", "Notes"],
    ),
    "hospital_daily": (
        "Hospital Daily",
        ["Date", "Report", "OPD", "IPD", "Collections",
         "Pharmacy sales", "Claims", "Flags", "Notes"],
    ),
}


def find(drive, parent, name, mime):
    q = (
        f"'{parent}' in parents and name = '{name}' "
        f"and mimeType = '{mime}' and trashed = false"
    )
    hits = drive.files().list(q=q, fields="files(id)").execute().get("files", [])
    return hits[0]["id"] if hits else None


def ensure_folder(drive, parent, name):
    fid = find(drive, parent, name, FOLDER_MIME)
    if fid:
        print(f"  exists   {name}/")
        return fid
    body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent]}
    fid = drive.files().create(body=body, fields="id").execute()["id"]
    print(f"  created  {name}/")
    return fid


def ensure_sheet(drive, gc, parent, name, headers):
    sid = find(drive, parent, name, SHEET_MIME)
    if sid:
        print(f"  exists   {name}")
        return sid
    body = {"name": name, "mimeType": SHEET_MIME, "parents": [parent]}
    sid = drive.files().create(body=body, fields="id").execute()["id"]
    ws = gc.open_by_key(sid).sheet1
    ws.append_row(headers)
    ws.format("1:1", {"textFormat": {"bold": True}})
    print(f"  created  {name}")
    return sid


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python setup_drive.py <ATLAS_FOLDER_ID>")
    root = sys.argv[1]
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

    creds = service_account.Credentials.from_service_account_file(
        sa_file, scopes=SCOPES
    )
    drive = build("drive", "v3", credentials=creds)
    gc = gspread.authorize(creds)

    print("Building ATLAS tree...")
    ids = {"root": root}
    ids["cases"] = ensure_folder(drive, root, "Cases")
    ids["health"] = ensure_folder(drive, root, "Health")
    ids["reports"] = ensure_folder(drive, root, "Hospital Reports")
    for key, (name, headers) in SHEETS.items():
        ids[key] = ensure_sheet(drive, gc, root, name, headers)

    with open("atlas_ids.json", "w") as f:
        json.dump(ids, f, indent=2)
    print("\nWrote atlas_ids.json. Setup complete — run: python atlas_bot.py")


if __name__ == "__main__":
    main()
