"""
Stage 2 component: Deterministic adjudication engine.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..schemas import (
    ClaimOutput,
    AggregatedEvidence,
    ClaimStatus,
    IssueType,
    Severity,
    RiskFlag,
    get_valid_parts,
    normalize_object_part,
    serialize_risk_flags,
    serialize_image_ids,
)

logger = logging.getLogger(__name__)


def adjudicate(evidence: AggregatedEvidence) -> ClaimOutput:
    """Apply deterministic business rules to intermediate evidence to produce a ClaimOutput."""
    claim = evidence.claim_input
    parsed = evidence.parsed_claim
    obs_list = evidence.observations
    
    # Initialize defaults
    claim_status = ClaimStatus.NOT_ENOUGH_INFORMATION
    valid_image = "true"
    evidence_standard_met = "false"
    issue_type = IssueType.UNKNOWN
    object_part = "unknown"
    severity = Severity.UNKNOWN
    
    status_justification = ""
    esm_reason = ""
    supporting_image_ids_list = []
    
    # Helper: get usable observations
    usable_obs = [o for o in obs_list if o.is_usable]
    
    # Gather all risk flags from evidence
    risk_flags_list = list(evidence.risk_flags)
    has_wrong_object_flag = "wrong_object" in risk_flags_list
    
    # ── Precedence Rules ────────────────────────────────────────────────
    
    # Rule 1: Authenticity / non-original image concern
    if evidence.any_authenticity_concern:
        claim_status = ClaimStatus.NOT_ENOUGH_INFORMATION
        valid_image = "false"
        evidence_standard_met = "false"
        issue_type = IssueType.UNKNOWN
        object_part = normalize_object_part(parsed.primary_part, claim.claim_object)
        severity = Severity.UNKNOWN
        esm_reason = "Evidence fails authenticity verification."
        status_justification = "Authenticity check failed: potential non-original or modified image detected."
        # Supporting images for authenticity failure can be the flagged ones
        supporting_image_ids_list = [o.image_id for o in obs_list if o.authenticity_concern]

    # Rule 2: Wrong object detected in all usable images
    elif usable_obs and all(
        (not o.object_visible) or (o.object_type_seen != "unknown" and o.object_type_seen.lower() != claim.claim_object.lower())
        for o in usable_obs
    ):
        claim_status = ClaimStatus.CONTRADICTED
        valid_image = "true"
        evidence_standard_met = "false"
        issue_type = IssueType.UNKNOWN
        object_part = "unknown"
        severity = Severity.NONE
        esm_reason = f"No images showing the claimed object ({claim.claim_object}) were found."
        status_justification = f"Claim contradicted because submitted images show a different object, not the claimed {claim.claim_object}."
        supporting_image_ids_list = [o.image_id for o in usable_obs]

    # Rule 3: No images submitted or all images unusable due to quality
    elif not usable_obs:
        claim_status = ClaimStatus.NOT_ENOUGH_INFORMATION
        valid_image = "false" if obs_list else "true"  # if empty list, image exists is technically false but not invalid
        evidence_standard_met = "false"
        issue_type = IssueType.UNKNOWN
        object_part = normalize_object_part(parsed.primary_part, claim.claim_object)
        severity = Severity.UNKNOWN
        esm_reason = "No usable or clear images were submitted to verify the claim."
        status_justification = "Not enough information because all submitted images are unusable due to quality issues (e.g., blurry, dark, low visibility)."
        supporting_image_ids_list = []

    # Rule 4: Wrong part shown (object visible, but claimed part not visible in any usable image)
    elif not evidence.any_part_visible:
        claim_status = ClaimStatus.NOT_ENOUGH_INFORMATION
        valid_image = "true"
        evidence_standard_met = "false"
        issue_type = IssueType.UNKNOWN
        # Use first usable observation's part seen if visible, otherwise unknown
        object_part = "unknown"
        severity = Severity.UNKNOWN
        esm_reason = f"The claimed part ({parsed.primary_part}) is not visible in any usable image."
        status_justification = f"Cannot verify the claim because the claimed part '{parsed.primary_part}' is not visible in the submitted images."
        supporting_image_ids_list = []

    # Rule 5: No damage observed on the visible claimed part (contradiction)
    elif any(o.is_usable and o.relevant_part_visible and o.issue_observed == "none" for o in usable_obs):
        # We see the claimed part clearly, and it has NO damage
        claim_status = ClaimStatus.CONTRADICTED
        valid_image = "true"
        evidence_standard_met = "true"
        issue_type = IssueType.NONE
        
        # Resolve part seen
        part_candidates = [o.part_seen for o in usable_obs if o.relevant_part_visible and o.part_seen != "unknown"]
        object_part = normalize_object_part(part_candidates[0] if part_candidates else parsed.primary_part, claim.claim_object)
        
        severity = Severity.NONE
        esm_reason = f"The claimed part ({parsed.primary_part}) is clearly visible and inspected."
        status_justification = f"Claim contradicted because the claimed part '{parsed.primary_part}' is visible with no visible damage."
        # Supporting images are those showing no damage
        supporting_image_ids_list = [o.image_id for o in usable_obs if o.relevant_part_visible and o.issue_observed == "none"]

    # Rule 6: Part visible, damage matches claim (supported)
    elif any(o.is_usable and o.relevant_part_visible and o.issue_matches_claim for o in usable_obs):
        claim_status = ClaimStatus.SUPPORTED
        valid_image = "true"
        evidence_standard_met = "true" if evidence.evidence_sufficient else "false"

        # Get matching observations
        matching_obs = [o for o in usable_obs if o.relevant_part_visible and o.issue_matches_claim]
        best_obs = sorted(matching_obs, key=lambda o: o.confidence, reverse=True)[0]

        # Use best issue and severity
        issue_type = IssueType(evidence.best_issue_observed) if evidence.best_issue_observed in [e.value for e in IssueType] else IssueType.UNKNOWN
        object_part = normalize_object_part(best_obs.part_seen if best_obs.part_seen != "unknown" else parsed.primary_part, claim.claim_object)
        severity = Severity(evidence.best_severity) if evidence.best_severity in [e.value for e in Severity] else Severity.UNKNOWN

        if evidence.evidence_sufficient and not has_wrong_object_flag:
            esm_reason = "Minimum evidence requirements satisfied."
            status_justification = f"Claim supported: damage '{parsed.issue_hypothesis}' observed on '{object_part}' in image {best_obs.image_id}."
            supporting_image_ids_list = [o.image_id for o in matching_obs]
        else:
            claim_status = ClaimStatus.NOT_ENOUGH_INFORMATION
            evidence_standard_met = "false"
            esm_reason = "A matching close-up exists, but the image set is not reliable enough to verify the full claim."
            status_justification = (
                f"Not enough information: image {best_obs.image_id} appears consistent with the claim, "
                "but the full image set does not meet the evidence standard."
            )
            supporting_image_ids_list = [o.image_id for o in matching_obs]

    # Rule 7: Part visible, damage observed but mismatch (contradicted or mismatch)
    elif any(o.is_usable and o.relevant_part_visible and o.issue_observed not in ("none", "unknown") for o in usable_obs):
        claim_status = ClaimStatus.CONTRADICTED
        valid_image = "true"
        evidence_standard_met = "true" if evidence.evidence_sufficient else "false"
        
        mismatched_obs = [o for o in usable_obs if o.relevant_part_visible and o.issue_observed not in ("none", "unknown")]
        best_obs = sorted(mismatched_obs, key=lambda o: o.confidence, reverse=True)[0]
        
        issue_type = IssueType(best_obs.issue_observed) if best_obs.issue_observed in [e.value for e in IssueType] else IssueType.UNKNOWN
        object_part = normalize_object_part(best_obs.part_seen if best_obs.part_seen != "unknown" else parsed.primary_part, claim.claim_object)
        severity = Severity(best_obs.severity_estimate) if best_obs.severity_estimate in [e.value for e in Severity] else Severity.UNKNOWN
        
        esm_reason = "Inspected claimed part, but found mismatching condition."
        status_justification = f"Claim contradicted: claimed '{parsed.issue_hypothesis}' but observed '{best_obs.issue_observed}' on '{object_part}'."
        supporting_image_ids_list = [o.image_id for o in mismatched_obs]

    # Rule 8: Low confidence or ambiguous cases
    else:
        claim_status = ClaimStatus.NOT_ENOUGH_INFORMATION
        valid_image = "true"
        evidence_standard_met = "false"
        issue_type = IssueType.UNKNOWN
        object_part = normalize_object_part(parsed.primary_part, claim.claim_object)
        severity = Severity.UNKNOWN
        esm_reason = "Evidence is ambiguous or has low confidence."
        status_justification = "Not enough information: images are ambiguous, or review confidence is too low to make a determination."
        supporting_image_ids_list = []

    # ── Post-processing and Normalization ──────────────────────────────

    # Serialize fields properly
    serialized_flags = serialize_risk_flags(risk_flags_list)
    serialized_supporting_ids = serialize_image_ids(supporting_image_ids_list)
    
    # Final validation fallback checks
    if object_part == "unknown" and claim_status == ClaimStatus.SUPPORTED:
        object_part = normalize_object_part(parsed.primary_part, claim.claim_object)
        
    return ClaimOutput(
        user_id=claim.user_id,
        image_paths=claim.image_paths,
        user_claim=claim.user_claim,
        claim_object=claim.claim_object,
        evidence_standard_met="true" if evidence_standard_met == "true" else "false",
        evidence_standard_met_reason=esm_reason or "Adjudication completed.",
        risk_flags=serialized_flags,
        issue_type=issue_type.value,
        object_part=object_part,
        claim_status=claim_status.value,
        claim_status_justification=status_justification or "Review completed.",
        supporting_image_ids=serialized_supporting_ids,
        valid_image=valid_image,
        severity=severity.value,
    )
