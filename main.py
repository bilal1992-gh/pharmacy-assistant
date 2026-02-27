import streamlit as st
from anthropic import Anthropic

st.title("Anthropic Streamlit App")

st.write("Hello! This is a simple Streamlit app using the Anthropic API.")

# Add more functionality as needed
import os
import anthropic
import streamlit as st

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

st.title("💊 Pharmacy Prescription Assistant")
st.write("Paste a prescription below and get an instant summary + WhatsApp draft reply.")

prescription_input = st.text_area("Paste prescription text here:", height=200)

if st.button("Analyse Prescription"):
    if not prescription_input.strip():
        st.warning("Please paste a prescription first.")
    else:
        with st.spinner("Analysing..."):
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are an assistant for a retail pharmacy in Chennai, India.

A patient has submitted the following prescription. Please:
1. Extract each medicine with dosage and duration
2. Flag any unclear or potentially risky items
3. Draft a friendly WhatsApp reply to the patient confirming their order and any notes

Prescription:
{prescription_input}

Respond in this format:
**Medicines Extracted:**
[list each medicine, dosage, duration]

**Flags / Notes:**
[anything unclear, missing, or worth flagging for pharmacist review]

**WhatsApp Draft Reply:**
[friendly message to send to patient]"""
                    }
                ]
            )

        st.markdown(message.content[0].text)