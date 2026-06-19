"""
Stage 1: Claim parsing and structured details extraction.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from ..models.base import ModelAdapter
from ..schemas import ClaimInput, ParsedClaim
from ..utils.json_utils import clean_and_load_json

logger = logging.getLogger(__name__)


def parse_claim(claim: ClaimInput, model: ModelAdapter) -> ParsedClaim:
    """Parse the user claim text into structured details."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "claim_parser.md"

    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding="utf-8")
    else:
        logger.warning(f"claim_parser.md not found at {prompt_path}, using hardcoded template fallback.")
        prompt_template = "Parse claim text: {user_claim}"

    prompt = prompt_template.replace("{user_claim}", claim.user_claim)
    try:
        response_text, was_cached = model.cached_text_call(prompt=prompt, system_prompt="You are a precise JSON extractor.")
        parsed_data = clean_and_load_json(response_text)
        
        # Build Pydantic model
        return ParsedClaim(
            primary_object=str(parsed_data.get("primary_object", claim.claim_object)),
            primary_part=str(parsed_data.get("primary_part", "unknown")),
            issue_hypothesis=str(parsed_data.get("issue_hypothesis", "unknown")),
            secondary_targets=list(parsed_data.get("secondary_targets", [])),
            has_instruction_text=bool(parsed_data.get("has_instruction_text", False)),
            instruction_text_detail=str(parsed_data.get("instruction_text_detail", "")),
            language_notes=str(parsed_data.get("language_notes", "english")),
            confidence=float(parsed_data.get("confidence", 0.8)),
        )
    except Exception as e:
        logger.error(f"Failed to parse claim text for user {claim.user_id}: {e}")
        # Return fallback ParsedClaim
        return ParsedClaim(
            primary_object=claim.claim_object,
            primary_part="unknown",
            issue_hypothesis="unknown",
            secondary_targets=[],
            has_instruction_text=False,
            instruction_text_detail="",
            language_notes="english",
            confidence=0.5,
        )


