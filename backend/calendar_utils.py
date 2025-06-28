import os
import base64
import json
from tempfile import NamedTemporaryFile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']
calendar_id = os.getenv("GOOGLE_CALENDAR_ID")

# Decode base64 credentials
encoded_credentials = os.getenv("GOOGLE_CREDENTIALS_B64")
if not encoded_credentials:
    raise ValueError("Missing GOOGLE_CREDENTIALS_B64 environment variable.")

try:
    decoded_bytes = base64.b64decode(encoded_credentials)
    json_credentials = json.loads(decoded_bytes)
except Exception as e:
    raise ValueError(f"Failed to decode or parse GOOGLE_CREDENTIALS_B64: {e}")

# Write credentials to a secure temporary file
with NamedTemporaryFile("w+", suffix=".json", delete=False) as temp_file:
    json.dump(json_credentials, temp_file)
    temp_file.flush()
    temp_file_name = temp_file.name

# Authenticate
credentials = service_account.Credentials.from_service_account_file(
    temp_file_name, scopes=SCOPES
)

# Initialize Google Calendar API
service = build('calendar', 'v3', credentials=credentials)

def check_availability(start_dt: datetime, end_dt: datetime) -> bool:
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_dt.astimezone(pytz.UTC).isoformat(),
        timeMax=end_dt.astimezone(pytz.UTC).isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return len(events_result.get('items', [])) == 0

def book_slot(summary: str, start_dt: datetime, end_dt: datetime) -> dict:
    event = {
        'summary': summary,
        'start': {'dateTime': start_dt.astimezone(pytz.UTC).isoformat()},
        'end': {'dateTime': end_dt.astimezone(pytz.UTC).isoformat()}
    }
    return service.events().insert(calendarId=calendar_id, body=event).execute()