import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']
calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
credentials = service_account.Credentials.from_service_account_file(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), scopes=SCOPES)
service = build('calendar', 'v3', credentials=credentials)

def check_availability(start_dt, end_dt):
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_dt.astimezone(pytz.UTC).isoformat(),
        timeMax=end_dt.astimezone(pytz.UTC).isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return len(events_result.get('items', [])) == 0

def book_slot(summary, start_dt, end_dt):
    event = {
        'summary': summary,
        'start': {'dateTime': start_dt.astimezone(pytz.UTC).isoformat()},
        'end': {'dateTime': end_dt.astimezone(pytz.UTC).isoformat()}
    }
    return service.events().insert(calendarId=calendar_id, body=event).execute()
