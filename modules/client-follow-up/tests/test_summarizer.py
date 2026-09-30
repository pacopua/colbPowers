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
