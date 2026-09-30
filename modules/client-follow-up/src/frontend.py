import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from loguru import logger

_src = Path(__file__).resolve().parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

try:
    from meeting_summarizer.config import StyleConfig, MeetingMetadata
    from meeting_summarizer.summarizer import MeetingSummarizer
    from meeting_summarizer.docx_exporter import export_to_docx
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(page_title="Meeting Summarizer", layout="wide", page_icon="📋")
load_dotenv()

_DEFAULT_TEMPLATE_PATH = (
    Path(__file__).parent / "meeting_summarizer" / "templates" / "default_template.md"
)
_DEFAULT_TEMPLATE = (
    _DEFAULT_TEMPLATE_PATH.read_text(encoding="utf-8")
    if _DEFAULT_TEMPLATE_PATH.exists()
    else "# Meeting Summary\n\n## Attendees\n\n## Key Decisions\n\n## Action Items\n\n## Next Steps\n"
)

# --- SESSION STATE ---
for key, default in [
    ("transcript_text", None),
    ("template_text", _DEFAULT_TEMPLATE),
    ("summary", None),
    ("chat_history", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- SIDEBAR ---
st.sidebar.header("Configuration")
llm_source = st.sidebar.selectbox("LLM Source", ["Google", "Azure"])

st.sidebar.markdown("---")
st.sidebar.subheader("Meeting Info")
client_name = st.sidebar.text_input("Client name", placeholder="Acme Corp")
next_meeting_date = st.sidebar.text_input("Next meeting date", placeholder="DD/MM/YYYY or 'Por confirmar'", value="Por confirmar")
next_meeting_time = st.sidebar.text_input("Next meeting time", value="10:00h")
participants_raw = st.sidebar.text_area("Participants (one per line)", height=80, placeholder="Alice\nBob\nCarlos")

st.sidebar.markdown("---")
st.sidebar.subheader("Summary Template")
template_choice = st.sidebar.radio("Template source", ["Use default", "Upload custom"])

if template_choice == "Upload custom":
    uploaded_tpl = st.sidebar.file_uploader("Upload .md template", type=["md", "txt"])
    if uploaded_tpl:
        st.session_state.template_text = uploaded_tpl.read().decode("utf-8")
else:
    st.session_state.template_text = _DEFAULT_TEMPLATE

with st.sidebar.expander("View active template"):
    st.markdown(st.session_state.template_text)

# --- TITLE ---
st.title("Meeting Summarizer 📋")
st.markdown(
    "Upload a meeting transcription, generate a structured AI summary, "
    "refine it via chat, and download as a Word document."
)

# --- STEP 1: INPUT ---
st.header("1. Transcription Input")
tab_upload, tab_paste = st.tabs(["Upload File", "Paste Text"])

with tab_upload:
    uploaded_file = st.file_uploader("Upload .txt transcript", type=["txt"])
    if uploaded_file:
        st.session_state.transcript_text = uploaded_file.read().decode("utf-8")
        st.session_state.summary = None
        st.session_state.chat_history = []

with tab_paste:
    pasted = st.text_area("Paste transcript here", height=300, key="paste_area")
    if st.button("Use pasted text"):
        if pasted.strip():
            st.session_state.transcript_text = pasted
            st.session_state.summary = None
            st.session_state.chat_history = []
            st.rerun()

if st.session_state.transcript_text:
    with st.expander("View loaded transcript", expanded=False):
        st.text_area(
            "Transcript",
            st.session_state.transcript_text,
            height=300,
            key="transcript_viewer",
            disabled=True,
        )

# --- STEP 2: GENERATE ---
if st.session_state.transcript_text:
    st.markdown("---")
    st.header("2. Generate Summary")

    if st.button("Generate Summary", type="primary"):
        with st.spinner("Generating summary with AI..."):
            try:
                summarizer = MeetingSummarizer(source=llm_source)
                st.session_state.summary = summarizer.generate_summary(
                    st.session_state.transcript_text,
                    st.session_state.template_text,
                )
                st.session_state.chat_history = []
                st.session_state["summary_editor"] = st.session_state.summary
                st.rerun()
            except Exception as e:
                st.error(f"Generation failed: {e}")
                logger.error(e)

# --- STEP 3: INTERACT ---
if st.session_state.summary:
    st.markdown("---")
    st.header("3. Review & Refine")

    user_input = st.chat_input(
        "Ask a question about the meeting, or request a change to the summary"
    )
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("Processing..."):
            try:
                summarizer = MeetingSummarizer(source=llm_source)
                first_word = user_input.strip().lower().split()[0] if user_input.strip() else ""
                is_question = "?" in user_input or first_word in {
                    "who", "what", "when", "where", "why", "how",
                    "did", "was", "were", "is", "are", "can", "could",
                }
                if is_question:
                    response = summarizer.ask_question(
                        user_input,
                        st.session_state.transcript_text,
                        history=st.session_state.chat_history[:-1],
                    )
                else:
                    st.session_state.summary = summarizer.refine_summary(
                        user_input,
                        st.session_state.summary,
                        st.session_state.transcript_text,
                        history=st.session_state.chat_history[:-1],
                    )
                    response = "Summary updated."
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": response}
                )
                if response == "Summary updated.":
                    st.session_state["summary_editor"] = st.session_state.summary
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")
                logger.error(e)

    if st.session_state.chat_history:
        with st.expander("Conversation History", expanded=True):
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])

    col_edit, col_preview = st.columns(2)
    with col_edit:
        st.subheader("Edit (Markdown)")
        edited = st.text_area(
            "Summary markdown",
            st.session_state.summary,
            height=500,
            key="summary_editor",
        )
        if edited != st.session_state.summary:
            st.session_state.summary = edited

    with col_preview:
        st.subheader("Preview")
        st.markdown(st.session_state.summary)

    # --- STEP 4: EXPORT ---
    st.markdown("---")
    st.header("4. Export")
    try:
        participants = [p.strip() for p in participants_raw.splitlines() if p.strip()]
        metadata = MeetingMetadata(
            client_name=client_name,
            next_meeting_date=next_meeting_date,
            next_meeting_time=next_meeting_time,
            participants=participants,
        ) if client_name else None
        docx_bytes = export_to_docx(st.session_state.summary, StyleConfig(), metadata=metadata)
        st.download_button(
            label="⬇ Download .docx",
            data=docx_bytes,
            file_name="meeting_summary.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )
    except Exception as e:
        st.error(f"Export failed: {e}")
        logger.error(e)
