import streamlit as st
import os
from anthropic import Anthropic

# Page configuration
st.set_page_config(page_title="Pharmacy Assistant", page_icon="💊")

# Initialize Anthropic client
# In a real app, this should be in secrets. 
# For this demo, we check for ANTHROPIC_API_KEY env var.
api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key) if api_key else None

st.title("💊 Pharmacy Prescription Assistant")

if not api_key:
    st.warning("Please set your ANTHROPIC_API_KEY in the Secrets tab to enable AI features.")

# Sidebar for instructions/info
with st.sidebar:
    st.header("About")
    st.info("This assistant helps extract medicine details, flags potential issues, and drafts patient-friendly instructions.")

# Input area
prescription_text = st.text_area(
    "Paste Prescription Details Here:",
    height=200,
    placeholder="Patient: Ramesh Kumar, 45M..."
)

if st.button("Analyze Prescription") and prescription_text:
    if not client:
        st.error("API Key not found. Please add it to your environment variables.")
    else:
        with st.spinner("Analyzing prescription..."):
            try:
                # Construct the prompt
                prompt = f"""You are a helpful pharmacy assistant. Analyze the following prescription and provide:
1. **Medicine Details**: Extract name, dosage, frequency, and duration for each item.
2. **Flag Issues**: Identify any missing information or potential concerns (e.g., missing duration, unclear instructions).
3. **Patient Instructions**: Draft a friendly message to the patient explaining how to take their medications in simple terms.

Prescription:
{prescription_text}
"""
                
                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Display results
                st.markdown("### Analysis Results")
                st.write(message.content[0].text)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# Sample data helper
if st.checkbox("Show Sample Prescription"):
    sample = """Patient: Ramesh Kumar, 45M
Dr. Priya Sharma, Apollo Clinic

1. Metformin 500mg - twice daily after meals - 30 days
2. Amlodipine 5mg - once daily morning - 30 days
3. Pantop 40 - before breakfast - 15 days
4. Vit D3 sachet - once weekly"""
    st.code(sample)
