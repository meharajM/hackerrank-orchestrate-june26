"""
Ollama model adapter for offline/local development.
Calls local Ollama service with support for text and multimodal payloads.
"""
from __future__ import annotations

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from .base import ModelAdapter

logger = logging.getLogger(__name__)


class OllamaAdapter(ModelAdapter):
    """Adapter for Ollama running local models (e.g. gemma4:e4b)."""

    def __init__(
        self,
        model_name: str = "gemma4:e4b",
        base_url: str = "http://localhost:11434",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._call_count = 0

    def text_call(self, prompt: str, system_prompt: str = "") -> str:
        """Make a text-only call to Ollama."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
        }

        return self._send_request(payload)

    def multimodal_call(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str = "",
    ) -> str:
        """Make a multimodal call to Ollama."""
        # Convert images to base64 strings
        b64_images = []
        for path in image_paths:
            if path.exists():
                try:
                    img_bytes = path.read_bytes()
                    b64_str = base64.b64encode(img_bytes).decode("utf-8")
                    b64_images.append(b64_str)
                except Exception as e:
                    logger.warning(f"Ollama adapter failed to read image {path}: {e}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_message = {"role": "user", "content": prompt}
        if b64_images:
            user_message["images"] = b64_images

        messages.append(user_message)

        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
        }

        return self._send_request(payload)

    def _send_request(self, payload: dict[str, Any]) -> str:
        url = f"{self._base_url}/api/chat"

        for attempt in range(self._max_retries):
            try:
                response = httpx.post(url, json=payload, timeout=120.0)
                if response.status_code == 200:
                    self._call_count += 1
                    data = response.json()
                    # Extract content from the assistant's message response
                    message = data.get("message", {})
                    content = message.get("content", "")
                    return content
                else:
                    logger.warning(
                        f"Ollama server returned status {response.status_code} "
                        f"(attempt {attempt+1}/{self._max_retries})"
                    )
            except Exception as e:
                logger.warning(
                    f"Ollama connection error (attempt {attempt+1}/{self._max_retries}): {e}"
                )

            if attempt < self._max_retries - 1:
                time.sleep(self._retry_delay)

        raise RuntimeError(
            f"Ollama API call failed after {self._max_retries} retries. "
            f"Please ensure Ollama is serving at {self._base_url} and model {self._model_name} is pulled."
        )

    def is_available(self) -> bool:
        """Check if local Ollama server is running and the model is pulled."""
        try:
            # First check if the service is up
            response = httpx.get(f"{self._base_url}/api/tags", timeout=2.0)
            if response.status_code != 200:
                return False
            # Check if model is pulled
            models = response.json().get("models", [])
            for m in models:
                if m.get("name") == self._model_name or m.get("model") == self._model_name:
                    return True
            # Try to match without version tags if tag is missing
            model_base = self._model_name.split(":")[0]
            for m in models:
                name = m.get("name", "")
                if name.startswith(model_base):
                    return True
            return False
        except Exception:
            return False

    @property
    def name(self) -> str:
        return f"Ollama ({self._model_name})"

    def get_stats(self) -> dict:
        return {"call_count": self._call_count}
