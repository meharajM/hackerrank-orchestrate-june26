"""
Strategy A: Holistic single-pass baseline.
Directly wraps the existing reviewer.review_claim module.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..models.base import ModelAdapter
from ..schemas import (
    ClaimInput,
    ClaimOutput,
    UserHistory,
    EvidenceRequirement,
)
from .reviewer import review_claim

logger = logging.getLogger(__name__)


def run_single_pass_pipeline(
    claim: ClaimInput,
    model: ModelAdapter,
    dataset_dir: Path,
    user_history: Optional[UserHistory] = None,
    evidence_requirements: Optional[list[EvidenceRequirement]] = None,
) -> ClaimOutput:
    """Run Strategy A: Single-pass holistic pipeline.

    Delegates directly to reviewer.review_claim.
    """
    logger.info(f"Running Single-Pass Holistic Pipeline (Strategy A) for claim: {claim.user_id}")
    
    return review_claim(
        claim=claim,
        model=model,
        dataset_dir=dataset_dir,
        user_history=user_history,
        evidence_requirements=evidence_requirements,
    )
