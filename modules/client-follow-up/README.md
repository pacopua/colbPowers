# Module: Client Follow-up (Meeting Summarizer)

A Streamlit app that turns a client follow-up meeting transcript into a structured Word document. This is the client follow-up module of my bachelor's thesis (section 5.2.2 of [the thesis](../../docs/thesis/memoria_TFG_Adria.pdf)).

The spec and plan that drove the implementation are included, in the `.specs/memory/` layout colbPowers uses:

| Artifact | Phase |
|---|---|
| [`.specs/memory/docs/specs/2026-05-29-meeting-summarizer-design.md`](.specs/memory/docs/specs/2026-05-29-meeting-summarizer-design.md) | Design (`brainstorming`) |
| [`.specs/memory/docs/plans/2026-05-29-meeting-summarizer.md`](.specs/memory/docs/plans/2026-05-29-meeting-summarizer.md) | Implementation plan (`writing-plans`) |
| `src/`, `tests/` | Implementation, test-first, following the plan task by task |

## How it works

1. **Load** a meeting transcript (`.txt`/`.md`) or paste it.
2. **Generate** a first summary with an LLM (Gemini or Azure OpenAI through LangChain), following a Markdown template: agenda, task status for each side, notes, next steps.
3. **Review**, human in the loop: edit the Markdown directly, ask questions about the meeting (`ask_question`), or give instructions in natural language (`refine_summary`).
4. **Export** to `.docx` with `python-docx`, with styled headings, colored task tables, header and footer.

The document template and styling are in Spanish, since the tool was built for Colb.ai's client meetings.

## Run it

```bash
cp .env.example .env    # add GOOGLE_API_KEY (or the Azure variables)
uv sync
uv run python run_frontend.py
```

## Tests

```bash
uv run pytest
```
