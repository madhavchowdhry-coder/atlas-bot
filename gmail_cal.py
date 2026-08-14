"""Gmail + Calendar layer for ATLAS.

Gmail: polled every few minutes — effectively live. New unread mail goes to
Claude for triage; only what matters interrupts Madhav. Sending happens ONLY
after his explicit SEND approval in Telegram (prime rule 1).

Calendar: today's events for the morning brief + a 30-minute look-ahead for
event reminders.
"""
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from google_auth import get_user_creds


class GoogleLive:
    def __init__(self):
        creds = get_user_creds()
        self.ok = creds is not None
        if self.ok:
            self.gmail = build("gmail", "v1", credentials=creds)
            self.cal = build("calendar", "v3", credentials=creds)

    # ------------------------------------------------------------- gmail read

    def unread_messages(self, max_n: int = 10) -> list:
        """Unread inbox messages, newest first: [{id, sender, subject, snippet}]."""
        res = (
            self.gmail.users()
            .messages()
            .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_n)
            .execute()
        )
        out = []
        for m in res.get("messages", []):
            full = (
                self.gmail.users()
                .messages()
                .get(userId="me", id=m["id"], format="metadata",
                     metadataHeaders=["From", "Subject"])
                .execute()
            )
            headers = {h["name"]: h["value"]
                       for h in full.get("payload", {}).get("headers", [])}
            out.append({
                "id": m["id"],
                "sender": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "snippet": full.get("snippet", ""),
            })
        return out

    def mark_seen(self, msg_id: str) -> None:
        """Remove UNREAD so the poller never re-triages the same mail.
        (It stays in the inbox; 'seen by ATLAS' not 'handled by Madhav'.)"""
        self.gmail.users().messages().modify(
            userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

    # ------------------------------------------------------------- gmail send

    def send_email(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        self.gmail.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

    # ------------------------------------------------------------- calendar

    def _events(self, start: datetime, end: datetime) -> list:
        res = (
            self.cal.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        out = []
        for e in res.get("items", []):
            start_s = e["start"].get("dateTime", e["start"].get("date", ""))
            out.append({"start": start_s, "title": e.get("summary", "(untitled)")})
        return out

    def today(self, tz) -> list:
        now = datetime.now(tz)
        end = now.replace(hour=23, minute=59, second=59)
        return self._events(now, end)

    def next_half_hour(self, tz) -> list:
        now = datetime.now(tz)
        return self._events(now + timedelta(minutes=1), now + timedelta(minutes=31))
