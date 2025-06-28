import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Load environment variables
calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not calendar_id:
    raise ValueError("GOOGLE_CALENDAR_ID is missing in .env")

if not credentials_path or not os.path.exists(credentials_path):
    raise FileNotFoundError("GOOGLE_APPLICATION_CREDENTIALS file not found or path is invalid.")

# Set up Google Calendar API client
credentials = service_account.Credentials.from_service_account_file(
    credentials_path, scopes=SCOPES
)
service = build('calendar', 'v3', credentials=credentials)

# Check if the slot is available
def check_availability(start_dt: datetime, end_dt: datetime) -> bool:
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_dt.astimezone(pytz.UTC).isoformat(),
            timeMax=end_dt.astimezone(pytz.UTC).isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return len(events) == 0
    except Exception as e:
        print(f"[Calendar Error] Availability check failed: {e}")
        return False

# Book a slot
def book_slot(summary: str, start_dt: datetime, end_dt: datetime):
    try:
        event = {
            'summary': summary,
            'start': {'dateTime': start_dt.astimezone(pytz.UTC).isoformat()},
            'end': {'dateTime': end_dt.astimezone(pytz.UTC).isoformat()},
        }
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"[Calendar] Event created: {created_event.get('htmlLink')}")
        return created_event
    except Exception as e:
        print(f"[Calendar Error] Failed to book slot: {e}")
        return None