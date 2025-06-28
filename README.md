# TailorTalk - AI Scheduling Assistant

A powerful AI-powered scheduling assistant built with Streamlit and Google Gemini that helps you book meetings, check availability, and manage your calendar effortlessly through natural language conversations.

## Features

- Advanced AI Natural Language Processing - Book meetings using conversational language powered by Google Gemini
- Real-time Google Calendar Integration - Instant availability checking and booking
- Smart Time Suggestions - Get alternative slots when your preferred time is unavailable
- Interactive Chat Interface - Conversational UI with suggestion buttons and feedback
- Modern Dark Theme - Clean, professional interface optimized for productivity
- Instant Responses - Fast calendar checking and booking confirmation
- Context Memory - Remembers conversation context for seamless follow-ups
- Responsive Design - Works perfectly on desktop and mobile devices

## Installation & Setup

### Prerequisites
- Python 3.8+
- Google Calendar API credentials
- Google Gemini API key
- Git for cloning

### Steps
1. Clone the Repository
   git clone https://github.com/priyanshuu16/TailorTalk.git
   cd TailorTalk

2. Install Dependencies
   pip install -r requirements.txt

3. Set Up Environment Variables
   Create a .env file in the root directory:
   GEMINI_API_KEY=your_gemini_api_key_here
   GOOGLE_CALENDAR_ID=your_calendar_id@gmail.com
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

4. Configure Google Calendar API
   - Go to Google Cloud Console
   - Create a new project or select existing one
   - Enable the Google Calendar API
   - Create a service account and download the JSON key file
   - Share your Google Calendar with the service account email

5. Get Gemini API Key
   - Visit Google AI Studio
   - Create a new API key
   - Add it to your .env file

6. Run the Application
   streamlit run app.py

## Usage Examples

TailorTalk understands natural language. Try these commands:

Basic Booking:
- "Book a meeting tomorrow at 3 PM"
- "Schedule a call today at 5 PM"
- "Book a 30-minute meeting next Monday at 10 AM"

Availability Checking:
- "Any free time this Friday?"
- "Do I have availability tomorrow afternoon?"
- "Check my schedule for next week"

Range-based Scheduling:
- "Book something between 3-5 PM next week"
- "Schedule a meeting tomorrow afternoon"
- "Find time for a call next Friday morning"

## Project Structure

TailorTalk/
├── app.py                    # Main Streamlit frontend application
├── backend/
│   ├── agent.py             # AI agent with Gemini integration
│   ├── calendar_utils.py    # Google Calendar API functions
│   └── main.py             # FastAPI backend server (optional)
├── requirements.txt         # Python dependencies
├── .env                    # Environment variables (create this)
├── README.md              # Project documentation
└── .gitignore            # Git ignore file

## Technologies Used

- Frontend Framework: Streamlit
- AI/NLP Engine: Google Gemini 1.5 Flash
- Calendar Integration: Google Calendar API
- Backend Framework: FastAPI (optional)
- Date Parsing: dateparser, python-dateutil
- State Management: LangGraph
- Deployment: Streamlit Community Cloud
- Authentication: Google Service Account

## Key Features

Smart Time Parsing:
- Understands natural language like "tomorrow afternoon", "next Friday at 3", "post-lunch"
- Handles relative dates and time ranges
- Clarifies ambiguous requests

Intelligent Suggestions:
- Suggests alternative times when requested slots are busy
- Prioritizes same-day alternatives before suggesting future dates
- Provides contextual follow-up suggestions

Conversation Memory:
- Remembers the last suggested time slot for confirmations
- Handles "yes/no" responses contextually
- Maintains conversation flow across multiple interactions

## Deployment

Deploy to Streamlit Community Cloud:
1. Push your code to GitHub
2. Visit share.streamlit.io
3. Connect your GitHub repository
4. Set app.py as the main file
5. Add environment variables in Streamlit settings
6. Deploy and share your link

## Contributing

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## Troubleshooting

Common Issues:
- "API key not found": Check your .env file and ensure GEMINI_API_KEY is set
- "Calendar not accessible": Verify your service account has calendar access
- "Slow responses": Check your internet connection and API quotas
- "Date parsing errors": Ensure dateparser is installed correctly

Performance Tips:
- Use specific date ranges for faster slot searching
- Limit calendar search to relevant time windows
- Cache frequently accessed calendar data

## License

This project is licensed under the MIT License.

## Acknowledgments

- Google Gemini for powerful AI capabilities
- Streamlit for the amazing web framework
- Google Calendar API for seamless calendar integration
- LangGraph for state management
- dateparser for natural language date parsing

## Contact & Support

- GitHub Issues: Report bugs or request features
- Email: priyanshuraj16@yahoo.com


Star this repository if TailorTalk helped you manage your schedule better!
