"""
Stage 2 component: Cross-image evidence aggregator.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..schemas import (
    ClaimInput,
    ParsedClaim,
    ImageObservation,
    UserHistory,
    EvidenceRequirement,
    AggregatedEvidence,
    RiskFlag,
    Severity,
    IssueType,
)

logger = logging.getLogger(__name__)

MANUAL_REVIEW_FLAGS = {
    "claim_mismatch",
    "wrong_object",
    "non_original_image",
    "possible_manipulation",
    "text_instruction_present",
    "user_history_risk",
}


def aggregate_observations(
    claim_input: ClaimInput,
    parsed_claim: ParsedClaim,
    observations: list[ImageObservation],
    user_history: Optional[UserHistory] = None,
    evidence_requirements: Optional[list[EvidenceRequirement]] = None,
) -> AggregatedEvidence:
    """Merge per-image observations and evaluate against evidence requirements."""
    if not observations:
        return AggregatedEvidence(
            claim_input=claim_input,
            parsed_claim=parsed_claim,
            observations=[],
            user_history=user_history,
            any_object_visible=False,
            any_part_visible=False,
            best_issue_observed="unknown",
            best_severity="unknown",
            any_mismatch=False,
            any_quality_issue=False,
            any_text_instruction=parsed_claim.has_instruction_text,
            any_authenticity_concern=False,
            all_images_usable=False,
            supporting_image_ids=[],
            risk_flags=["manual_review_required"],
            evidence_sufficient=False,
            confidence=0.0,
            escalation_reasons=["no_images_submitted"],
        )

    any_object_visible = any(obs.object_visible for obs in observations)
    any_part_visible = any(obs.relevant_part_visible for obs in observations)
    any_mismatch = any(bool(obs.mismatch_notes) for obs in observations)
    any_quality_issue = any(bool(obs.quality_issues and obs.quality_issues != ["none"]) for obs in observations)
    any_text_instruction = parsed_claim.has_instruction_text or any(obs.has_text_instruction for obs in observations)
    any_authenticity_concern = any(obs.authenticity_concern for obs in observations)
    all_images_usable = all(obs.is_usable for obs in observations)
    usable_obs = [obs for obs in observations if obs.is_usable]
    has_matching_support = any(
        obs.is_usable and obs.relevant_part_visible and obs.issue_matches_claim
        for obs in observations
    )
    has_visible_claimed_part = any(
        obs.is_usable and obs.relevant_part_visible
        for obs in observations
    )

    # 1. Determine best issue observed
    # Order by usability and part visibility, then by confidence descending
    priority_observations = sorted(
        observations,
        key=lambda o: (o.is_usable, o.relevant_part_visible, o.confidence),
        reverse=True
    )
    
    best_issue_observed = "unknown"
    for obs in priority_observations:
        if obs.is_usable and obs.relevant_part_visible and obs.issue_observed not in ("unknown", ""):
            best_issue_observed = obs.issue_observed
            break
            
    if best_issue_observed == "unknown":
        # Fallback to any usable observation's issue
        for obs in priority_observations:
            if obs.is_usable and obs.issue_observed not in ("unknown", ""):
                best_issue_observed = obs.issue_observed
                break

    # 2. Determine best severity estimate
    severity_priority = {
        "high": 4,
        "medium": 3,
        "low": 2,
        "none": 1,
        "unknown": 0
    }
    
    max_severity_val = 0
    best_severity = "unknown"
    for obs in observations:
        if obs.is_usable:
            val = severity_priority.get(obs.severity_estimate.lower(), 0)
            if val > max_severity_val:
                max_severity_val = val
                best_severity = obs.severity_estimate.lower()

    # 3. Supporting image IDs: usable images where issue matches claim
    supporting_image_ids = [
        obs.image_id for obs in observations
        if obs.is_usable and obs.issue_matches_claim
    ]

    # 4. Collect risk flags
    collected_flags = set()
    
    # Flags from image quality checks
    for obs in observations:
        for q in obs.quality_issues:
            q_clean = q.strip().lower()
            if q_clean and q_clean != "none":
                collected_flags.add(q_clean)
                
    # Model-detected mismatches or invalid states
    for obs in observations:
        if obs.is_usable:
            if obs.object_type_seen != "unknown" and obs.object_type_seen.lower() != claim_input.claim_object.lower():
                collected_flags.add("wrong_object")

            if (
                obs.object_visible
                and obs.part_seen != "unknown"
                and not obs.relevant_part_visible
                and not has_visible_claimed_part
            ):
                collected_flags.add("wrong_object_part")

            if (
                obs.object_visible
                and obs.relevant_part_visible
                and not obs.issue_matches_claim
            ):
                # If damage was observed but didn't match claim
                if obs.issue_observed not in ("none", "unknown"):
                    collected_flags.add("claim_mismatch")

        if obs.authenticity_concern:
            collected_flags.add("non_original_image")

        if obs.has_text_instruction:
            collected_flags.add("text_instruction_present")

    if parsed_claim.has_instruction_text:
        collected_flags.add("text_instruction_present")

    # Add user history risk flags
    if user_history and user_history.has_risk():
        collected_flags.add("user_history_risk")
        for flag in user_history.get_flag_list():
            if flag and flag != "none":
                collected_flags.add(flag)

    # 5. Evaluate evidence requirements
    evidence_sufficient = True
    reqs_checked = evidence_requirements or []
    
    # If requirements are provided, evaluate them
    if reqs_checked:
        for req in reqs_checked:
            req_id = req.requirement_id
            if req_id == "REQ_REVIEW_TRUST":
                if not any(obs.is_usable for obs in observations):
                    evidence_sufficient = False
            elif req_id == "REQ_GENERAL_OBJECT_PART":
                if not any(obs.object_visible and obs.relevant_part_visible and obs.is_usable for obs in observations):
                    evidence_sufficient = False
            elif req_id == "REQ_GENERAL_MULTI_IMAGE":
                if len(observations) > 1:
                    # Multi-image: require at least one usable image showing object or part
                    if not any((obs.object_visible or obs.relevant_part_visible) and obs.is_usable for obs in observations):
                        evidence_sufficient = False
            else:
                # Specific object/part check: requires at least one usable image with both object & part visible
                if not any(obs.object_visible and obs.relevant_part_visible and obs.is_usable for obs in observations):
                    evidence_sufficient = False
    else:
        # Fallback default: at least one usable image shows the object and part
        evidence_sufficient = any(
            obs.object_visible and obs.relevant_part_visible and obs.is_usable
            for obs in observations
        )

    if len(usable_obs) > 1 and "wrong_object" in collected_flags:
        evidence_sufficient = False

    # 6. Confidence and escalation reasons
    if usable_obs:
        confidence = sum(obs.confidence for obs in usable_obs) / len(usable_obs)
    else:
        confidence = 0.0

    escalation_reasons = []
    if confidence < 0.6:
        escalation_reasons.append("low_confidence")
    if any_authenticity_concern:
        escalation_reasons.append("authenticity_concern")
    if any_text_instruction:
        escalation_reasons.append("text_instruction_present")
    if user_history and user_history.has_risk():
        escalation_reasons.append("user_history_risk")
    if any_mismatch:
        escalation_reasons.append("mismatch_observed")
    if not evidence_sufficient:
        escalation_reasons.append("insufficient_evidence")

    # Reserve manual review for substantive risk or fraud-style triggers.
    if collected_flags.intersection(MANUAL_REVIEW_FLAGS):
        collected_flags.add("manual_review_required")

    return AggregatedEvidence(
        claim_input=claim_input,
        parsed_claim=parsed_claim,
        observations=observations,
        user_history=user_history,
        any_object_visible=any_object_visible,
        any_part_visible=any_part_visible,
        best_issue_observed=best_issue_observed,
        best_severity=best_severity,
        any_mismatch=any_mismatch,
        any_quality_issue=any_quality_issue,
        any_text_instruction=any_text_instruction,
        any_authenticity_concern=any_authenticity_concern,
        all_images_usable=all_images_usable,
        supporting_image_ids=supporting_image_ids,
        risk_flags=list(collected_flags),
        evidence_sufficient=evidence_sufficient,
        confidence=confidence,
        escalation_reasons=escalation_reasons,
    )
