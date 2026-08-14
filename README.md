# ATLAS Bot

One Telegram chat that messages you first. Claude is the brain, Google Drive/Sheets is the filing cabinet. You forward photos and type replies; everything files itself.

## What it does

- **07:00** — morning brief (Sundays include the weekly review automatically)
- **10:00 / 13:00 / 16:00 / 19:00** — short check-ins (lunch/snack photo asks, task nudges)
- **21:00** — evening close
- **Any photo you send** — analysed by Claude, auto-cropped, renamed, filed to Drive, logged to the right Sheet. X-rays with visible patient identifiers are **refused, never stored**.
- **"weight 100.4"** in chat — logged to the Health Log instantly.
- **Any text** — full ATLAS conversation, with your master context loaded every time.

## Setup (about an hour, once)

### 1. Telegram (5 min)
1. Message **@BotFather** → `/newbot` → name it ATLAS → copy the **token**.
2. Message **@userinfobot** → copy your numeric **user ID**.

### 2. Anthropic (2 min)
Create an API key at **console.anthropic.com** → API Keys.

### 3. Google Cloud (20 min, the fiddly one)
1. Go to **console.cloud.google.com** → create a project (e.g. "atlas").
2. **APIs & Services → Enable APIs** → enable **Google Drive API** and **Google Sheets API**.
3. **IAM & Admin → Service Accounts** → create one (any name) → **Keys → Add key → JSON** → download, save it next to the code as `service_account.json`.
4. In **your own Google Drive**: create a folder named **ATLAS**. Share it with the service-account email (the `...@...iam.gserviceaccount.com` address inside the JSON) as **Editor**. Copy the folder **ID** from the URL (the string after `/folders/`).

### 4. Run
```bash
pip install -r requirements.txt
cp .env.example .env        # fill in the four values
python setup_drive.py <ATLAS_FOLDER_ID>   # builds Cases/, Health/, the 3 Sheets
python atlas_bot.py
```
Send the bot a message. If it replies, you're live.

## Deploy (so it runs 24/7, not on your laptop)

**Option A — Railway (easiest, ~$5/mo).** railway.app → New Project → Deploy from repo (push this folder to a private GitHub repo first). Add the env vars in the dashboard; upload `service_account.json` and `atlas_ids.json` as files or paste the JSON into env vars and adapt. Start command: `python atlas_bot.py`.

**Option B — any $5 VPS (DigitalOcean/Hetzner/Lightsail).** Copy the folder up, install Python 3.11+, then:

```ini
# /etc/systemd/system/atlas.service
[Unit]
Description=ATLAS bot
After=network.target

[Service]
WorkingDirectory=/opt/atlas-bot
ExecStart=/usr/bin/python3 atlas_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
`systemctl enable --now atlas` and it survives reboots.

## Daily operation

- The **master context** lives in `atlas_context.md` next to the bot. It's the single source of truth. To update it, edit the file and restart the bot (10 seconds). Keep the same copy in your Claude.ai project so both brains match.
- **Cost:** ~$5/mo hosting + API usage. At your volume (7 scheduled calls/day + conversation + photos) expect roughly $5–15/mo on Sonnet.
- **Privacy:** the bot answers only your Telegram ID. Medical images are auto-cropped and identifier-gated before storage; keep patient names out of captions too.
- **Deep work** (drafting papers, email via connected tools, browsing) stays in Claude.ai. Telegram ATLAS will stage drafts and tell you when to switch over.

## Files

| File | Purpose |
|---|---|
| `atlas_bot.py` | main bot: handlers, scheduler, filing pipeline |
| `gdrive.py` | Drive/Sheets layer |
| `setup_drive.py` | one-time: builds folder tree + Sheets |
| `atlas_persona.txt` | ATLAS voice and prime rules |
| `atlas_context.md` | master context (edit this as life changes) |
| `atlas_ids.json` | generated — folder/sheet IDs |
| `memory.json` | generated — rolling conversation memory |

## v2 additions

**Gmail + Calendar live (needs one extra setup step):**
1. In the same Google Cloud project: enable **Gmail API** + **Calendar API**.
2. OAuth consent screen → External → add yourself as a test user.
3. Credentials → OAuth client ID → **Desktop app** → download JSON as `oauth_client.json`.
4. On your laptop: `python get_token.py` → browser opens → approve → `token.json` appears.
5. Copy `token.json` to the server. Done — email triage and calendar reminders go live. Without it, the bot runs fine minus those two feeds.

**How email works:** polled every 5 min. Claude triages silently — only genuinely important mail interrupts you, with a drafted reply staged. Type `SEND` to send it, or describe edits and a revised draft is staged. Nothing ever sends without that explicit word (prime rule 1).

**Commands:** `papers` `nuos` `hospital` `cases` `health` (tracker status) · `add to papers: ...` (file anything by talking) · `social` (pull the post/reply queue when you're free) · `SEND`.

**Protocol schedule:** 5:15 gym · 7:30 breakfast + brief · 13:00 lunch · 17:00 snack · 20:30 dinner · 21:30 close · 22:00 skincare + lights-out.

## Hospital (DocPulse) ingestion

DocPulse has no public API, so the pipeline runs on its **exports**:
1. Log into DocPulse → export any day-end / billing / pharmacy / OPD-IPD report (Excel, CSV, or PDF).
2. Send the file to the ATLAS Telegram chat.
3. It's analysed against the three-flows principle (clinical vs stock vs money), anomalies flagged, raw file archived to `Hospital Reports/`, numbers appended to the **Hospital Daily** sheet, and you get a short summary.

On-site later: staff email the day-end export to your Gmail on a schedule; the existing email poll picks it up automatically. Zero staff training beyond "attach and send".
