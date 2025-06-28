import streamlit as st
import requests

st.set_page_config(page_title="TailorTalk", layout="centered")

st.markdown("""
    <style>
        body, .stApp {
            background-color: #121212 !important;
            color: #e0e0e0 !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        h1 {
            color: #00bcd4;
            font-weight: 700;
            font-size: 3rem;
            margin-bottom: 0;
        }
        p {
            color: #b0bec5;
            font-size: 1.1rem;
            margin-top: 0;
            margin-bottom: 1.5rem;
        }
        .stChatMessage {
            background-color: #1e1e1e !important;
            border-radius: 12px !important;
            padding: 12px !important;
            margin-bottom: 8px !important;
            color: #e0e0e0 !important;
            font-size: 1rem !important;
        }
        .stChatMessage .stMarkdown {
            color: #e0e0e0 !important;
        }
        .user {
            color: #81d4fa !important;
            font-weight: 600;
        }
        .assistant {
            color: #80cbc4 !important;
            font-weight: 600;
        }
        .stButton>button {
            background-color: #00bcd4 !important;
            color: #121212 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
            cursor: pointer !important;
            transition: background-color 0.3s ease !important;
        }
        .stButton>button:hover {
            background-color: #0097a7 !important;
        }
        .stChatInput>div>div>input {
            background-color: #1e1e1e !important;
            color: #e0e0e0 !important;
            border: 1px solid #00bcd4 !important;
            border-radius: 8px !important;
            padding: 12px !important;
            font-size: 1rem !important;
        }
        .stChatInput>div>div>input::placeholder {
            color: #80deea !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h1 style="text-align:center;">🧵 TailorTalk</h1>
    <p style="text-align:center;">Gemini-powered calendar assistant</p>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_suggestion" not in st.session_state:
    st.session_state.pending_suggestion = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Book an appointment (e.g., 'tomorrow afternoon')")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {"text": prompt}
    if st.session_state.pending_suggestion and prompt.lower().strip() in ["yes", "ok", "sure", "confirm", "yep"]:
        payload["last_suggested"] = st.session_state.pending_suggestion
    else:
        payload["last_suggested"] = None

    with st.spinner("Checking calendar..."):
        try:
            # ✅ Updated to point to your Render backend
            r = requests.post("https://tailortalk-backend-t263.onrender.com/chat", json=payload)
            r.raise_for_status()
            response_data = r.json()
            reply = response_data.get("response", "❌ Failed to get a reply.")

            if "last_suggested" in response_data and response_data["last_suggested"]:
                st.session_state.pending_suggestion = response_data["last_suggested"]
            else:
                st.session_state.pending_suggestion = None

        except requests.exceptions.RequestException as e:
            reply = f"❌ Error connecting to the backend: {e}"

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()