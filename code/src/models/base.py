"""
Base model adapter interface.
All model backends (Gemini, Ollama, Mock) implement this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class ModelAdapter(ABC):
    """Abstract base for model adapters."""

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

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter is ready to use."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""
        ...
