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

    # Provider settings
    @property
    def gemini_api_key(self) -> str | None:
        return os.environ.get("GEMINI_API_KEY")

    @property
    def has_gemini(self) -> bool:
        key = self.gemini_api_key
        return key is not None and len(key.strip()) > 0

    # Model settings
    gemini_model: str = "gemini-2.0-flash"
    gemini_thinking_model: str = "gemini-2.5-flash"
    ollama_model: str = "gemma4:e4b"
    ollama_base_url: str = "http://localhost:11434"

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
