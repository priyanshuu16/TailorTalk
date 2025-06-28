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

# ✅ LangGraph-compatible state
class State(BaseModel):
    text: Optional[str] = None
    response: Optional[str] = None
    last_suggested: Optional[dict] = None
    suggested_time: Optional[str] = None
    summary: Optional[str] = None
    duration: Optional[int] = None

# ✅ Gemini setup
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY in environment.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# ✅ Extract scheduling info using Gemini
def extract_scheduling_details(user_message):
    now = datetime.now()
    today = now.date()

    prompt = f"""
You are a smart calendar assistant. Return user request as a JSON object like:

{{
  "intent": "book" | "check_availability" | "confirm" | "clarify",
  "start_time": "YYYY-MM-DD HH:MM:SS" | null,
  "end_time": "YYYY-MM-DD HH:MM:SS" | null,
  "duration_minutes": integer | null,
  "summary": string | null,
  "reply": string | null
}}

User: "{user_message}"
ONLY output JSON.
"""
    try:
        response = model.generate_content(prompt)
        match = re.search(r"\{.*\}", response.text or "", re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print("Gemini Error:", e)
        print("Response:", getattr(response, "text", ""))
    return None

# ✅ Find next available slot
def find_next_available_slot(start_after, duration, same_day_only=False, max_days=14):
    for i in range(1 if same_day_only else max_days):
        date = (start_after + timedelta(days=i)).date()
        hour = start_after.hour if i == 0 else 9
        minute = start_after.minute if i == 0 else 0
        for h in range(hour, 21):
            for m in [0, 15, 30, 45]:
                if h == hour and m < minute:
                    continue
                slot_start = datetime.combine(date, dt_time(h, m))
                slot_end = slot_start + duration
                if slot_start >= datetime.now() and check_availability(slot_start, slot_end):
                    return slot_start
    return None

# ✅ Book logic
def handle_schedule_request(details, session_state):
    start = dateparser.parse(details.get("start_time")) if details.get("start_time") else None
    end = dateparser.parse(details.get("end_time")) if details.get("end_time") else None
    minutes = details.get("duration_minutes") or 60
    duration = timedelta(minutes=minutes)
    summary = details.get("summary", "Meeting")

    if start and (not end or start == end):
        if check_availability(start, start + duration):
            book_slot(summary, start, start + duration)
            return {"response": f"✅ Booked for {start.strftime('%A, %B %d at %I:%M %p')}", "last_suggested": None}
        next_slot = find_next_available_slot(start + timedelta(minutes=15), duration, same_day_only=start.date() == datetime.now().date())
        if next_slot:
            return {
                "response": f"❌ Busy. Next: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                "last_suggested": {
                    "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                    "summary": summary,
                    "duration": minutes
                }
            }
        return {"response": "❌ No available slots.", "last_suggested": None}

    if start and end:
        current = start
        while current + duration <= end:
            if check_availability(current, current + duration):
                return {
                    "response": f"✅ Available: {current.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                    "last_suggested": {
                        "suggested_time": current.strftime('%Y-%m-%d %H:%M:%S'),
                        "summary": summary,
                        "duration": minutes
                    }
                }
            current += timedelta(minutes=15)

    return {"response": "❌ Could not find available slot.", "last_suggested": None}

# ✅ Availability check logic
def handle_availability_check(details, session_state):
    start = dateparser.parse(details.get("start_time"))
    end = dateparser.parse(details.get("end_time"))
    minutes = details.get("duration_minutes") or 60
    duration = timedelta(minutes=minutes)

    current = start
    while current + duration <= end:
        if check_availability(current, current + duration):
            return {
                "response": f"✅ Free: {current.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                "last_suggested": {
                    "suggested_time": current.strftime('%Y-%m-%d %H:%M:%S'),
                    "summary": "Meeting",
                    "duration": minutes
                }
            }
        current += timedelta(minutes=15)

    return {"response": "❌ No availability found.", "last_suggested": None}

# ✅ Chat logic
def chat(state: State) -> State:
    user_input = (state.text or "").strip()
    parsed = extract_scheduling_details(user_input)

    if not parsed:
        return State(response="❌ Couldn't parse your request. Try 'Book tomorrow at 2pm'.")

    intent = parsed.get("intent")

    if intent == "confirm" and state.last_suggested:
        suggestion = state.last_suggested
        if not suggestion.get("suggested_time") or not suggestion.get("duration"):
            return State(response="❌ Missing suggested slot details.")
        start = dateparser.parse(suggestion["suggested_time"])
        duration = timedelta(minutes=suggestion["duration"])
        end = start + duration
        if check_availability(start, end):
            book_slot(suggestion["summary"], start, end)
            return State(response=f"✅ Confirmed for {start.strftime('%A, %B %d at %I:%M %p')}")
        else:
            next_slot = find_next_available_slot(start + timedelta(minutes=15), duration)
            if next_slot:
                return State(
                    response=f"❌ That time is now busy. Next: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                    last_suggested={
                        "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                        "summary": suggestion["summary"],
                        "duration": suggestion["duration"]
                    }
                )
            return State(response="❌ No available alternatives.")
    elif intent == "clarify":
        return State(response=parsed.get("reply", "❓ Can you clarify your request?"))
    elif intent == "book":
        return State(**handle_schedule_request(parsed, state.dict()))
    elif intent == "check_availability":
        return State(**handle_availability_check(parsed, state.dict()))
    else:
        return State(response=parsed.get("reply", "❌ I didn’t understand your intent."))

# ✅ LangGraph setup
workflow = StateGraph(State)
workflow.add_node("chat", chat)
workflow.set_entry_point("chat")
workflow.add_edge("chat", END)
agent_app = workflow.compile()