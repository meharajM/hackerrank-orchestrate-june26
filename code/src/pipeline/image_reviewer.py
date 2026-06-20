"""
Stage 2 component: Per-image structured review.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..models.base import ModelAdapter
from ..prompting import PromptProvider, resolve_prompt
from ..runtime import RuntimeSettings
from ..schemas import ImageObservation, ParsedClaim
from .image_quality import check_image_quality
from .claim_rules import (
    build_mismatch_notes,
    issue_matches_claim,
    normalize_issue_type,
    part_matches_claim,
)
from ..utils.json_utils import clean_and_load_json

logger = logging.getLogger(__name__)


def review_image(
    image_path: Path,
    parsed_claim: ParsedClaim,
    model: ModelAdapter,
    prompt_provider: PromptProvider | None = None,
    runtime_settings: RuntimeSettings | None = None,
) -> ImageObservation:
    """Run per-image evidence review, merging Pillow quality checks with model observations."""
    image_id = image_path.stem
    if prompt_provider is None:
        from ..config import get_config
        from ..prompting import FilePromptProvider

        prompt_provider = FilePromptProvider(get_config().prompts_dir)
    runtime_settings = runtime_settings or RuntimeSettings()
    
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
    prompt_template = resolve_prompt(
        prompt_provider,
        name="image_reviewer",
        fallback="Review image {image_id} for claim: {claim_object} {claimed_part} {claimed_issue}",
        shared_sections=("json_only", "vision_grounding"),
    )

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
            system_prompt=runtime_settings.image_reviewer_system_prompt,
        )
        
        parsed_data = clean_and_load_json(response_text)

        # Merge precheck quality issues with model-detected quality issues
        raw_quality = parsed_data.get("quality_issues", [])
        if isinstance(raw_quality, str):
            model_quality = [raw_quality]
        else:
            model_quality = [str(item).strip().lower() for item in raw_quality]
        merged_quality = list(set(precheck_flags + model_quality))
        if "none" in merged_quality and len(merged_quality) > 1:
            merged_quality.remove("none")

        object_type_seen = str(parsed_data.get("object_type_seen", "unknown")).strip().lower()
        part_seen = str(parsed_data.get("part_seen", "unknown")).strip().lower()
        issue_observed = normalize_issue_type(str(parsed_data.get("issue_observed", "unknown")))
        object_visible = bool(parsed_data.get("object_visible", object_type_seen != "unknown"))

        # Determine if image is usable based on quality issues and model flags
        object_matches_claim = object_type_seen in {"unknown", parsed_claim.primary_object}
        relevant_part_visible = bool(
            parsed_data.get(
                "relevant_part_visible",
                object_visible
                and object_matches_claim
                and part_matches_claim(
                    parsed_claim.primary_part,
                    part_seen,
                    parsed_claim.primary_object,
                ),
            )
        )
        local_issue_match = bool(
            parsed_data.get(
                "issue_matches_claim",
                relevant_part_visible
                and issue_matches_claim(
                    parsed_claim.issue_hypothesis,
                    issue_observed,
                ),
            )
        )
        mismatch_notes = build_mismatch_notes(
            claim_object=parsed_claim.primary_object,
            claimed_part=parsed_claim.primary_part,
            claimed_issue=parsed_claim.issue_hypothesis,
            object_visible=object_visible,
            object_type_seen=object_type_seen,
            part_seen=part_seen,
            issue_observed=issue_observed,
        )

        is_usable = bool(parsed_data.get("is_usable", relevant_part_visible or local_issue_match))
        if (
            "blurry_image" in merged_quality
            or "damage_not_visible" in merged_quality
            or (not object_visible and object_type_seen == "unknown")
        ):
            is_usable = False

        return ImageObservation(
            image_id=image_id,
            object_visible=object_visible,
            object_type_seen=object_type_seen,
            relevant_part_visible=relevant_part_visible,
            part_seen=part_seen,
            issue_observed=issue_observed,
            issue_matches_claim=local_issue_match,
            severity_estimate=str(parsed_data.get("severity_estimate", "unknown")),
            quality_issues=merged_quality,
            is_usable=is_usable,
            mismatch_notes=mismatch_notes or str(parsed_data.get("mismatch_notes", "")),
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
