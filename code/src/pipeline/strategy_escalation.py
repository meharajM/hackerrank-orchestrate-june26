"""
Strategy C: Disagreement-aware and confidence-based escalation pipeline.
Runs Strategy B (staged) by default, and escalates to a hosted model (Gemini) on low confidence or flags.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..models.base import ModelAdapter
from ..prompting import PromptProvider
from ..runtime import RuntimeSettings
from ..schemas import (
    ClaimInput,
    ClaimOutput,
    UserHistory,
    EvidenceRequirement,
    serialize_risk_flags,
)
from ..image_io import resolve_all_image_paths
from .claim_parser import parse_claim
from .image_reviewer import review_image
from .aggregation import aggregate_observations
from .adjudication import adjudicate
from .reviewer import review_claim

logger = logging.getLogger(__name__)


def run_escalation_pipeline(
    claim: ClaimInput,
    model: ModelAdapter,
    escalation_model: ModelAdapter,
    dataset_dir: Path,
    stage2_model: ModelAdapter | None = None,
    user_history: Optional[UserHistory] = None,
    evidence_requirements: Optional[list[EvidenceRequirement]] = None,
    prompt_provider: PromptProvider | None = None,
    runtime_settings: RuntimeSettings | None = None,
) -> ClaimOutput:
    """Run Strategy C: Conditional escalation pipeline."""
    runtime_settings = runtime_settings or RuntimeSettings()
    stage2_model = stage2_model or model
    # 1. Run Staged Pipeline (Strategy B) internally to get intermediate evidence
    parsed_claim = parse_claim(
        claim,
        model,
        prompt_provider=prompt_provider,
        runtime_settings=runtime_settings,
    )
    image_info = resolve_all_image_paths(claim.image_paths, dataset_dir)
    
    observations = []
    for img_id, img_path, exists in image_info:
        obs = review_image(
            img_path,
            parsed_claim,
            stage2_model,
            prompt_provider=prompt_provider,
            runtime_settings=runtime_settings,
        )
        observations.append(obs)

    evidence = aggregate_observations(
        claim_input=claim,
        parsed_claim=parsed_claim,
        observations=observations,
        user_history=user_history,
        evidence_requirements=evidence_requirements,
    )
    
    provisional_output = adjudicate(evidence)

    # 2. Check escalation triggers
    escalated = False
    reasons = []

    if evidence.confidence < runtime_settings.escalation_confidence_threshold:
        escalated = True
        reasons.append(f"low_confidence_({evidence.confidence:.2f})")
        
    prov_flags = [f.strip() for f in provisional_output.risk_flags.split(";") if f.strip() and f.strip() != "none"]
    if "manual_review_required" in prov_flags or "manual_review_required" in evidence.risk_flags:
        escalated = True
        reasons.append("manual_review_required")
        
    if evidence.any_authenticity_concern:
        escalated = True
        reasons.append("authenticity_concern")
        
    if evidence.any_text_instruction:
        escalated = True
        reasons.append("text_instruction_present")

    # 3. Handle escalation if triggered and escalation model is available
    if escalated:
        if escalation_model.is_available():
            logger.info(f"Escalating claim for user {claim.user_id} due to: {', '.join(reasons)}")
            try:
                # Call holistic re-review on the escalation model
                escalated_output = review_claim(
                    claim=claim,
                    model=escalation_model,
                    dataset_dir=dataset_dir,
                    user_history=user_history,
                    evidence_requirements=evidence_requirements,
                    prompt_provider=prompt_provider,
                )

                # Merge Policy:
                # - Preserve provisional evidence_standard_met and valid_image
                # - Override claim_status, issue_type, severity, claim_status_justification, and supporting_image_ids
                # - Union risk flags
                merged_output = provisional_output.model_copy()
                merged_output.claim_status = escalated_output.claim_status
                merged_output.issue_type = escalated_output.issue_type
                merged_output.severity = escalated_output.severity
                merged_output.supporting_image_ids = escalated_output.supporting_image_ids
                
                # Prepend escalation note to justification
                reason_str = ", ".join(reasons)
                merged_output.claim_status_justification = (
                    f"[Escalated: {reason_str}] {escalated_output.claim_status_justification}"
                )
                
                # Union risk flags
                esc_flags = [f.strip() for f in escalated_output.risk_flags.split(";") if f.strip() and f.strip() != "none"]
                merged_output.risk_flags = serialize_risk_flags(list(set(prov_flags + esc_flags)))
                
                return merged_output
            except Exception as e:
                logger.error(f"Escalation model call failed, falling back to provisional output: {e}")
                # Fallback to provisional output if call fails
                return provisional_output
        else:
            logger.warning(
                f"Escalation triggered for user {claim.user_id} but escalation model is unavailable. "
                "Returning provisional output."
            )
            return provisional_output
    else:
        # Not escalated: return provisional Strategy B output
        return provisional_output
