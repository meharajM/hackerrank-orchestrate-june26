"""
Stage 1: Claim parsing and structured details extraction.
"""
from __future__ import annotations

import logging

from ..models.base import ModelAdapter
from ..prompting import PromptProvider, resolve_prompt
from ..schemas import normalize_object_part
from ..runtime import RuntimeSettings
from ..schemas import ClaimInput, ParsedClaim
from ..utils.json_utils import clean_and_load_json
from .claim_rules import extract_claim_signals, normalize_issue_type

logger = logging.getLogger(__name__)


def parse_claim(
    claim: ClaimInput,
    model: ModelAdapter,
    prompt_provider: PromptProvider | None = None,
    runtime_settings: RuntimeSettings | None = None,
) -> ParsedClaim:
    """Parse the user claim text into structured details."""
    heuristic = extract_claim_signals(claim.user_claim, claim.claim_object)
    if prompt_provider is None:
        from ..config import get_config
        from ..prompting import FilePromptProvider

        prompt_provider = FilePromptProvider(get_config().prompts_dir)
    runtime_settings = runtime_settings or RuntimeSettings()

    prompt_template = resolve_prompt(
        prompt_provider,
        name="claim_parser",
        fallback="Parse claim text: {user_claim}",
        shared_sections=("json_only",),
    )

    prompt = prompt_template.replace("{user_claim}", claim.user_claim)
    try:
        response_text, was_cached = model.cached_text_call(
            prompt=prompt,
            system_prompt=runtime_settings.claim_parser_system_prompt,
        )
        parsed_data = clean_and_load_json(response_text)

        return ParsedClaim(
            primary_object=str(parsed_data.get("primary_object", claim.claim_object)),
            primary_part=_normalize_part_value(
                _choose_value(
                    str(parsed_data.get("primary_part", "unknown")),
                    heuristic.primary_part,
                ),
                claim.claim_object,
            ),
            issue_hypothesis=normalize_issue_type(
                _choose_value(
                    str(parsed_data.get("issue_hypothesis", "unknown")),
                    heuristic.issue_hypothesis,
                ),
            ),
            secondary_targets=_merge_secondary_targets(
                list(parsed_data.get("secondary_targets", [])),
                heuristic.secondary_targets,
                claim.claim_object,
            ),
            has_instruction_text=bool(parsed_data.get("has_instruction_text", False)) or heuristic.has_instruction_text,
            instruction_text_detail=str(parsed_data.get("instruction_text_detail", "")).strip() or heuristic.instruction_text_detail,
            language_notes=_choose_language_note(
                str(parsed_data.get("language_notes", "english")),
                heuristic.language_notes,
            ),
            confidence=max(float(parsed_data.get("confidence", 0.8)), min(heuristic.confidence, 0.85)),
        )
    except Exception as e:
        logger.error(f"Failed to parse claim text for user {claim.user_id}: {e}")
        return ParsedClaim(
            primary_object=claim.claim_object,
            primary_part=heuristic.primary_part,
            issue_hypothesis=heuristic.issue_hypothesis,
            secondary_targets=heuristic.secondary_targets,
            has_instruction_text=heuristic.has_instruction_text,
            instruction_text_detail=heuristic.instruction_text_detail,
            language_notes=heuristic.language_notes,
            confidence=heuristic.confidence,
        )


def _choose_value(model_value: str, heuristic_value: str) -> str:
    """Prefer a specific model answer, then fall back to heuristic extraction."""
    cleaned_model = model_value.strip().lower()
    cleaned_heuristic = heuristic_value.strip().lower()
    if cleaned_model and cleaned_model != "unknown":
        return cleaned_model
    if cleaned_heuristic and cleaned_heuristic != "unknown":
        return cleaned_heuristic
    return "unknown"


def _merge_secondary_targets(model_targets: list[str], heuristic_targets: list[str], claim_object: str) -> list[str]:
    merged: list[str] = []
    for target in model_targets + heuristic_targets:
        cleaned = _normalize_part_value(str(target).strip().lower(), claim_object)
        if cleaned and cleaned not in merged:
            merged.append(cleaned)
    return merged


def _choose_language_note(model_value: str, heuristic_value: str) -> str:
    if heuristic_value and heuristic_value != "english":
        return heuristic_value
    cleaned_model = model_value.strip().lower()
    return cleaned_model or heuristic_value or "english"


def _normalize_part_value(value: str, claim_object: str) -> str:
    normalized = normalize_object_part(value, claim_object)
    if normalized != "unknown":
        return normalized
    return extract_claim_signals(value, claim_object).primary_part
