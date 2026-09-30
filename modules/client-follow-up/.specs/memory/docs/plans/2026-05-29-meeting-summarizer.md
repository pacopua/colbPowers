# Meeting Summarizer (Part3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Feature Reference:** New standalone module (Part3) — Meeting Summarizer. Not yet listed in features.md (file does not exist).

**Goal:** Build a Streamlit app that takes a meeting transcription + a markdown template, generates a structured AI summary via LangChain, supports Q&A and natural language refinement, and exports to a styled .docx Word document.

**Architecture:** Single LangChain `MeetingSummarizer` class with three chains (generate, ask, refine) backed by Google Gemini 2.5 Pro (configurable). A `docx_exporter` converts the markdown output to a Word document using `python-docx` with a `StyleConfig` dataclass for easy company branding. A Streamlit frontend ties everything together.

**Tech Stack:** Python 3.11+, `uv` (package manager), LangChain (`langchain-core`, `langchain-google-genai`, `langchain-openai`), `python-docx`, `streamlit`, `loguru`, `python-dotenv`, `pytest`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `Part3/pyproject.toml` | Create | Project metadata, dependencies, pytest config |
| `Part3/src/meeting_summarizer/__init__.py` | Create | Package marker |
| `Part3/src/meeting_summarizer/config.py` | Create | `StyleConfig` dataclass + `build_llm()` factory |
| `Part3/src/meeting_summarizer/summarizer.py` | Create | `MeetingSummarizer` class (3 LangChain chains) |
| `Part3/src/meeting_summarizer/docx_exporter.py` | Create | `export_to_docx(markdown, style_config) -> bytes` |
| `Part3/src/meeting_summarizer/templates/default_template.md` | Create | Default meeting summary structure |
| `Part3/src/frontend.py` | Create | Streamlit app |
| `Part3/run_frontend.py` | Create | Entry point launcher |
| `Part3/tests/__init__.py` | Create | Package marker |
| `Part3/tests/conftest.py` | Create | Empty — path is handled by `pyproject.toml` |
| `Part3/tests/test_config.py` | Create | Unit tests for `StyleConfig` |
| `Part3/tests/test_docx_exporter.py` | Create | Unit tests for `export_to_docx` |
| `Part3/tests/test_summarizer.py` | Create | Unit tests for `MeetingSummarizer` (fake LLM) |

---

## Task 1: Project Scaffold + uv Setup

**Files:**
- Create: `Part3/pyproject.toml`
- Create: `Part3/src/meeting_summarizer/__init__.py`
- Create: `Part3/tests/__init__.py`
- Create: `Part3/tests/conftest.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p Part3/src/meeting_summarizer/templates
mkdir -p Part3/tests
```

- [ ] **Step 2: Create `Part3/pyproject.toml`**

```toml
[project]
name = "meeting-summarizer"
version = "0.1.0"
description = "Meeting transcription to Word document summarizer"
requires-python = ">=3.11"
dependencies = [
    "python-docx>=1.1.0",
    "langchain-core>=0.3.0",
    "langchain-google-genai>=2.0.0",
    "langchain-openai>=0.2.0",
    "streamlit>=1.40.0",
    "loguru>=0.7.0",
    "python-dotenv>=1.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Install dependencies with uv**

```bash
cd Part3 && uv sync
```
Expected: uv creates `.venv/`, installs all dependencies, generates `uv.lock`

- [ ] **Step 4: Create `Part3/src/meeting_summarizer/__init__.py`**

```python
```
(empty file)

- [ ] **Step 5: Create `Part3/tests/__init__.py`**

```python
```
(empty file)

- [ ] **Step 6: Create `Part3/tests/conftest.py`**

```python
```
(empty file — `pythonpath = ["src"]` in `pyproject.toml` handles the import path)

- [ ] **Step 7: Verify the environment works**

```bash
cd Part3 && uv run python -c "import sys; sys.path.insert(0, 'src'); print('Python', sys.version)"
```
Expected: `Python 3.11.x ...`

- [ ] **Step 8: Commit**

```bash
git add Part3/pyproject.toml Part3/uv.lock Part3/src/ Part3/tests/
git commit -m "feat(part3): scaffold project with uv and pyproject.toml"
```

---

## Task 2: `config.py` — StyleConfig + build_llm

**Files:**
- Create: `Part3/src/meeting_summarizer/config.py`
- Create: `Part3/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `Part3/tests/test_config.py`:

```python
import pytest
from meeting_summarizer.config import StyleConfig, build_llm


def test_style_config_defaults():
    config = StyleConfig()
    assert config.body_font == "Calibri"
    assert config.heading_font == "Calibri"
    assert config.title_size == 24
    assert config.heading1_size == 16
    assert config.heading2_size == 13
    assert config.heading3_size == 11
    assert config.body_size == 11
    assert config.title_color == "2E74B5"
    assert config.heading1_color == "2E74B5"
    assert config.heading2_color == "404040"
    assert config.heading3_color == "595959"
    assert config.body_color == "000000"
    assert config.margin_cm == 2.54


def test_style_config_override():
    config = StyleConfig(body_font="Arial", title_size=28)
    assert config.body_font == "Arial"
    assert config.title_size == 28
    assert config.heading_font == "Calibri"  # unchanged default


def test_build_llm_raises_without_google_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        build_llm(source="Google")


def test_build_llm_raises_without_azure_endpoint(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        build_llm(source="Azure")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd Part3 && uv run pytest tests/test_config.py -v
```
Expected: `ImportError` or `ModuleNotFoundError` (config.py doesn't exist yet)

- [ ] **Step 3: Create `Part3/src/meeting_summarizer/config.py`**

```python
import os
from dataclasses import dataclass
from typing import Literal

from loguru import logger
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


@dataclass
class StyleConfig:
    body_font: str = "Calibri"
    heading_font: str = "Calibri"
    title_size: int = 24
    heading1_size: int = 16
    heading2_size: int = 13
    heading3_size: int = 11
    body_size: int = 11
    title_color: str = "2E74B5"
    heading1_color: str = "2E74B5"
    heading2_color: str = "404040"
    heading3_color: str = "595959"
    body_color: str = "000000"
    margin_cm: float = 2.54


def build_llm(
    temperature: float = 0.2,
    source: Literal["Azure", "Google"] = "Google",
) -> AzureChatOpenAI | ChatGoogleGenerativeAI:
    logger.info(f"Building {source} LLM with temperature={temperature}")

    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv(
            "LANGCHAIN_PROJECT", "meeting-summarizer"
        )

    match source:
        case "Azure":
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            if not endpoint or not deployment:
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT are required"
                )
            return AzureChatOpenAI(
                azure_endpoint=endpoint,
                azure_deployment=deployment,
                api_version=api_version,
                temperature=temperature,
                streaming=True,
            )
        case "Google":
            if not os.getenv("GOOGLE_API_KEY"):
                raise ValueError("GOOGLE_API_KEY is required")
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-pro", temperature=temperature
            )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd Part3 && uv run pytest tests/test_config.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Part3/src/meeting_summarizer/config.py Part3/tests/test_config.py
git commit -m "feat(part3): add StyleConfig and build_llm factory"
```

---

## Task 3: Default Template

**Files:**
- Create: `Part3/src/meeting_summarizer/templates/default_template.md`

- [ ] **Step 1: Create the template file**

Create `Part3/src/meeting_summarizer/templates/default_template.md`:

```markdown
# Meeting Summary

## 1. Attendees
List all people present in the meeting.

## 2. Meeting Objective
The stated purpose or agenda of the meeting.

## 3. Key Discussion Points
Main topics discussed, with brief context for each.

## 4. Decisions Made
Decisions that were agreed upon during the meeting. Include rationale if mentioned.

## 5. Action Items
Tasks assigned during the meeting. For each item include: responsible person, description, and deadline if mentioned.

## 6. Next Steps
Follow-up meetings, pending deliverables, or dependencies that arise from this meeting.
```

- [ ] **Step 2: Verify the file is readable**

```bash
cd Part3 && uv run python -c "from pathlib import Path; t = Path('src/meeting_summarizer/templates/default_template.md').read_text(); print(t[:80])"
```
Expected: `# Meeting Summary` printed

- [ ] **Step 3: Commit**

```bash
git add Part3/src/meeting_summarizer/templates/default_template.md
git commit -m "feat(part3): add default meeting summary template"
```

---

## Task 4: `docx_exporter.py`

**Files:**
- Create: `Part3/src/meeting_summarizer/docx_exporter.py`
- Create: `Part3/tests/test_docx_exporter.py`

- [ ] **Step 1: Write the failing tests**

Create `Part3/tests/test_docx_exporter.py`:

```python
from io import BytesIO
import pytest
from docx import Document
from meeting_summarizer.config import StyleConfig
from meeting_summarizer.docx_exporter import export_to_docx


def _load(docx_bytes: bytes) -> Document:
    return Document(BytesIO(docx_bytes))


def _texts(doc: Document) -> list[str]:
    return [p.text for p in doc.paragraphs if p.text.strip()]


def test_returns_bytes():
    result = export_to_docx("# Title\n\n## Section\n\nSome text.")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_headings_and_body_present():
    md = "# Meeting Title\n\n## Attendees\n\nAlice and Bob.\n\n### Sub-section\n\nDetail here."
    doc = _load(export_to_docx(md))
    texts = _texts(doc)
    assert "Meeting Title" in texts
    assert "Attendees" in texts
    assert "Sub-section" in texts
    assert "Alice and Bob." in texts


def test_bullet_items_present():
    md = "## Action Items\n\n- Alice: write report\n- Bob: review code"
    doc = _load(export_to_docx(md))
    texts = _texts(doc)
    assert "Alice: write report" in texts
    assert "Bob: review code" in texts


def test_bold_inline_creates_bold_run():
    md = "Some **bold** text here."
    doc = _load(export_to_docx(md))
    body_para = next(p for p in doc.paragraphs if "bold" in p.text)
    bold_run = next(r for r in body_para.runs if r.text == "bold")
    assert bold_run.bold is True


def test_custom_style_config_applied():
    config = StyleConfig(body_font="Times New Roman", title_size=30)
    md = "# Big Title\n\nNormal text."
    doc = _load(export_to_docx(md, config))
    title_para = next(p for p in doc.paragraphs if p.text == "Big Title")
    assert title_para.runs[0].font.size.pt == 30


def test_empty_markdown_returns_valid_docx():
    result = export_to_docx("")
    assert isinstance(result, bytes)
    doc = _load(result)
    assert doc is not None


def test_default_style_config_used_when_none():
    result = export_to_docx("# Title", style_config=None)
    doc = _load(result)
    title_para = next(p for p in doc.paragraphs if p.text == "Title")
    assert title_para.runs[0].font.size.pt == 24  # StyleConfig default
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd Part3 && uv run pytest tests/test_docx_exporter.py -v
```
Expected: `ImportError` (docx_exporter.py doesn't exist yet)

- [ ] **Step 3: Create `Part3/src/meeting_summarizer/docx_exporter.py`**

```python
import re
from io import BytesIO

from docx import Document
from docx.shared import Pt, RGBColor, Cm

from .config import StyleConfig


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _set_run(run, font_name: str, size: int, color: str, bold: bool = False) -> None:
    run.font.name = font_name
    run.font.size = Pt(size)
    run.font.color.rgb = _hex_to_rgb(color)
    run.bold = bold


def _add_heading(doc: Document, text: str, level: int, cfg: StyleConfig) -> None:
    para = doc.add_paragraph()
    run = para.add_run(text)
    if level == 0:
        _set_run(run, cfg.heading_font, cfg.title_size, cfg.title_color, bold=True)
    elif level == 1:
        _set_run(run, cfg.heading_font, cfg.heading1_size, cfg.heading1_color, bold=True)
    elif level == 2:
        _set_run(run, cfg.heading_font, cfg.heading2_size, cfg.heading2_color, bold=True)
    else:
        _set_run(run, cfg.heading_font, cfg.heading3_size, cfg.heading3_color, bold=True)


def _add_body(doc: Document, text: str, cfg: StyleConfig, bullet: bool = False) -> None:
    para = doc.add_paragraph(style="List Bullet" if bullet else "Normal")
    for part in re.split(r"(\*\*[^*]+\*\*)", text):
        if part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            _set_run(run, cfg.body_font, cfg.body_size, cfg.body_color, bold=True)
        else:
            run = para.add_run(part)
            _set_run(run, cfg.body_font, cfg.body_size, cfg.body_color)


def export_to_docx(markdown_text: str, style_config: StyleConfig = None) -> bytes:
    cfg = style_config or StyleConfig()
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(cfg.margin_cm)
        section.bottom_margin = Cm(cfg.margin_cm)
        section.left_margin = Cm(cfg.margin_cm)
        section.right_margin = Cm(cfg.margin_cm)

    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#### "):
            _add_heading(doc, stripped[5:], level=3, cfg=cfg)
        elif stripped.startswith("### "):
            _add_heading(doc, stripped[4:], level=2, cfg=cfg)
        elif stripped.startswith("## "):
            _add_heading(doc, stripped[3:], level=1, cfg=cfg)
        elif stripped.startswith("# "):
            _add_heading(doc, stripped[2:], level=0, cfg=cfg)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            _add_body(doc, stripped[2:], cfg, bullet=True)
        else:
            _add_body(doc, stripped, cfg)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd Part3 && uv run pytest tests/test_docx_exporter.py -v
```
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Part3/src/meeting_summarizer/docx_exporter.py Part3/tests/test_docx_exporter.py
git commit -m "feat(part3): add docx_exporter with markdown-to-Word conversion"
```

---

## Task 5: `summarizer.py`

**Files:**
- Create: `Part3/src/meeting_summarizer/summarizer.py`
- Create: `Part3/tests/test_summarizer.py`

- [ ] **Step 1: Write the failing tests**

Create `Part3/tests/test_summarizer.py`:

```python
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from meeting_summarizer.summarizer import MeetingSummarizer

FAKE_SUMMARY = "# Summary\n\n## Attendees\nAlice, Bob\n\n## Decisions\nUse Python"
FAKE_ANSWER = "Alice and Bob were the main speakers."
TRANSCRIPT = "Alice: Let's use Python. Bob: Agreed."
TEMPLATE = "# Summary\n\n## Attendees\nList attendees.\n\n## Decisions\nList decisions."


def make_summarizer(responses: list[str]) -> MeetingSummarizer:
    fake_llm = FakeListChatModel(responses=responses)
    return MeetingSummarizer(llm=fake_llm)


def test_generate_summary_returns_string():
    s = make_summarizer([FAKE_SUMMARY])
    result = s.generate_summary(TRANSCRIPT, TEMPLATE)
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_summary_returns_llm_content():
    s = make_summarizer([FAKE_SUMMARY])
    result = s.generate_summary(TRANSCRIPT, TEMPLATE)
    assert result == FAKE_SUMMARY


def test_ask_question_returns_string():
    s = make_summarizer([FAKE_ANSWER])
    result = s.ask_question("Who was in the meeting?", TRANSCRIPT)
    assert isinstance(result, str)
    assert len(result) > 0


def test_ask_question_with_history():
    history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    s = make_summarizer([FAKE_ANSWER])
    result = s.ask_question("Who was in the meeting?", TRANSCRIPT, history=history)
    assert isinstance(result, str)


def test_refine_summary_returns_string():
    refined = "# Summary\n\n## Attendees\nAlice, Bob, Charlie\n\n## Decisions\nUse Python"
    s = make_summarizer([refined])
    result = s.refine_summary("Add Charlie to attendees", FAKE_SUMMARY, TRANSCRIPT)
    assert isinstance(result, str)
    assert len(result) > 0


def test_refine_summary_with_history():
    history = [{"role": "user", "content": "Earlier change"}, {"role": "assistant", "content": "Done."}]
    s = make_summarizer(["Updated summary"])
    result = s.refine_summary("Change title", FAKE_SUMMARY, TRANSCRIPT, history=history)
    assert isinstance(result, str)


def test_constructor_accepts_llm_injection():
    fake_llm = FakeListChatModel(responses=["test"])
    s = MeetingSummarizer(llm=fake_llm)
    assert s.llm is fake_llm
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd Part3 && uv run pytest tests/test_summarizer.py -v
```
Expected: `ImportError` (summarizer.py doesn't exist yet)

- [ ] **Step 3: Create `Part3/src/meeting_summarizer/summarizer.py`**

```python
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from loguru import logger

from .config import build_llm


class MeetingSummarizer:
    def __init__(self, source: str = "Google", llm: Any = None):
        self.llm = llm if llm is not None else build_llm(source=source)

    def _to_messages(self, history: list[dict]) -> list:
        result = []
        for msg in history:
            if msg["role"] == "user":
                result.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                result.append(AIMessage(content=msg["content"]))
        return result

    def generate_summary(self, transcription: str, template: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert meeting secretary. "
             "Given a meeting transcription, produce a structured summary in markdown "
             "following the provided template exactly. "
             "Preserve the section headers from the template. "
             "Fill each section with relevant content from the transcription. "
             "Output only valid markdown. Be concise and factual."),
            ("user", "Template:\n{template}\n\nTranscription:\n{transcription}"),
        ])
        chain = prompt | self.llm | StrOutputParser()
        logger.info("Generating meeting summary")
        return chain.invoke({"template": template, "transcription": transcription})

    def ask_question(
        self,
        question: str,
        transcription: str,
        history: list[dict] | None = None,
    ) -> str:
        history = history or []
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a helpful assistant with access to a meeting transcription. "
             "Answer questions accurately and concisely based only on the transcription. "
             "If the answer is not in the transcription, say so clearly."),
            ("user", "Meeting transcription:\n{transcription}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{question}"),
        ])
        chain = prompt | self.llm | StrOutputParser()
        logger.info(f"Answering question: {question[:80]}")
        return chain.invoke({
            "transcription": transcription,
            "question": question,
            "chat_history": self._to_messages(history),
        })

    def refine_summary(
        self,
        instruction: str,
        current_summary: str,
        transcription: str,
        history: list[dict] | None = None,
    ) -> str:
        history = history or []
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert meeting secretary. "
             "You have a draft meeting summary and the original transcription. "
             "Apply the user's modification instruction to the summary. "
             "Return the complete updated summary in markdown, preserving all sections."),
            ("user", "Original transcription:\n{transcription}\n\nCurrent summary:\n{current_summary}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "Modification requested: {instruction}"),
        ])
        chain = prompt | self.llm | StrOutputParser()
        logger.info(f"Refining summary: {instruction[:80]}")
        return chain.invoke({
            "transcription": transcription,
            "current_summary": current_summary,
            "instruction": instruction,
            "chat_history": self._to_messages(history),
        })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd Part3 && uv run pytest tests/test_summarizer.py -v
```
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add Part3/src/meeting_summarizer/summarizer.py Part3/tests/test_summarizer.py
git commit -m "feat(part3): add MeetingSummarizer with generate, ask, and refine chains"
```

---

## Task 6: `frontend.py` — Streamlit App

**Files:**
- Create: `Part3/src/frontend.py`

There are no unit tests for Streamlit frontends — manual testing is done in Task 7.

- [ ] **Step 1: Create `Part3/src/frontend.py`**

```python
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from loguru import logger

_src = Path(__file__).resolve().parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

try:
    from meeting_summarizer.config import StyleConfig
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
        docx_bytes = export_to_docx(st.session_state.summary, StyleConfig())
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
```

- [ ] **Step 2: Verify syntax is valid**

```bash
cd Part3 && uv run python -m py_compile src/frontend.py && echo "OK"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add Part3/src/frontend.py
git commit -m "feat(part3): add Streamlit frontend"
```

---

## Task 7: Entry Point + Smoke Test

**Files:**
- Create: `Part3/run_frontend.py`

- [ ] **Step 1: Create `Part3/run_frontend.py`**

```python
import subprocess
from pathlib import Path

if __name__ == "__main__":
    frontend = Path(__file__).parent / "src" / "frontend.py"
    subprocess.run(
        ["uv", "run", "streamlit", "run", str(frontend)],
        check=True,
        cwd=Path(__file__).parent,
    )
```

- [ ] **Step 2: Copy .env from Part1**

```bash
cp Part1/.env Part3/.env
```

- [ ] **Step 3: Run the full test suite**

```bash
cd Part3 && uv run pytest tests/ -v
```
Expected: All 14 tests PASS

- [ ] **Step 4: Verify the app starts without import errors**

```bash
cd Part3 && uv run streamlit run src/frontend.py --server.headless true &
sleep 4 && curl -s http://localhost:8501 | grep -q "Meeting Summarizer" && echo "App OK" || echo "App NOT OK"
kill %1
```
Expected: `App OK`

- [ ] **Step 5: Final commit**

```bash
git add Part3/run_frontend.py Part3/.env
git commit -m "feat(part3): add entry point and complete meeting summarizer module"
```

---

## Running the App

```bash
# From the Part3 directory:
uv run streamlit run src/frontend.py

# Or via the launcher (from repo root):
cd Part3 && uv run python run_frontend.py
```

## Adding / Updating Dependencies

```bash
# Add a new runtime dependency:
cd Part3 && uv add <package>

# Add a dev-only dependency:
cd Part3 && uv add --dev <package>

# Sync after pulling changes (installs from uv.lock):
cd Part3 && uv sync
```
