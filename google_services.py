import os, uuid, base64
from pathlib import Path
from datetime import timedelta
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE = Path(__file__).resolve().parent
CREDENTIALS = BASE / "credentials.json"
TOKEN = BASE / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]

def credentials():
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not CREDENTIALS.exists():
            raise FileNotFoundError("Place Google OAuth desktop credentials at credentials.json.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds

def send_email(to_email, subject, body):
    service = build("gmail", "v1", credentials=credentials())
    msg = EmailMessage()
    msg["To"], msg["Subject"] = to_email, subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id", "")

def create_meet_event(title, description, email, start_dt):
    service = build("calendar", "v3", credentials=credentials())
    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": (start_dt + timedelta(minutes=30)).isoformat(),
                "timeZone": "Asia/Kolkata"},
        "attendees": [{"email": email}],
        "conferenceData": {"createRequest": {
            "requestId": str(uuid.uuid4()),
            "conferenceSolutionKey": {"type": "hangoutsMeet"}
        }}
    }
    created = service.events().insert(
        calendarId="primary", body=event,
        conferenceDataVersion=1, sendUpdates="all"
    ).execute()
    link = created.get("hangoutLink")
    if not link:
        for point in created.get("conferenceData", {}).get("entryPoints", []):
            if point.get("entryPointType") == "video":
                link = point.get("uri")
                break
    return {"event_id": created["id"], "event_url": created.get("htmlLink", ""),
            "meet_link": link or ""}
