import pytest
from meeting_summarizer.config import StyleConfig, build_llm


def test_style_config_defaults():
    config = StyleConfig()
    assert config.body_font == "Arial"
    assert config.heading_font == "Arial"
    assert config.title_size == 24
    assert config.heading1_size == 14
    assert config.heading2_size == 13
    assert config.heading3_size == 11
    assert config.body_size == 11
    assert config.title_color == "4472C4"
    assert config.heading1_color == "4472C4"
    assert config.heading2_color == "404040"
    assert config.heading3_color == "595959"
    assert config.body_color == "000000"
    assert config.margin_cm == 2.54


def test_style_config_override():
    config = StyleConfig(body_font="Arial", title_size=28)
    assert config.body_font == "Arial"
    assert config.title_size == 28
    assert config.heading_font == "Arial"  # unchanged default


def test_build_llm_raises_without_google_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        build_llm(source="Google")


def test_build_llm_raises_without_azure_endpoint(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        build_llm(source="Azure")
