"""
User history repository abstractions and file-backed implementation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .schemas import UserHistory
from .csv_io import read_user_history


@runtime_checkable
class HistoryRepository(Protocol):
    """Abstract lookup interface for user-history data."""

    def get_user_history(self, user_id: str) -> Optional[UserHistory]:
        """Look up history for a user, returning None if not found."""
        ...


class FileHistoryRepository:
    """File-backed repository for user claim history."""

    def __init__(self, csv_path: Path):
        self._history = read_user_history(csv_path)

    def get_user_history(self, user_id: str) -> Optional[UserHistory]:
        """Look up history for a user, returning None if not found."""
        return self._history.get(user_id)


class HistoryManager(FileHistoryRepository):
    """Backward-compatible alias for file-backed history lookups."""


__all__ = [
    "HistoryRepository",
    "FileHistoryRepository",
    "HistoryManager",
]
