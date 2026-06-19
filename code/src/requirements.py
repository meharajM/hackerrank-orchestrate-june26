"""
Evidence requirements manager.
Wraps the logic for loading and filtering evidence requirements.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .schemas import EvidenceRequirement
from .csv_io import read_evidence_requirements, get_evidence_requirements_for_claim


class RequirementsManager:
    """Manages lookups and filtering for evidence requirements."""

    def __init__(self, csv_path: Path):
        self._requirements = read_evidence_requirements(csv_path)

    def get_requirements_for_claim(
        self, claim_object: str, issue_family: Optional[str] = None
    ) -> list[EvidenceRequirement]:
        """Get all requirements applicable to a specific claim object and issue family."""
        return get_evidence_requirements_for_claim(
            self._requirements, claim_object, issue_family
        )
