"""
Configuration module for the claims verification system.
Centralizes all paths, environment variables, and runtime settings.
"""
import os
from pathlib import Path
from dataclasses import dataclass, field


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains dataset/)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "dataset").is_dir():
            return current
        current = current.parent
    # Fallback: assume two levels up from code/src/
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class Config:
    """Runtime configuration."""

    # Paths
    repo_root: Path = field(default_factory=_find_repo_root)

    @property
    def dataset_dir(self) -> Path:
        return self.repo_root / "dataset"

    @property
    def claims_csv(self) -> Path:
        return self.dataset_dir / "claims.csv"

    @property
    def sample_claims_csv(self) -> Path:
        return self.dataset_dir / "sample_claims.csv"

    @property
    def user_history_csv(self) -> Path:
        return self.dataset_dir / "user_history.csv"

    @property
    def evidence_requirements_csv(self) -> Path:
        return self.dataset_dir / "evidence_requirements.csv"

    @property
    def output_csv(self) -> Path:
        return self.repo_root / "output.csv"

    @property
    def images_dir(self) -> Path:
        return self.dataset_dir / "images"

    @property
    def prompts_dir(self) -> Path:
        return self.repo_root / "code" / "src" / "prompts"

    # Provider settings
    @property
    def gemini_api_key(self) -> str | None:
        return os.environ.get("GEMINI_API_KEY")

    @property
    def has_gemini(self) -> bool:
        key = self.gemini_api_key
        return key is not None and len(key.strip()) > 0

    # Model settings
    gemini_model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
    gemini_thinking_model: str = field(default_factory=lambda: os.environ.get("GEMINI_THINKING_MODEL", "gemini-2.5-flash"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "qwen3-vl:4b"))
    ollama_stage2_model: str = field(default_factory=lambda: os.environ.get("OLLAMA_STAGE2_MODEL", "qwen3-vl:4b"))
    ollama_base_url: str = field(default_factory=lambda: os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_api_key: str = field(default_factory=lambda: os.environ.get("OLLAMA_API_KEY", "ollama"))
    openai_compatible_model: str = field(default_factory=lambda: os.environ.get("OPENAI_COMPAT_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o-mini")))
    openai_compatible_stage2_model: str = field(default_factory=lambda: os.environ.get("OPENAI_COMPAT_STAGE2_MODEL", os.environ.get("OPENAI_COMPAT_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))))
    openai_compatible_base_url: str = field(default_factory=lambda: os.environ.get("OPENAI_COMPAT_BASE_URL", os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")))
    openai_compatible_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_COMPAT_API_KEY", os.environ.get("OPENAI_API_KEY", "")))

    # Pipeline settings
    max_concurrent_requests: int = 5
    request_timeout: int = 120
    max_retries: int = 3
    retry_base_delay: float = 1.0

    # Escalation settings
    enable_escalation: bool = True
    escalation_confidence_threshold: float = 0.6


def get_config() -> Config:
    """Return the default configuration."""
    return Config()
