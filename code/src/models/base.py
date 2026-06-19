"""
Base model adapter interface.
All model backends (Gemini, Ollama, Mock) implement this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..telemetry.caching import CacheBackend


class ModelAdapter(ABC):
    """Abstract base for model adapters."""

    _cache: Optional["CacheBackend"] = None

    def wire_cache(self, cache: "CacheBackend") -> None:
        """Attach a cache backend so cached_text_call / cached_multimodal_call work."""
        self._cache = cache

    # ── Public cached entry-points ───────────────────────────────────────
    def cached_text_call(self, prompt: str, system_prompt: str = "") -> tuple[str, bool]:
        """Like text_call but checks cache first. Returns (response, was_cached)."""
        if self._cache is not None:
            key = self._cache.make_key(self.name, prompt, system_prompt)
            cached = self._cache.get(key)
            if cached is not None:
                return cached, True

        response = self.text_call(prompt, system_prompt)

        if self._cache is not None:
            self._cache.put(key, response)

        return response, False

    def cached_multimodal_call(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str = "",
    ) -> tuple[str, bool]:
        """Like multimodal_call but checks cache first. Returns (response, was_cached)."""
        if self._cache is not None:
            key = self._cache.make_key(self.name, prompt, system_prompt, image_paths)
            cached = self._cache.get(key)
            if cached is not None:
                return cached, True

        response = self.multimodal_call(prompt, image_paths, system_prompt)

        if self._cache is not None:
            self._cache.put(key, response)

        return response, False

    # ── Abstract methods (subclasses implement these) ────────────────────
    @abstractmethod
    def text_call(self, prompt: str, system_prompt: str = "") -> str:
        """Make a text-only call to the model and return the response text."""
        ...

    @abstractmethod
    def multimodal_call(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str = "",
    ) -> str:
        """Make a multimodal call with text + images and return response text."""
        ...

    def get_stats(self) -> dict:
        """Return usage statistics. Subclasses can override."""
        return {
            "call_count": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter is ready to use."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""
        ...
