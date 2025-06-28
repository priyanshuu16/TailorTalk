from dotenv import load_dotenv
load_dotenv()

import os
import google.generativeai as genai
from datetime import datetime, timedelta, time as dt_time
import dateparser
import json
import re
from backend.calendar_utils import check_availability, book_slot
from langgraph.graph import END, StateGraph

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

def get_weekday_name(weekday):
    """Convert weekday number to name (0=Monday, 6=Sunday)"""
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday]

def get_month_mondays(year, month):
    """Get all Mondays in a given month"""
    from calendar import monthrange
    import datetime
    mondays = []
    first_day = datetime.date(year, month, 1)
    last_day = datetime.date(year, month, monthrange(year, month)[1])
    
    current = first_day
    while current <= last_day:
        if current.weekday() == 0:  # Monday
            mondays.append(current)
        current += timedelta(days=1)
    
    return mondays

def extract_scheduling_details(user_message):
    now = datetime.now()
    
    # Get some useful dates for examples
    today = now.date()
    tomorrow = today + timedelta(days=1)
    next_monday = today + timedelta(days=(7 - today.weekday()) % 7)
    if next_monday == today:
        next_monday += timedelta(days=7)
    
    prompt = f"""
You are a world-class scheduling assistant. Convert the user's request into this JSON format:

{{
  "intent": "book" | "check_availability" | "confirm" | "clarify",
  "start_time": "YYYY-MM-DD HH:MM:SS" | null,
  "end_time": "YYYY-MM-DD HH:MM:SS" | null,
  "duration_minutes": integer | null,
  "summary": string | null,
  "reply": string | null
}}

IMPORTANT RULES:
1. If a request is ambiguous about which specific date (like "Monday July" or "next week"), use "clarify" intent
2. Only use "book" intent when the date and time are completely clear
3. For availability checks, use "check_availability" intent
4. For confirmations like "yes", "ok", "sure", use "confirm" intent

Definitions:
- "afternoon": 13:00-17:00
- "post-lunch": 13:00-15:00  
- "evening": 17:00-21:00
- "morning": 09:00-12:00
- "noon": 12:00-13:00
- "night": 21:00-23:59
- "weekend": Saturday and Sunday

Current date: {now.strftime('%A, %B %d, %Y')}

Examples:

User: "book for 5pm today"
{{
  "intent": "book",
  "start_time": "{today.strftime('%Y-%m-%d')} 17:00:00",
  "end_time": "{today.strftime('%Y-%m-%d')} 17:00:00",
  "duration_minutes": 60,
  "summary": "Meeting",
  "reply": "Booking for today at 5pm."
}}

User: "book for Monday July"
{{
  "intent": "clarify",
  "start_time": null,
  "end_time": null,
  "duration_minutes": null,
  "summary": "Meeting",
  "reply": "There are several Mondays in July 2025: July 7, 14, 21, and 28. Which specific Monday would you like to book?"
}}

User: "book for next Monday at 3pm"
{{
  "intent": "book",
  "start_time": "{next_monday.strftime('%Y-%m-%d')} 15:00:00",
  "end_time": "{next_monday.strftime('%Y-%m-%d')} 15:00:00",
  "duration_minutes": 60,
  "summary": "Meeting",
  "reply": "Booking for next Monday at 3pm."
}}

User: "any free time tomorrow afternoon?"
{{
  "intent": "check_availability",
  "start_time": "{tomorrow.strftime('%Y-%m-%d')} 13:00:00",
  "end_time": "{tomorrow.strftime('%Y-%m-%d')} 17:00:00",
  "duration_minutes": 60,
  "summary": null,
  "reply": "Checking availability tomorrow afternoon."
}}

User: "schedule something next week"
{{
  "intent": "clarify",
  "start_time": null,
  "end_time": null,
  "duration_minutes": null,
  "summary": "Meeting",
  "reply": "I'd be happy to schedule something next week! Could you specify which day and time you prefer?"
}}

User: "yes"
{{
  "intent": "confirm",
  "start_time": null,
  "end_time": null,
  "duration_minutes": null,
  "summary": null,
  "reply": "Confirming your booking."
}}

User: "book for July 15th at 2pm"
{{
  "intent": "book",
  "start_time": "2025-07-15 14:00:00",
  "end_time": "2025-07-15 14:00:00",
  "duration_minutes": 60,
  "summary": "Meeting",
  "reply": "Booking for July 15th at 2pm."
}}

User: "30 minute call tomorrow at 10am"
{{
  "intent": "book",
  "start_time": "{tomorrow.strftime('%Y-%m-%d')} 10:00:00",
  "end_time": "{tomorrow.strftime('%Y-%m-%d')} 10:00:00",
  "duration_minutes": 30,
  "summary": "Call",
  "reply": "Booking 30-minute call tomorrow at 10am."
}}

User: "{user_message}"

Respond ONLY with the JSON object. No other text.
"""
    
    try:
        response = model.generate_content(prompt)
        # Extract JSON from response
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return parsed
        return None
    except Exception as e:
        print(f"Gemini parsing error: {e}")
        print(f"Response was: {response.text}")
        return None

def find_next_available_slot(start_after, duration, same_day_only=False, max_days=14):
    """Find the next available slot after start_after"""
    search_days = 1 if same_day_only else max_days
    
    for day_offset in range(0, search_days):
        candidate_date = (start_after + timedelta(days=day_offset)).date()
        
        # Start from the specified time on the first day, 9am on subsequent days
        start_hour = start_after.hour if day_offset == 0 else 9
        start_minute = start_after.minute if day_offset == 0 else 0
        
        for hour in range(start_hour, 21):  # 9am to 9pm
            for minute in [0, 15, 30, 45]:  # Check every 15 minutes
                if hour == start_hour and minute < start_minute:
                    continue
                    
                slot_start = datetime.combine(candidate_date, dt_time(hour, minute))
                slot_end = slot_start + duration
                
                # Don't suggest slots in the past
                if slot_start < datetime.now():
                    continue
                    
                if check_availability(slot_start, slot_end):
                    return slot_start
    
    return None

def handle_schedule_request(details, session_state):
    """Handle booking requests"""
    start_window = dateparser.parse(details.get("start_time")) if details.get("start_time") else None
    end_window = dateparser.parse(details.get("end_time")) if details.get("end_time") else None
    duration = timedelta(minutes=details.get("duration_minutes", 60))
    summary = details.get("summary", "Appointment")
    now = datetime.now()

    # Specific time booking
    if start_window and (not end_window or start_window == end_window):
        # Check if slot is available
        if check_availability(start_window, start_window + duration):
            book_slot(summary, start_window, start_window + duration)
            return {
                "response": f"✅ Your appointment is booked for {start_window.strftime('%A, %B %d at %I:%M %p')}",
                "last_suggested": None
            }
        else:
            # Suggest alternatives
            if start_window.date() == now.date():
                # Try to find another slot today first
                next_slot_today = find_next_available_slot(
                    start_window + timedelta(minutes=15), 
                    duration, 
                    same_day_only=True
                )
                
                if next_slot_today:
                    suggestion = {
                        "suggested_time": next_slot_today.strftime('%Y-%m-%d %H:%M:%S'),
                        "summary": summary,
                        "duration": details.get("duration_minutes", 60)
                    }
                    return {
                        "response": f"❌ {start_window.strftime('%I:%M %p')} is unavailable. Next available today: {next_slot_today.strftime('%I:%M %p')}. Reply 'yes' to confirm.",
                        "last_suggested": suggestion,
                        **suggestion
                    }
                else:
                    # No more slots today, suggest tomorrow
                    next_slot = find_next_available_slot(
                        datetime.combine(now.date() + timedelta(days=1), dt_time(9, 0)),
                        duration,
                        same_day_only=False
                    )
                    
                    if next_slot:
                        suggestion = {
                            "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                            "summary": summary,
                            "duration": details.get("duration_minutes", 60)
                        }
                        return {
                            "response": f"❌ No more slots available today. Next available: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                            "last_suggested": suggestion,
                            **suggestion
                        }
                    else:
                        return {
                            "response": "❌ No available slots found in the next two weeks. Please try another time.",
                            "last_suggested": None
                        }
            else:
                # Future date booking - suggest next available on that day or later
                next_slot = find_next_available_slot(
                    start_window + timedelta(minutes=15),
                    duration,
                    same_day_only=True
                )
                
                if next_slot and next_slot.date() == start_window.date():
                    suggestion = {
                        "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                        "summary": summary,
                        "duration": details.get("duration_minutes", 60)
                    }
                    return {
                        "response": f"❌ {start_window.strftime('%I:%M %p')} is unavailable. Next available on {start_window.strftime('%A, %B %d')}: {next_slot.strftime('%I:%M %p')}. Reply 'yes' to confirm.",
                        "last_suggested": suggestion,
                        **suggestion
                    }
                else:
                    # No slots that day, find next available
                    next_slot = find_next_available_slot(
                        start_window + timedelta(days=1),
                        duration,
                        same_day_only=False
                    )
                    
                    if next_slot:
                        suggestion = {
                            "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                            "summary": summary,
                            "duration": details.get("duration_minutes", 60)
                        }
                        return {
                            "response": f"❌ No slots available on {start_window.strftime('%A, %B %d')}. Next available: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                            "last_suggested": suggestion,
                            **suggestion
                        }
                    else:
                        return {
                            "response": "❌ No available slots found in the next two weeks. Please try another time.",
                            "last_suggested": None
                        }

    # Time range booking (e.g., "tomorrow afternoon")
    if start_window and end_window:
        current_slot = start_window
        while current_slot + duration <= end_window:
            if check_availability(current_slot, current_slot + duration):
                suggestion = {
                    "suggested_time": current_slot.strftime('%Y-%m-%d %H:%M:%S'),
                    "summary": summary,
                    "duration": details.get("duration_minutes", 60)
                }
                return {
                    "response": f"✅ Available: {current_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                    "last_suggested": suggestion,
                    **suggestion
                }
            current_slot += timedelta(minutes=15)
        
        # No slots in range, suggest next available
        next_slot = find_next_available_slot(end_window, duration, same_day_only=False)
        if next_slot:
            suggestion = {
                "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                "summary": summary,
                "duration": details.get("duration_minutes", 60)
            }
            return {
                "response": f"❌ No available slots in that window. Next available: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                "last_suggested": suggestion,
                **suggestion
            }
        else:
            return {
                "response": "❌ No available slots found in the next two weeks. Please try another time.",
                "last_suggested": None
            }

    return {
        "response": "❌ Could not parse your request. Please try again with a specific date and time.",
        "last_suggested": None
    }

def handle_availability_check(details, session_state):
    """Handle availability check requests"""
    start_time = dateparser.parse(details["start_time"])
    end_time = dateparser.parse(details["end_time"])
    duration = timedelta(minutes=details.get("duration_minutes", 60))
    
    # Find first available slot in the window
    current_slot = start_time
    while current_slot + duration <= end_time:
        if check_availability(current_slot, current_slot + duration):
            suggestion = {
                "suggested_time": current_slot.strftime('%Y-%m-%d %H:%M:%S'),
                "summary": "Meeting",
                "duration": duration.seconds // 60
            }
            return {
                "response": f"✅ Yes, you have free time. Earliest available: {current_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to book this slot.",
                "last_suggested": suggestion,
                **suggestion
            }
        current_slot += timedelta(minutes=15)
    
    # No slots in requested window, suggest next available
    next_slot = find_next_available_slot(end_time, duration, same_day_only=False)
    if next_slot:
        suggestion = {
            "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
            "summary": "Meeting",
            "duration": duration.seconds // 60
        }
        return {
            "response": f"❌ No free time in that window. Next available: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to book this slot.",
            "last_suggested": suggestion,
            **suggestion
        }
    else:
        return {
            "response": "❌ Sorry, you are fully booked in the next two weeks.",
            "last_suggested": None
        }

def chat(state: dict) -> dict:
    """Main chat function"""
    # Get the last suggested slot from the state
    last_suggested = state.get("last_suggested")
    user_input = state.get("text", "").strip()
    
    # Extract details from user input
    details = extract_scheduling_details(user_input)
    if not details:
        return {
            "response": "Sorry, I couldn't understand your request. Please try something like 'Book a meeting tomorrow at 3 PM' or 'Do you have any free time this Friday?'",
            "last_suggested": None
        }
    
    intent = details.get("intent")
    
    # Handle confirmation
    if intent == "confirm":
        if last_suggested and last_suggested.get("suggested_time"):
            try:
                meeting_start = dateparser.parse(last_suggested["suggested_time"])
                duration = timedelta(minutes=last_suggested["duration"])
                meeting_end = meeting_start + duration
                summary = last_suggested["summary"]
                
                # Double-check availability
                if check_availability(meeting_start, meeting_end):
                    book_slot(summary, meeting_start, meeting_end)
                    return {
                        "response": f"✅ Confirmed! Your appointment is booked for {meeting_start.strftime('%A, %B %d at %I:%M %p')}",
                        "last_suggested": None
                    }
                else:
                    # Slot no longer available, suggest next
                    next_slot = find_next_available_slot(
                        meeting_start + timedelta(minutes=15),
                        duration,
                        same_day_only=False
                    )
                    
                    if next_slot:
                        suggestion = {
                            "suggested_time": next_slot.strftime('%Y-%m-%d %H:%M:%S'),
                            "summary": summary,
                            "duration": duration.seconds // 60
                        }
                        return {
                            "response": f"❌ That slot is no longer available. Next available: {next_slot.strftime('%A, %B %d at %I:%M %p')}. Reply 'yes' to confirm.",
                            "last_suggested": suggestion,
                            **suggestion
                        }
                    else:
                        return {
                            "response": "❌ Sorry, no available slots found in the next two weeks.",
                            "last_suggested": None
                        }
                        
            except Exception as e:
                print(f"Error confirming booking: {e}")
                return {
                    "response": "❌ There was an error confirming your booking. Please try again.",
                    "last_suggested": None
                }
        else:
            return {
                "response": "You haven't been offered a time to confirm. How can I help you schedule an appointment?",
                "last_suggested": None
            }
    
    # Handle clarification requests
    elif intent == "clarify":
        return {
            "response": details.get("reply", "Could you please provide more specific details about when you'd like to schedule?"),
            "last_suggested": None
        }
    
    # Handle booking requests
    elif intent == "book":
        return handle_schedule_request(details, state)
    
    # Handle availability checks
    elif intent == "check_availability":
        return handle_availability_check(details, state)
    
    # Default fallback
    else:
        return {
            "response": details.get("reply", "I'm not sure how to handle that. Can you please rephrase your request?"),
            "last_suggested": None
        }

# Create the workflow
workflow = StateGraph(dict)
workflow.add_node("chat", chat)
workflow.set_entry_point("chat")
workflow.add_edge("chat", END)
agent_app = workflow.compile()
