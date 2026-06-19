"""
Strategy B: Staged evidence review pipeline.
Claims parser -> Per-image review -> Aggregator -> Adjudicator.
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
from ..image_io import resolve_all_image_paths
from .claim_parser import parse_claim
from .image_reviewer import review_image
from .aggregation import aggregate_observations
from .adjudication import adjudicate

logger = logging.getLogger(__name__)


def run_staged_pipeline(
    claim: ClaimInput,
    model: ModelAdapter,
    dataset_dir: Path,
    user_history: Optional[UserHistory] = None,
    evidence_requirements: Optional[list[EvidenceRequirement]] = None,
) -> ClaimOutput:
    """Run Strategy B: Staged pipeline.

    Connects claim parser, per-image reviewer, aggregator, and adjudicator.
    """
    logger.info(f"Running Staged Pipeline (Strategy B) for claim: {claim.user_id}")

    # 1. Parse claim
    parsed_claim = parse_claim(claim, model)

    # 2. Resolve image paths
    image_info = resolve_all_image_paths(claim.image_paths, dataset_dir)
    
    observations = []
    for img_id, img_path, exists in image_info:
        # Review image (handles missing file cases internally)
        obs = review_image(img_path, parsed_claim, model)
        observations.append(obs)

    # 3. Aggregate evidence
    evidence = aggregate_observations(
        claim_input=claim,
        parsed_claim=parsed_claim,
        observations=observations,
        user_history=user_history,
        evidence_requirements=evidence_requirements,
    )

    # 4. Adjudicate
    output = adjudicate(evidence)
    return output
