"""
Prompt provider abstractions and file-backed defaults.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class PromptRequest:
    """Declarative prompt assembly request."""

    name: str
    fallback: str
    shared_sections: tuple[str, ...] = ()


@runtime_checkable
class PromptProvider(Protocol):
    """Abstract source of prompt templates and system prompts."""

    def get_prompt(self, name: str, fallback: str) -> str:
        """Return prompt content for a named prompt, or the fallback if unavailable."""
        ...


class FilePromptProvider:
    """Prompt provider that composes prompt files with shared security fragments."""

    def __init__(self, prompt_dir: Path):
        self._prompt_dir = Path(prompt_dir)
        self._shared_dir = self._prompt_dir / "_shared"
        self._always_on_sections = ("core_security",)

    def get_prompt(self, name: str, fallback: str) -> str:
        return self.build_prompt(PromptRequest(name=name, fallback=fallback))

    def build_prompt(self, request: PromptRequest) -> str:
        parts: list[str] = []

        for section in self._always_on_sections + tuple(request.shared_sections):
            section_text = self._load_shared_section(section)
            if section_text:
                parts.append(section_text)

        prompt_path = self._prompt_dir / f"{request.name}.md"
        if prompt_path.exists():
            parts.append(prompt_path.read_text(encoding="utf-8").strip())
        else:
            parts.append(request.fallback.strip())

        return "\n\n".join(part for part in parts if part).strip()

    def _load_shared_section(self, section: str) -> str:
        section_path = self._shared_dir / f"{section}.md"
        if not section_path.exists():
            return ""
        return section_path.read_text(encoding="utf-8").strip()


def resolve_prompt(
    prompt_provider: PromptProvider,
    *,
    name: str,
    fallback: str,
    shared_sections: tuple[str, ...] = (),
) -> str:
    """Render a prompt, using composable sections when supported by the provider."""
    build_prompt = getattr(prompt_provider, "build_prompt", None)
    if callable(build_prompt):
        return build_prompt(
            PromptRequest(
                name=name,
                fallback=fallback,
                shared_sections=shared_sections,
            )
        )
    return prompt_provider.get_prompt(name, fallback)


__all__ = [
    "PromptProvider",
    "FilePromptProvider",
    "PromptRequest",
    "resolve_prompt",
]
