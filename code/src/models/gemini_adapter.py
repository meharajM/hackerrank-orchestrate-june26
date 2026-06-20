"""
Gemini adapter through Google's OpenAI-compatible endpoint.
Extends OpenAICompatibleAdapter with Gemini-specific defaults.
"""
from __future__ import annotations

import os
import logging

from .openai_compatible_adapter import OpenAICompatibleAdapter

logger = logging.getLogger(__name__)

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


class GeminiAdapter(OpenAICompatibleAdapter):
    """Adapter for Google Gemini via the OpenAI-compatible REST endpoint."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash-lite",
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        text_timeout: float | None = None,
        multimodal_timeout: float | None = None,
        max_tokens: int | None = None,
    ):
        resolved_api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        resolved_base_url = base_url or os.environ.get("GEMINI_BASE_URL", _GEMINI_BASE_URL)
        resolved_model = model_name or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        resolved_max_tokens = max_tokens if max_tokens is not None else int(os.environ.get("GEMINI_MAX_TOKENS", "4096"))

        # Store raw URL before normalization (Gemini endpoint doesn't want /v1 appended)
        self._raw_base_url = resolved_base_url
        self._resolved_api_key = resolved_api_key

        super().__init__(
            model_name=resolved_model,
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            label="Gemini",
            max_retries=max_retries,
            retry_delay=retry_delay,
            text_timeout=text_timeout,
            multimodal_timeout=multimodal_timeout,
            response_format_json=True,
            max_tokens=resolved_max_tokens,
        )

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("openai package not installed. Run: pip install openai") from exc
            api_key = self._resolved_api_key or "gemini"
            self._client = OpenAI(api_key=api_key, base_url=self._raw_base_url, timeout=self._text_timeout)
        return self._client

    def is_available(self) -> bool:
        """Check if Gemini API key is configured (avoids models.list() call which may not work on Gemini's endpoint)."""
        return bool(self._api_key and self._api_key.strip())

    @property
    def name(self) -> str:
        return f"Gemini ({self._model_name})"
