# Design Spec: Meeting Summarizer (Part3)

**Date:** 2026-05-29  
**Status:** Approved  

---

## Overview

Part3 receives a plain-text meeting transcription and a markdown template that defines the desired summary structure. An LLM generates a structured markdown summary following the template. The user can then ask questions about the meeting, refine the summary via natural language, and download the final result as a styled Word document (`.docx`).

---

## Directory Structure

```
Part3/
├── run_frontend.py                    # Entry point: streamlit run run_frontend.py
├── .env                               # LLM API keys (same vars as Part1)
├── src/
│   └── meeting_summarizer/
│       ├── config.py                  # build_llm() factory + StyleConfig dataclass
│       ├── summarizer.py              # MeetingSummarizer class (LangChain chains)
│       ├── docx_exporter.py           # Markdown → .docx renderer with configurable styles
│       ├── templates/
│       │   └── default_template.md    # Default meeting summary template
│       └── frontend.py                # Streamlit app
```

---

## Components

### `config.py`

Two responsibilities:

1. **`build_llm(source, temperature)`** — same factory pattern as Part1. Supports `"Azure"` (AzureChatOpenAI) and `"Google"` (ChatGoogleGenerativeAI). Defaults to Google Gemini 2.5 Pro (large context window, handles full transcriptions without chunking).

2. **`StyleConfig`** — Python dataclass with all document style parameters and sensible defaults. Changing company branding means editing values in this one dataclass.

```python
@dataclass
class StyleConfig:
    # Fonts
    body_font: str = "Calibri"
    heading_font: str = "Calibri"
    # Font sizes (pt)
    title_size: int = 24
    heading1_size: int = 16
    heading2_size: int = 13
    heading3_size: int = 11
    body_size: int = 11
    # Colors (hex, no #)
    title_color: str = "2E74B5"
    heading1_color: str = "2E74B5"
    heading2_color: str = "404040"
    heading3_color: str = "595959"
    body_color: str = "000000"
    # Layout
    margin_cm: float = 2.54
```

---

### `summarizer.py`

**`MeetingSummarizer`** class with three public methods, each backed by a LangChain chain using `ChatPromptTemplate` + `MessagesPlaceholder` for history:

| Method | Purpose | Returns |
|---|---|---|
| `generate_summary(transcription, template)` | Initial summary following the template structure | `str` (markdown) |
| `ask_question(question, transcription, history)` | Q&A grounded in the meeting content | `str` |
| `refine_summary(instruction, current_summary, transcription, history)` | Modifies summary per natural language instruction | `str` (updated markdown) |

- Single LLM instance (no cheap/expensive split — no chunking needed).
- `history` is `List[Dict]` with `role`/`content` keys, converted to `HumanMessage`/`AIMessage` internally (same pattern as Part1's `_convert_history_to_messages`).
- The system prompt for `generate_summary` instructs the LLM to produce valid markdown with the sections defined in the template.

---

### `docx_exporter.py`

**`export_to_docx(markdown_text: str, style_config: StyleConfig) -> bytes`**

- Uses `python-docx` only — no external pandoc binary required.
- Parses markdown line by line:
  - `# Title` → Word Title style with `title_color`
  - `## Heading` → Heading 1 with `heading1_color`
  - `### Subheading` → Heading 2 with `heading2_color`
  - `- item` / `* item` → bulleted list paragraph
  - `**bold**` inline → bold run within a paragraph
  - Blank line → paragraph break
  - Everything else → Normal paragraph
- Applies `StyleConfig` values (font family, size, color) to each element.
- Returns `bytes` (in-memory `BytesIO`) so Streamlit can serve it directly as a download without writing to disk.

---

### `templates/default_template.md`

Ready-to-use template that users can override by uploading their own `.md` file:

```markdown
# Meeting Summary

## 1. Attendees
List all people present in the meeting.

## 2. Meeting Objective
The stated purpose or agenda of the meeting.

## 3. Key Discussion Points
Main topics discussed, with brief context.

## 4. Decisions Made
Decisions that were agreed upon, with rationale if mentioned.

## 5. Action Items
Tasks assigned during the meeting. For each: responsible person, description, and deadline if mentioned.

## 6. Next Steps
What happens after this meeting — follow-up meetings, deliverables, dependencies.
```

---

### `frontend.py` — Streamlit App

**Sidebar:**
- Template selector: "Use default" or upload custom `.md` file
- LLM source selector: Google / Azure (maps to `build_llm(source=...)`)

**Step 1 — Transcription Input:**
- Two tabs: "Upload File" (`.txt`) and "Paste Text" (same pattern as Part1 Mode 2)
- Shows transcript preview in a collapsed expander once loaded

**Step 2 — Generate Summary:**
- "Generate Summary" button → spinner → calls `summarizer.generate_summary()`
- Result stored in `st.session_state.summary`
- Rendered as markdown preview (collapsed) + editable text area

**Step 3 — Interact:**
- `st.chat_input` for both Q&A and summary refinement
  - User messages starting with a question word / "?" → routed to `ask_question()`
  - Other messages → routed to `refine_summary()`
  - Responses shown in chat bubbles
- Shared `chat_history` in session state for both modes
- Conversation history expander (same as Part1)
- Manual edit: editable text area synced with `st.session_state.summary`

**Step 4 — Export:**
- "Download .docx" button → calls `export_to_docx()` → `st.download_button` with bytes output
- Filename defaults to `meeting_summary.docx`

---

## Session State Keys

| Key | Type | Description |
|---|---|---|
| `transcript_text` | `str` | Raw transcription content |
| `template_text` | `str` | Active template markdown |
| `summary` | `str` | Current summary markdown |
| `chat_history` | `List[Dict]` | Shared Q&A + refinement history |

---

## Environment Variables (`.env`)

Same as Part1:
- `GOOGLE_API_KEY` — for Gemini
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` — for Azure
- `LANGCHAIN_API_KEY` (optional) — LangSmith tracing

---

## Dependencies

New additions over Part1:
- `python-docx` — Word document generation
- `streamlit` — already used in Part1

No new external binaries required.
