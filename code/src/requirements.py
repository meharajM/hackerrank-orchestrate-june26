"""
Evidence requirements repository abstractions and file-backed implementation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .schemas import EvidenceRequirement
from .csv_io import read_evidence_requirements, get_evidence_requirements_for_claim


@runtime_checkable
class RequirementsRepository(Protocol):
    """Abstract lookup interface for evidence requirements."""

    def get_requirements_for_claim(
        self, claim_object: str, issue_family: Optional[str] = None
    ) -> list[EvidenceRequirement]:
        """Get all requirements applicable to a specific claim object and issue family."""
        ...


class FileRequirementsRepository:
    """File-backed repository for evidence requirements."""

    def __init__(self, csv_path: Path):
        self._requirements = read_evidence_requirements(csv_path)

    def get_requirements_for_claim(
        self, claim_object: str, issue_family: Optional[str] = None
    ) -> list[EvidenceRequirement]:
        """Get all requirements applicable to a specific claim object and issue family."""
        return get_evidence_requirements_for_claim(
            self._requirements, claim_object, issue_family
        )


class RequirementsManager(FileRequirementsRepository):
    """Backward-compatible alias for file-backed requirements lookups."""


__all__ = [
    "RequirementsRepository",
    "FileRequirementsRepository",
    "RequirementsManager",
]
