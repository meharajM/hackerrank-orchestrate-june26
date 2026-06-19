"""
User history manager.
Wraps the historical claim data lookup.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .schemas import UserHistory
from .csv_io import read_user_history


class HistoryManager:
    """Manages lookups for user claim history."""

    def __init__(self, csv_path: Path):
        self._history = read_user_history(csv_path)

    def get_user_history(self, user_id: str) -> Optional[UserHistory]:
        """Look up history for a user, returning None if not found."""
        return self._history.get(user_id)
