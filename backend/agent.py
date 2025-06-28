from dotenv import load_dotenv
load_dotenv()

import os
import json
import re
import dateparser
import google.generativeai as genai
from datetime import datetime, timedelta, time as dt_time
from backend.calendar_utils import check_availability, book_slot
from langgraph.graph import END, StateGraph
from typing import Optional
from pydantic import BaseModel

class State(BaseModel):
    text: Optional[str] = None
    response: Optional[str] = None
    last_suggested: Optional[dict] = None
    suggested_time: Optional[str] = None
    summary: Optional[str] = None
    duration: Optional[int] = None

# Setup Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

def extract_scheduling_details(user_message):
    now = datetime.now()
    today = now.date()
    prompt = f"""
You are a scheduling assistant. Convert user request into JSON like:

{{
  "intent": "book" | "check_availability" | "confirm" | "clarify",
  "start_time": "YYYY-MM-DD HH:MM:SS" | null,
  "end_time": "YYYY-MM-DD HH:MM:SS" | null,
  "duration_minutes": integer | null,
  "summary": string | null,
  "reply": string | null
}}

User: "{user_message}"
Respond ONLY with JSON.
"""
    try:
        response = model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print("Parsing error:", e)
        print("Raw Gemini response:", getattr(response, 'text', ''))
    return None

def find_next_available_slot(start_after, duration, same_day_only=False, max_days=14):
    search_days = 1 if same_day_only else max_days
    for day_offset in range(search_days):
        candidate_date = (start_after + timedelta(days=day_offset)).date()
        start_hour = start_after.hour if day_offset == 0 else 9
        start_minute = start_after.minute if day_offset == 0 else 0
        for hour in range(start_hour, 21):
            for minute in [0, 15, 30, 45]:
                if hour == start_hour and minute < start_minute:
                    continue
                slot_start = datetime.combine(candidate_date, dt_time(hour, minute))
                slot_end = slot_start + duration
                if slot_start >= datetime.now() and check_availability(slot_start, slot_end):
                    return slot_start
    return None

def handle_schedule_request(details, session_dict):
    start_window = dateparser.parse(details.get("start_time")) if details.get("start_time") else None
    end_window = dateparser.parse(details.get("end_time")) if details.get("end_time") else None
    duration_minutes = details.get("duration_minutes") or 60
    duration = timedelta(minutes=duration_minutes)
    summary = details.get("summary", "Appointment")
    now = datetime.now()

    if start_window and (not end_window or start_window == end_window):
        if check_availability(start_window, start_window + duration):
            book_slot(summary, start_window, start_window + duration)
            return {
                "response": f"✅ Booked for {start_window.strftime('%A, %B %d at %I:%M %p')}",
                "last_suggested": None
            }

        next_slot = find_next_available_slot(
            start_window + timedelta(minutes=15),
            duration,
            same_day_only=start_window.date() == now.date()
        )
        if next_slot:
            suggestion = {
                "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                "summary": summary,
                "duration": duration_minutes
            }
            return {
                "response": f"❌ Unavailable. Next: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                "last_suggested": suggestion,
                **suggestion
            }
        return {"response": "❌ No available slots found.", "last_suggested": None}

    if start_window and end_window:
        current = start_window
        while current + duration <= end_window:
            if check_availability(current, current + duration):
                suggestion = {
                    "suggested_time": current.strftime('%Y-%m-%d %H:%M:%S'),
                    "summary": summary,
                    "duration": duration_minutes
                }
                return {
                    "response": f"✅ Available: {current.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                    "last_suggested": suggestion,
                    **suggestion
                }
            current += timedelta(minutes=15)

        next_slot = find_next_available_slot(end_window, duration)
        if next_slot:
            suggestion = {
                "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                "summary": summary,
                "duration": duration_minutes
            }
            return {
                "response": f"❌ None in range. Next: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                "last_suggested": suggestion,
                **suggestion
            }

    return {"response": "❌ Could not parse a valid slot. Try again with a specific date/time.", "last_suggested": None}

def handle_availability_check(details, session_dict):
    start_time = dateparser.parse(details["start_time"])
    end_time = dateparser.parse(details["end_time"])
    duration_minutes = details.get("duration_minutes") or 60
    duration = timedelta(minutes=duration_minutes)

    current = start_time
    while current + duration <= end_time:
        if check_availability(current, current + duration):
            suggestion = {
                "suggested_time": current.strftime('%Y-%m-%d %H:%M:%S'),
                "summary": "Meeting",
                "duration": duration_minutes
            }
            return {
                "response": f"✅ Free slot: {current.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                "last_suggested": suggestion,
                **suggestion
            }
        current += timedelta(minutes=15)

    next_slot = find_next_available_slot(end_time, duration)
    if next_slot:
        suggestion = {
            "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
            "summary": "Meeting",
            "duration": duration_minutes
        }
        return {
            "response": f"❌ No slots in that window. Next: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
            "last_suggested": suggestion,
            **suggestion
        }

    return {"response": "❌ No availability found.", "last_suggested": None}

def chat(state: State) -> State:
    user_input = state.text.strip() if state.text else ""
    last_suggested = state.last_suggested
    details = extract_scheduling_details(user_input)
    if not details:
        return State(response="❌ Couldn't understand. Try 'Book a meeting tomorrow at 3 PM'.")

    intent = details.get("intent")
    if intent == "confirm":
        if last_suggested and last_suggested.get("suggested_time"):
            meeting_start = dateparser.parse(last_suggested["suggested_time"])
            duration = timedelta(minutes=last_suggested.get("duration", 60))
            meeting_end = meeting_start + duration
            summary = last_suggested.get("summary", "Meeting")
            if check_availability(meeting_start, meeting_end):
                book_slot(summary, meeting_start, meeting_end)
                return State(response=f"✅ Confirmed for {meeting_start.strftime('%A, %B %d at %I:%M %p')}")
            next_slot = find_next_available_slot(meeting_start + timedelta(minutes=15), duration)
            if next_slot:
                return State(
                    response=f"❌ That time is gone. Next: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                    last_suggested={
                        "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                        "summary": summary,
                        "duration": duration.seconds // 60
                    }
                )
            return State(response="❌ No available slots.")
        return State(response="❌ Nothing to confirm. What time would you like to book?")

    if intent == "clarify":
        return State(response=details.get("reply", "Can you clarify the time?"))
    elif intent == "book":
        return State(**handle_schedule_request(details, state.dict()))
    elif intent == "check_availability":
        return State(**handle_availability_check(details, state.dict()))

    return State(response=details.get("reply", "Try rephrasing your request."))

workflow = StateGraph(State)
workflow.add_node("chat", chat)
workflow.set_entry_point("chat")
workflow.add_edge("chat", END)
agent_app = workflow.compile()
