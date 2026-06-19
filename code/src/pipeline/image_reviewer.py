"""
Stage 2 component: Per-image structured review.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from ..models.base import ModelAdapter
from ..schemas import ImageObservation, ParsedClaim
from .image_quality import check_image_quality
from ..utils.json_utils import clean_and_load_json

logger = logging.getLogger(__name__)


def review_image(
    image_path: Path,
    parsed_claim: ParsedClaim,
    model: ModelAdapter,
) -> ImageObservation:
    """Run per-image evidence review, merging Pillow quality checks with model observations."""
    image_id = image_path.stem
    
    # 1. Run lightweight Pillow quality checks first
    precheck_flags = check_image_quality(image_path)
    
    # If the image is completely missing or unreadable, return a default failed observation
    if "damage_not_visible" in precheck_flags and not image_path.exists():
        return ImageObservation(
            image_id=image_id,
            object_visible=False,
            object_type_seen="unknown",
            relevant_part_visible=False,
            part_seen="unknown",
            issue_observed="unknown",
            issue_matches_claim=False,
            severity_estimate="unknown",
            quality_issues=["damage_not_visible"],
            is_usable=False,
            mismatch_notes="Image file does not exist or is missing.",
            has_text_instruction=False,
            authenticity_concern=False,
            confidence=0.0,
            raw_description="Missing image file.",
        )

    # 2. Load prompt template
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "image_reviewer.md"

    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding="utf-8")
    else:
        logger.warning(f"image_reviewer.md not found at {prompt_path}, using hardcoded template fallback.")
        prompt_template = "Review image {image_id} for claim: {claim_object} {claimed_part} {claimed_issue}"

    prompt = (
        prompt_template.replace("{claim_object}", parsed_claim.primary_object)
        .replace("{claimed_part}", parsed_claim.primary_part)
        .replace("{claimed_issue}", parsed_claim.issue_hypothesis)
        .replace("{image_id}", image_id)
    )

    try:
        # Call multimodal model
        response_text, was_cached = model.cached_multimodal_call(
            prompt=prompt,
            image_paths=[image_path],
            system_prompt="You are a precise JSON extractor analyzing images.",
        )
        
        parsed_data = clean_and_load_json(response_text)
        
        # Merge precheck quality issues with model-detected quality issues
        model_quality = list(parsed_data.get("quality_issues", []))
        merged_quality = list(set(precheck_flags + model_quality))
        if "none" in merged_quality and len(merged_quality) > 1:
            merged_quality.remove("none")
            
        # Determine if image is usable based on quality issues and model flags
        is_usable = bool(parsed_data.get("is_usable", True))
        if "blurry_image" in merged_quality or "damage_not_visible" in merged_quality:
            is_usable = False

        return ImageObservation(
            image_id=image_id,
            object_visible=bool(parsed_data.get("object_visible", True)),
            object_type_seen=str(parsed_data.get("object_type_seen", parsed_claim.primary_object)),
            relevant_part_visible=bool(parsed_data.get("relevant_part_visible", True)),
            part_seen=str(parsed_data.get("part_seen", "unknown")),
            issue_observed=str(parsed_data.get("issue_observed", "unknown")),
            issue_matches_claim=bool(parsed_data.get("issue_matches_claim", False)),
            severity_estimate=str(parsed_data.get("severity_estimate", "unknown")),
            quality_issues=merged_quality,
            is_usable=is_usable,
            mismatch_notes=str(parsed_data.get("mismatch_notes", "")),
            has_text_instruction=bool(parsed_data.get("has_text_instruction", False)),
            authenticity_concern=bool(parsed_data.get("authenticity_concern", False)),
            confidence=float(parsed_data.get("confidence", 0.7)),
            raw_description=str(parsed_data.get("raw_description", "")),
        )
    except Exception as e:
        logger.error(f"Failed to review image {image_id}: {e}")
        # Return fallback observation
        return ImageObservation(
            image_id=image_id,
            object_visible=False,
            object_type_seen="unknown",
            relevant_part_visible=False,
            part_seen="unknown",
            issue_observed="unknown",
            issue_matches_claim=False,
            severity_estimate="unknown",
            quality_issues=precheck_flags or ["blurry_image"],
            is_usable=False,
            mismatch_notes=f"Image review failed: {e}",
            has_text_instruction=False,
            authenticity_concern=False,
            confidence=0.0,
            raw_description=f"Fallback observation due to failure: {e}",
        )


