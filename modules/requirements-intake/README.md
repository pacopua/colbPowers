# Module: Requirements Intake

Turns a client meeting into a researched architecture plan and a set of GitHub issues, with a human reviewing every step. This is the requirements-gathering module of my bachelor's thesis (section 5.1 of [the thesis](../../docs/thesis/memoria_TFG_Adria.pdf)). Its output, the plan, is the starting point for development with colbPowers.

## Pipeline

1. **Transcription** (`src/speech_transcriptor/`): compresses the audio with ffmpeg (mono, 16 kHz), uploads it to Azure Blob Storage, and runs an **Azure Speech batch transcription** job with speaker diarization. The output is a `[Speaker N]: text` transcript. Job status is tracked in a local `jobs.csv`, which is created on first run.
2. **Filtering** (`src/transcription_preprocessing/`): splits the transcript into 25,000-character chunks with 1,200 characters of overlap. A cheap model (Azure OpenAI) keeps only the functional requirements and business rules from each chunk and drops chunks with nothing relevant.
3. **Research plan**: a stronger model (Gemini 2.5 Pro) finds the open technical decisions and proposes up to 3 web-search queries. *You review and edit the queries.*
4. **Research**: runs the approved queries with **Tavily** (advanced depth, results from the last year).
5. **Architecture plan**: Gemini combines the transcript and the research into a Markdown implementation plan. *You refine it in natural language or edit it directly.*
6. **Issues**: the approved plan is converted into structured issues. *You refine them*, then push them to a GitHub repository (`src/issue_manager/`, PyGithub).

Every review step keeps a conversation history (LangChain `MessagesPlaceholder`), so each refinement builds on the previous ones.

## Run it

```bash
cp .env.example .env    # fill in the Azure, Gemini, Tavily and GitHub keys
uv sync
uv run streamlit run src/frontend.py
```

The app has three modes: **Audio → Plan** (full pipeline), **Text Context → Issues** (start from a transcript or notes) and **JSON Issues → GitHub** (sync only).

To transcribe a single file from the command line:

```bash
uv run python run_transcription.py path/to/meeting.m4a
```

## Notes

- The Azure Speech and Blob Storage parts need your own Azure resources.
- Example transcripts and outputs from real client meetings were removed before publishing.
