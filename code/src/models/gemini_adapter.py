"""
Gemini model adapter using the google-genai SDK.
Handles both text-only and multimodal (image) calls.
"""
from __future__ import annotations

import json
import os
import time
import logging
from pathlib import Path
from typing import Optional

from .base import ModelAdapter

logger = logging.getLogger(__name__)


class GeminiAdapter(ModelAdapter):
    """Adapter for Google Gemini via the google-genai SDK."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self._model_name = model_name
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._client = None
        self._call_count = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    def _get_client(self):
        """Lazy-init the Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "google-genai package not installed. Run: pip install google-genai"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Gemini client: {e}")
        return self._client

    def text_call(self, prompt: str, system_prompt: str = "") -> str:
        """Make a text-only call to Gemini."""
        client = self._get_client()
        from google.genai import types

        contents = []
        if system_prompt:
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=system_prompt + "\n\n" + prompt)]
            ))
        else:
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            ))

        for attempt in range(self._max_retries):
            try:
                response = client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=4096,
                    ),
                )
                self._call_count += 1
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    self._total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                    self._total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
                return response.text or ""
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "resource" in err_str or "quota" in err_str or "rate" in err_str:
                    wait = self._retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited (attempt {attempt+1}/{self._max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if attempt == self._max_retries - 1:
                    logger.error(f"Gemini text call failed after {self._max_retries} attempts: {e}")
                    raise
                time.sleep(self._retry_delay)

        raise RuntimeError("Gemini text call failed after all retries")

    def multimodal_call(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str = "",
    ) -> str:
        """Make a multimodal call with text + images."""
        client = self._get_client()
        from google.genai import types

        parts = []

        # Add system prompt as prefix if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = system_prompt + "\n\n" + prompt

        # Add images first
        for img_path in image_paths:
            if img_path.exists():
                try:
                    img_bytes = img_path.read_bytes()
                    # Determine mime type
                    suffix = img_path.suffix.lower()
                    mime_map = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".gif": "image/gif",
                        ".webp": "image/webp",
                    }
                    mime_type = mime_map.get(suffix, "image/jpeg")
                    parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
                except Exception as e:
                    logger.warning(f"Failed to load image {img_path}: {e}")
                    parts.append(types.Part.from_text(text=f"[Image {img_path.stem} could not be loaded: {e}]"))
            else:
                parts.append(types.Part.from_text(text=f"[Image {img_path.stem} not found]"))

        # Add prompt text after images
        parts.append(types.Part.from_text(text=full_prompt))

        contents = [types.Content(role="user", parts=parts)]

        for attempt in range(self._max_retries):
            try:
                response = client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=4096,
                    ),
                )
                self._call_count += 1
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    self._total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                    self._total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
                return response.text or ""
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "resource" in err_str or "quota" in err_str or "rate" in err_str:
                    wait = self._retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited (attempt {attempt+1}/{self._max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if attempt == self._max_retries - 1:
                    logger.error(f"Gemini multimodal call failed after {self._max_retries} attempts: {e}")
                    raise
                time.sleep(self._retry_delay)

        raise RuntimeError("Gemini multimodal call failed after all retries")

    def is_available(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self._api_key and self._api_key.strip())

    @property
    def name(self) -> str:
        return f"Gemini ({self._model_name})"

    def get_stats(self) -> dict:
        """Return usage statistics."""
        return {
            "call_count": self._call_count,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        }
