"""
Ollama adapter implemented through Ollama's OpenAI-compatible API surface.
"""
from __future__ import annotations

import os

from .openai_compatible_adapter import OpenAICompatibleAdapter


class OllamaAdapter(OpenAICompatibleAdapter):
    """Adapter for Ollama using the OpenAI-compatible `/v1/chat/completions` API."""

    def __init__(
        self,
        model_name: str = "qwen3-vl:4b",
        base_url: str = "http://localhost:11434",
        max_retries: int = 3,
        retry_delay: float = 2.0,
        text_timeout: float | None = None,
        multimodal_timeout: float | None = None,
    ):
        super().__init__(
            model_name=model_name,
            base_url=base_url,
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            label="Ollama",
            max_retries=max_retries,
            retry_delay=retry_delay,
            text_timeout=text_timeout,
            multimodal_timeout=multimodal_timeout,
            response_format_json=True,
            reasoning_effort=os.environ.get("OLLAMA_REASONING_EFFORT", "none"),
        )
