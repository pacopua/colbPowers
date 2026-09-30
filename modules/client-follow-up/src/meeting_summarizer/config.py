import os
from dataclasses import dataclass, field
from typing import Literal

from loguru import logger
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


@dataclass
class StyleConfig:
    body_font: str = "Arial"
    heading_font: str = "Arial"
    title_size: int = 24
    heading1_size: int = 14
    heading2_size: int = 13
    heading3_size: int = 11
    body_size: int = 11
    title_color: str = "4472C4"
    heading1_color: str = "4472C4"
    heading2_color: str = "404040"
    heading3_color: str = "595959"
    body_color: str = "000000"
    margin_cm: float = 2.54


@dataclass
class MeetingMetadata:
    client_name: str = ""
    next_meeting_date: str = "Por confirmar"   # DD/MM/YYYY or "Por confirmar"
    next_meeting_time: str = "10:00h"
    participants: list[str] = field(default_factory=list)
    created_date: str = ""   # DD/MM/YYYY; defaults to today when empty


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
