import os

from src.config import Config


def test_config_reads_model_overrides_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "llava:latest")
    monkeypatch.setenv("OLLAMA_STAGE2_MODEL", "qwen3-vl:4b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OPENAI_COMPAT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_COMPAT_STAGE2_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_THINKING_MODEL", "gemini-2.5-pro")

    config = Config()

    assert config.ollama_model == "llava:latest"
    assert config.ollama_stage2_model == "qwen3-vl:4b"
    assert config.ollama_base_url == "http://127.0.0.1:11434"
    assert config.openai_compatible_model == "gpt-4o-mini"
    assert config.openai_compatible_stage2_model == "gpt-4.1-mini"
    assert config.openai_compatible_base_url == "https://example.test/v1"
    assert config.openai_compatible_api_key == "test-key"
    assert config.gemini_model == "gemini-2.5-flash"
    assert config.gemini_thinking_model == "gemini-2.5-pro"
