"""Configuration for LLM and environment variables."""

import os
from pathlib import Path
from typing import Literal

from loguru import logger

from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# ------ Logging configuration ------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def build_llm(temperature: float = 0.2, source: Literal["Azure", "Google"] = "Google", model_name: str | None = "gemini-2.5-pro") -> AzureChatOpenAI | ChatGoogleGenerativeAI:
    """Build Azure OpenAI LLM with configuration from environment."""
    logger.info(f"Building {source} {model_name} LLM with temperature={temperature}")
    
    # Configure LangSmith tracing
    if os.getenv("LANGCHAIN_API_KEY"):
        logger.debug("LangSmith tracing enabled")
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "hcp-personas-ui")
        logger.debug(f"LangSmith project: {os.environ['LANGCHAIN_PROJECT']}")
    else:
        logger.debug("LangSmith tracing not configured (no API key)")

    match source:
        case "Azure":
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = model_name or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            
            if not endpoint or not deployment:
                logger.error("AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_DEPLOYMENT environment variable is not set")
                raise ValueError("Both AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT environment variables are required for Azure LLM")

            logger.info(f"Azure OpenAI configuration: endpoint={endpoint}, deployment={deployment}, api_version={api_version}")

            return AzureChatOpenAI(
                azure_endpoint=endpoint,
                azure_deployment=deployment,
                api_version=api_version,
                temperature=temperature,
                streaming=True,  # Enable streaming for better UX
            )

        case "Google":
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                logger.error("GOOGLE_API_KEY environment variable is not set")
                raise ValueError("GOOGLE_API_KEY environment variable is required for Google LLM")
            logger.info("Google Generative AI configuration loaded")
            return ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=temperature)