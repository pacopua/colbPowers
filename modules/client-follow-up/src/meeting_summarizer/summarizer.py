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
