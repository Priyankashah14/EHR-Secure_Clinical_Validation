import os

import streamlit as st
import requests

# In Docker, set API_BASE_URL to the API service name (e.g. http://api:8000)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_CHAT_URL = f"{API_BASE_URL}/api/v1/chat"
API_PATIENTS_URL = f"{API_BASE_URL}/api/v1/patients"

st.set_page_config(page_title="Zero-Trust Clinical EHR", layout="centered")
st.title("🏥 Enterprise EHR Chat")
st.caption("Protected by Presidio Zero-Trust & NeMo Guardrails")

# --- FETCH PATIENTS DYNAMICALLY ---
@st.cache_data(ttl=300) # Cache the list for 5 minutes to reduce database load
def fetch_patient_list():
    # Raises on failure so errors are shown and not cached
    response = requests.get(API_PATIENTS_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(f"API database error: {data['error']}")
    return data.get("patients") or ["No patients found"]

try:
    patient_list = fetch_patient_list()
except Exception as e:
    st.sidebar.error(f"Could not load patients from {API_PATIENTS_URL}: {e}")
    patient_list = []

# Streamlit's selectbox is automatically searchable!
patient_id = st.sidebar.selectbox("Select Patient File (Type to search)", patient_list)
st.sidebar.info(f"🔒 Database explicitly locked to Patient: {patient_id}")

# --- CHAT MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# --- CHAT INPUT & API CALL ---
if prompt := st.chat_input(f"Ask about patient {patient_id}'s history..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    payload = {
        "patient_id": patient_id,
        "messages": st.session_state.messages
    }

    with st.spinner("Analyzing securely..."):
        try:
            response = requests.post(API_CHAT_URL, json=payload)
            response.raise_for_status()
            bot_reply = response.json().get("llm_response")
            
            # Enforce Output Disclaimer
            bot_reply += "\n\n*⚠️ AI generated summary. Do not use for diagnostic purposes.*"
            
        except requests.exceptions.RequestException as e:
            bot_reply = f"❌ API Error: {e}"

    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    st.chat_message("assistant").write(bot_reply)