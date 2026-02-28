import streamlit as st
import os
import csv
import json
import base64
from anthropic import Anthropic

st.set_page_config(page_title="Pharmacy Assistant", page_icon="💊")

api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key) if api_key else None

st.title("💊 Pharmacy Prescription Assistant")

with st.sidebar:
    st.header("About")
    st.info("Extracts medicines, checks stock, flags issues, and drafts patient instructions.")

def load_inventory():
    inventory = {}
    try:
        with open("inventory.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row["medicine_name"].lower().strip()
                inventory[key] = row
    except FileNotFoundError:
        st.warning("inventory.csv not found.")
    return inventory

def check_stock(medicines_list, inventory):
    results = []
    for med in medicines_list:
        med_name = med.get("name", "").lower().strip()
        matched = None
        for key in inventory:
            if any(word in key for word in med_name.split() if len(word) > 3):
                matched = inventory[key]
                break
        if matched:
            qty = int(matched["stock_quantity"])
            if qty == 0:
                status = "❌ Out of Stock"
            elif qty < 20:
                status = f"⚠️ Low Stock ({qty} left)"
            else:
                status = f"✅ In Stock ({qty} left)"
            results.append({
                "medicine": med.get("name"),
                "status": status,
                "alternative": matched["alternative"] if qty == 0 else None
            })
        else:
            results.append({
                "medicine": med.get("name"),
                "status": "🔍 Not found in system",
                "alternative": None
            })
    return results

def run_analysis(prescription_text, language):
    inventory = load_inventory()

    with st.spinner("Step 1: Extracting medicines..."):
        extraction = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": f"""Extract all medicines from this prescription and return ONLY a JSON array.
Each item must have: name, dosage, frequency, duration.
Return ONLY the JSON array, no other text.

Prescription:
{prescription_text}

Example format:
[{{"name": "Metformin 500mg", "dosage": "500mg", "frequency": "twice daily", "duration": "30 days"}}]"""
            }]
        )

    try:
        raw = extraction.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        medicines = json.loads(raw.strip())
    except Exception as e:
        st.error(f"Could not parse medicine list: {e}")
        st.stop()

    stock_results = check_stock(medicines, inventory)

    if language == "Tamil":
        language_instruction = "Write the patient instructions section in Tamil language. Use clear, natural Tamil. Max 3 lines per medicine."
    elif language == "Tamil (Simplified)":
        language_instruction = """Write the patient instructions in Tamil language for elderly or low-literacy patients.
    Rules:
    - Maximum 2 very short sentences per medicine
    - No medical jargon whatsoever — use only words a 70-year-old village elder would know
    - Use the most basic Tamil vocabulary possible
    - Include ONLY: what the medicine is for, when to take it, one key warning
    - Do NOT include brand names, drug class names, or dosage numbers in the instructions"""
    else:
        language_instruction = "Write the patient instructions in simple English, max 3 lines per medicine."


    with st.spinner("Step 2: Full prescription analysis..."):
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""You are an assistant for a retail pharmacy in Chennai, India.

Analyse this prescription:

{prescription_text}

{language_instruction}

Respond in this format:

**⚠️ Pre-Dispensing Safety Check:**
[Allergy status and critical flags — always first]

**💊 Medicines Extracted:**
[Name, dosage, frequency, duration]

**🚩 Flags / Notes:**
[Missing info, concerns, follow-up needed]

**👋 Patient Instructions:**
[Simple instructions, max 3 lines per medicine]"""
            }]
        )

    with st.spinner("Step 3: Generating sign-off checklist..."):
        checklist_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"""Based on this prescription, generate exactly 5 specific sign-off checklist items for the pharmacist to verify before dispensing.

Prescription:
{prescription_text}

Rules:
- Each item must be specific to THIS prescription, not generic
- Start each item with a verb (Confirmed, Verified, Checked, Asked, Counselled)
- Return ONLY a JSON array of 5 strings, no other text

Example format:
["Confirmed patient has no allergy to Metformin or sulfa drugs", "Verified kidney function test done in last 3 months"]"""
            }]
        )

    try:
        raw = checklist_response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        checklist_items = json.loads(raw.strip())
    except:
        checklist_items = [
            "Confirmed allergy status with patient",
            "Verified all medicines are in stock",
            "Checked dosing instructions are complete",
            "Counselled patient on key side effects",
            "Confirmed patient understands when to return"
        ]

    # Store everything in session state
    st.session_state.analysis_done = True
    st.session_state.stock_results = stock_results
    st.session_state.analysis_text = message.content[0].text
    st.session_state.checklist_items = checklist_items

def display_results():
    stock_results = st.session_state.stock_results
    analysis_text = st.session_state.analysis_text
    checklist_items = st.session_state.checklist_items

    st.markdown("---")
    st.markdown("### 📦 Stock Check")
    for item in stock_results:
        if "Out of Stock" in item["status"]:
            st.error(f"**{item['medicine']}** — {item['status']}")
            if item["alternative"]:
                st.info(f"💊 Suggested alternative: **{item['alternative']}**")
        elif "Low Stock" in item["status"]:
            st.warning(f"**{item['medicine']}** — {item['status']}")
        elif "In Stock" in item["status"]:
            st.success(f"**{item['medicine']}** — {item['status']}")
        else:
            st.info(f"**{item['medicine']}** — {item['status']}")

    st.markdown("---")
    st.markdown(analysis_text)

    # WhatsApp button
    st.markdown("---")
    st.markdown("### 📲 Send to Patient via WhatsApp")

    patient_phone = st.text_input(
        "Patient mobile number (with country code)",
        placeholder="919884262888",
        help="Include country code without + sign. India = 91xxxxxxxxxx"
    )

    if patient_phone:
        # Extract just the patient instructions from the analysis
        analysis = st.session_state.analysis_text
        if "Patient Instructions" in analysis or "👋" in analysis:
            lines = analysis.split("\n")
            instructions_start = next(
                (i for i, l in enumerate(lines) if "Patient Instructions" in l or "👋" in l),
                0
            )
            patient_message = "\n".join(lines[instructions_start:]).strip()
        else:
            patient_message = analysis

        # Clean up markdown symbols for WhatsApp
        clean_message = patient_message.replace("**", "*").replace("###", "").replace("##", "")

        import urllib.parse
        encoded = urllib.parse.quote(clean_message)
        whatsapp_url = f"https://wa.me/{patient_phone}?text={encoded}"

        st.link_button("📲 Open WhatsApp with Message", whatsapp_url)
        st.caption("This will open WhatsApp Web with the patient instructions pre-filled. Review before sending.")

    st.markdown("---")
    st.markdown("### ✅ Pharmacist Sign-Off")
    st.caption("Complete all checks before dispensing. This cannot be skipped.")

    all_checked = True
    for i, item in enumerate(checklist_items):
        checked = st.checkbox(item, key=f"check_{st.session_state.get('active_tab', 'tab1')}_{i}")
        if not checked:
            all_checked = False

    st.markdown("")
    if all_checked:
        st.success("### 🟢 CLEAR TO DISPENSE")
        st.balloons()
    else:
        st.error("### 🔴 Complete all checks above before dispensing")

def extract_text_from_file(uploaded_file):
    file_bytes = uploaded_file.read()
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    if uploaded_file.type == "application/pdf":
        content = [
            {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}
            },
            {
                "type": "text",
                "text": "This is a prescription document. Please transcribe ALL text you can see exactly as written, including patient name, doctor name, medicines, dosages, and instructions. Return only the transcribed text."
            }
        ]
    else:
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": uploaded_file.type, "data": b64}
            },
            {
                "type": "text",
                "text": "This is a photo of a handwritten prescription. Please transcribe ALL text you can see exactly as written, including patient name, doctor name, medicines, dosages, and instructions. Return only the transcribed text."
            }
        ]

    with st.spinner("Reading prescription image..."):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": content}]
        )

    return response.content[0].text

# Initialise session state
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# --- TABS ---
tab1, tab2 = st.tabs(["⌨️ Type Prescription", "📷 Upload Prescription"])

with tab1:
    prescription_text = st.text_area(
        "Paste Prescription Details Here:",
        height=200,
        placeholder="Patient: Ramesh Kumar, 45M..."
    )
    language = st.radio("Patient instructions language:", ["English", "Tamil", "Tamil (Simplified)"], key="lang_tab1")

    if st.checkbox("Show Sample Prescription"):
        sample = """Patient: Ramesh Kumar, 45M
Dr. Priya Sharma, Apollo Clinic
1. Metformin 500mg - twice daily after meals - 30 days
2. Amlodipine 5mg - once daily morning - 30 days
3. Pantop 40 - before breakfast - 15 days
4. Vit D3 sachet - once weekly"""
        st.code(sample)

    if st.button("Analyse Prescription", key="analyse_tab1"):
        if not client:
            st.error("API Key not found.")
        elif not prescription_text.strip():
            st.warning("Please paste a prescription first.")
        else:
            st.session_state.analysis_done = False
            st.session_state.active_tab = "tab1"
            run_analysis(prescription_text, language)


with tab2:
    st.markdown("**Upload a photo or scanned PDF of a handwritten prescription.**")
    uploaded_file = st.file_uploader(
        "Choose file",
        type=["jpg", "jpeg", "png", "pdf"],
        help="Photo of handwritten prescription or scanned PDF"
    )
    language2 = st.radio("Patient instructions language:", ["English", "Tamil", "Tamil (Simplified)"], key="lang_tab2")

    if uploaded_file is not None:
        if uploaded_file.type != "application/pdf":
            st.image(uploaded_file, caption="Uploaded prescription", width=400)

        if st.button("Analyse Prescription", key="analyse_tab2"):
            if not client:
                st.error("API Key not found.")
            else:
                st.session_state.analysis_done = False
                st.session_state.active_tab = "tab2"
                transcribed = extract_text_from_file(uploaded_file)
                with st.expander("📝 Transcribed text (review for accuracy)"):
                    st.write(transcribed)
                run_analysis(transcribed, language2)

# Results always displayed once, outside tabs
if st.session_state.analysis_done:
        display_results()