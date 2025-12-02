import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from pptx import Presentation
from gtts import gTTS  # <-- Vi använder den stabila Google-rösten
import tempfile
import os

# --- INSTÄLLNINGAR ---
st.set_page_config(page_title="Jag Lär Mig", page_icon="📖", layout="wide")

# --- SESSIONS-HANTERING ---
if "subjects" not in st.session_state:
    st.session_state.subjects = {"Allmänt": ""}
if "current_subject" not in st.session_state:
    st.session_state.current_subject = "Allmänt"

# --- FUNKTIONER ---

def extract_text_from_pdf(pdf_file):
    text = ""
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_pptx(pptx_file):
    prs = Presentation(pptx_file)
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

# Den stabila ljudfunktionen (gTTS)
def generate_speech_simple(text):
    try:
        # Skapar ljud på svenska
        tts = gTTS(text=text, lang='sv')

        # Spara till en tillfällig fil
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        st.error(f"Kunde inte skapa ljud: {e}")
        return None

def get_gemini_response(prompt, context, api_key):
    if not api_key: return "⚠️ Ingen API-nyckel inlagd."

    genai.configure(api_key=api_key)
    system_instruction = (
        "Du är en smart och pedagogisk studiecoach i appen 'Jag Lär Mig'. "
        "Din uppgift är att hjälpa användaren att förstå sitt studiematerial. "
        "Var tydlig, uppmuntrande och svara alltid på svenska."
    )
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)

    full_prompt = f"Studiematerial:\n{context}\n\nUppgift/Fråga: {prompt}"
    return model.generate_content(full_prompt).text

# --- SIDOPANEL (MENY) ---
with st.sidebar:
    st.title("📖 Jag Lär Mig")

    api_key = st.text_input("Nyckel (API Key)", type="password")

    st.divider()

    st.subheader("📂 Mina Ämnen")
    subject_list = list(st.session_state.subjects.keys())

    selected_sub = st.selectbox("Välj ämne:", subject_list, index=subject_list.index(st.session_state.current_subject))
    st.session_state.current_subject = selected_sub

    new_sub = st.text_input("Nytt ämne:")
    if st.button("Skapa mapp") and new_sub:
        st.session_state.subjects[new_sub] = ""
        st.session_state.current_subject = new_sub
        st.success(f"Mappen '{new_sub}' skapad!")
        st.rerun()

    st.divider()

    st.subheader(f"📥 Ladda upp till: {st.session_state.current_subject}")
    uploaded_files = st.file_uploader("Filer (PDF, PPTX)", accept_multiple_files=True)

    if st.button("Spara materialet"):
        text_data = st.session_state.subjects[st.session_state.current_subject]
        count = 0
        for file in uploaded_files:
            if file.name.endswith(".pdf"):
                text_data += f"\n--- {file.name} ---\n" + extract_text_from_pdf(file)
                count += 1
            elif file.name.endswith(".pptx"):
                text_data += f"\n--- {file.name} ---\n" + extract_text_from_pptx(file)
                count += 1

        st.session_state.subjects[st.session_state.current_subject] = text_data
        st.success(f"Sparade {count} filer!")

# --- HUVUDVY ---
st.header(f"Studerar: {st.session_state.current_subject}")

current_material = st.session_state.subjects[st.session_state.current_subject]

if not current_material:
    st.info("👈 Börja med att ladda upp material i menyn!")
else:
    tab1, tab2, tab3 = st.tabs(["📝 Material", "🎧 Lyssna", "💬 Förhör"])

    # FLIK 1: REDIGERA
    with tab1:
        st.subheader("Ditt material")
        edited_text = st.text_area("Innehåll", current_material, height=300)

        if st.button("Spara ändringar"):
            st.session_state.subjects[st.session_state.current_subject] = edited_text
            st.success("Uppdaterat!")
            st.rerun()

        if st.button("✨ Dela upp i kapitel (AI)"):
            with st.spinner("Analyserar..."):
                chapters = get_gemini_response(
                    "Dela upp texten i tydliga kapitel med rubriker.", 
                    edited_text, api_key
                )
                st.markdown(chapters)

    # FLIK 2: LYSSNA (NU MED gTTS)
    with tab2:
        st.subheader("Uppläsning")

        text_to_read = st.text_area("Text att läsa upp:", value=edited_text[:3000], height=150)

        if st.button("▶️ Spela upp"):
            with st.spinner("Skapar ljud..."):
                # Här använder vi den enkla, säkra funktionen
                audio_path = generate_speech_simple(text_to_read)
                if audio_path:
                    st.audio(audio_path, format="audio/mp3")

    # FLIK 3: CHATT
    with tab3:
        st.subheader("Plugga med AI")

        c1, c2 = st.columns(2)
        if c1.button("Skapa prov"):
            with st.spinner("Skapar prov..."):
                test = get_gemini_response("Skapa ett prov med 5 frågor + facit.", edited_text, api_key)
                st.markdown(test)

        if c2.button("Sammanfatta"):
            with st.spinner("Sammanfattar..."):
                summary = get_gemini_response("Sammanfatta det viktigaste.", edited_text, api_key)
                st.markdown(summary)

        st.divider()
        user_q = st.chat_input("Ställ en fråga...")
        if user_q:
            st.chat_message("user").write(user_q)
            with st.spinner("Tänker..."):
                ans = get_gemini_response(user_q, edited_text, api_key)
                st.chat_message("assistant").write(ans)
