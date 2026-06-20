"""
Adapter for OpenAI-compatible chat-completions APIs.
Supports both hosted providers and local servers such as Ollama.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from .base import ModelAdapter

logger = logging.getLogger(__name__)


class OpenAICompatibleAdapter(ModelAdapter):
    """Adapter for servers that implement the OpenAI chat-completions API."""

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        label: str = "OpenAI Compatible",
        max_retries: int = 3,
        retry_delay: float = 2.0,
        text_timeout: float | None = None,
        multimodal_timeout: float | None = None,
        response_format_json: bool = True,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ):
        self._model_name = model_name
        self._base_url = _normalize_base_url(base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
        self._api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self._label = label
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._text_timeout = text_timeout or float(os.environ.get("OPENAI_COMPAT_TEXT_TIMEOUT", os.environ.get("OLLAMA_TEXT_TIMEOUT", "120")))
        self._multimodal_timeout = multimodal_timeout or float(os.environ.get("OPENAI_COMPAT_MULTIMODAL_TIMEOUT", os.environ.get("OLLAMA_MULTIMODAL_TIMEOUT", "300")))
        self._response_format_json = response_format_json
        self._reasoning_effort = reasoning_effort
        self._max_tokens = (
            max_tokens
            if max_tokens is not None
            else int(os.environ.get("OPENAI_COMPAT_MAX_TOKENS", "4096"))
        )
        self._client = None
        self._call_count = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("openai package not installed. Run: pip install openai") from exc

            # Local Ollama accepts an ignored placeholder key.
            api_key = self._api_key or "ollama"
            self._client = OpenAI(api_key=api_key, base_url=self._base_url, timeout=self._text_timeout)
        return self._client

    def text_call(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._create_completion(messages, timeout=self._text_timeout)

    def multimodal_call(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str = "",
    ) -> str:
        content = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            if not img_path.exists():
                continue
            try:
                mime_type = _guess_mime_type(img_path)
                b64_image = base64.b64encode(img_path.read_bytes()).decode("utf-8")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}",
                            "detail": "high",
                        },
                    }
                )
            except Exception as exc:
                logger.warning("Failed to load image %s: %s", img_path, exc)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})
        return self._create_completion(messages, timeout=self._multimodal_timeout)

    def _create_completion(self, messages: list[dict], *, timeout: float) -> str:
        client = self._get_client()
        last_error: Exception | None = None

        request_kwargs = {
            "model": self._model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": self._max_tokens,
            "timeout": timeout,
        }
        if self._response_format_json:
            request_kwargs["response_format"] = {"type": "json_object"}
        if self._reasoning_effort:
            request_kwargs["extra_body"] = {"reasoning_effort": self._reasoning_effort}

        for attempt in range(self._max_retries):
            try:
                response = client.chat.completions.create(**request_kwargs)
                self._call_count += 1
                usage = getattr(response, "usage", None)
                if usage is not None:
                    self._total_input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                    self._total_output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                logger.warning(
                    "OpenAI-compatible call failed (attempt %s/%s) against %s: %s",
                    attempt + 1,
                    self._max_retries,
                    self._base_url,
                    exc,
                )
                if attempt < self._max_retries - 1:
                    retry_delay = self._retry_delay
                    if "429" in err_str:
                        retry_delay = _extract_gemini_retry_delay(err_str) or retry_delay
                        retry_delay = max(retry_delay, 5.0)
                    elif attempt > 0:
                        retry_delay *= 2 ** attempt
                    logger.warning("  waiting %.1fs before retry...", retry_delay)
                    time.sleep(retry_delay)

        raise RuntimeError(
            f"OpenAI-compatible API call failed after {self._max_retries} retries. "
            f"Endpoint={self._base_url}, model={self._model_name}. Last error: {last_error}"
        )

    def is_available(self) -> bool:
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception:
            return False

    def set_max_tokens(self, value: int) -> None:
        self._max_tokens = value

    @property
    def name(self) -> str:
        return f"{self._label} ({self._model_name})"

    def get_stats(self) -> dict:
        return {
            "call_count": self._call_count,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        }


def _extract_gemini_retry_delay(err_str: str) -> float | None:
    """Extract the retry delay from Gemini's 429 error RetryInfo if present."""
    match = re.search(r'retryDelay["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)s', err_str)
    if match:
        return float(match.group(1))
    return None


def _normalize_base_url(base_url: str) -> str:
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/v1"):
        return trimmed
    return f"{trimmed}/v1"


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return "image/jpeg"
