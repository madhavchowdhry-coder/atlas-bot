"""Google Drive + Sheets storage layer for ATLAS.

One tree, one truth:
  ATLAS/
    Cases/YYYY-MM/    de-identified medical images
    Health/YYYY-MM/   meal photos
    Case Log          (Sheet)
    Health Log        (Sheet)
    Master Tracker    (Sheet)

Folder and sheet IDs live in atlas_ids.json, written by setup_drive.py.
"""
import io
import json
from datetime import datetime

import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveStore:
    def __init__(self, sa_file: str, ids_file: str = "atlas_ids.json"):
        creds = service_account.Credentials.from_service_account_file(
            sa_file, scopes=SCOPES
        )
        self.drive = build("drive", "v3", credentials=creds)
        self.gc = gspread.authorize(creds)
        with open(ids_file) as f:
            self.ids = json.load(f)

    # ---------- folders ----------

    def _month_folder(self, parent_id: str) -> str:
        """Return (creating if needed) this month's subfolder, e.g. 2026-08."""
        name = datetime.now().strftime("%Y-%m")
        q = (
            f"'{parent_id}' in parents and name = '{name}' "
            f"and mimeType = '{FOLDER_MIME}' and trashed = false"
        )
        hits = (
            self.drive.files()
            .list(q=q, fields="files(id)")
            .execute()
            .get("files", [])
        )
        if hits:
            return hits[0]["id"]
        body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
        return self.drive.files().create(body=body, fields="id").execute()["id"]

    # ---------- images ----------

    def upload_image(self, kind: str, filename: str, data: bytes) -> str:
        """kind: 'cases' or 'health'. Returns a webViewLink."""
        parent = self._month_folder(self.ids[kind])
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="image/jpeg")
        f = (
            self.drive.files()
            .create(
                body={"name": filename, "parents": [parent]},
                media_body=media,
                fields="id, webViewLink",
            )
            .execute()
        )
        return f.get("webViewLink", "")

    def upload_file(self, kind: str, filename: str, data: bytes, mime: str) -> str:
        """Upload any raw file (hospital reports etc.). Returns webViewLink."""
        parent = self._month_folder(self.ids[kind])
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime)
        f = (
            self.drive.files()
            .create(
                body={"name": filename, "parents": [parent]},
                media_body=media,
                fields="id, webViewLink",
            )
            .execute()
        )
        return f.get("webViewLink", "")

    # ---------- sheets ----------

    def append_case(self, row: list) -> None:
        self.gc.open_by_key(self.ids["case_log"]).sheet1.append_row(
            row, value_input_option="USER_ENTERED"
        )

    def append_health(self, row: list) -> None:
        self.gc.open_by_key(self.ids["health_log"]).sheet1.append_row(
            row, value_input_option="USER_ENTERED"
        )

    def recent_health(self, n: int = 15) -> list:
        """Last n Health Log rows — fed to the Sunday brief for weight trend."""
        ws = self.gc.open_by_key(self.ids["health_log"]).sheet1
        rows = ws.get_all_values()
        return rows[-n:] if len(rows) > 1 else []

    # ---------- generic trackers (papers, nuos, hospital, ...) ----------

    def tracker_rows(self, key: str, n: int = 40) -> list:
        """All (or last n) rows of any tracker sheet, headers included."""
        ws = self.gc.open_by_key(self.ids[key]).sheet1
        rows = ws.get_all_values()
        return rows[:1] + rows[max(1, len(rows) - n):] if rows else []

    def tracker_append(self, key: str, row: list) -> None:
        self.gc.open_by_key(self.ids[key]).sheet1.append_row(
            row, value_input_option="USER_ENTERED"
        )
