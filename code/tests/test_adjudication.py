import pytest
from pathlib import Path
from src.schemas import ClaimInput, ParsedClaim, ImageObservation, UserHistory
from src.pipeline.aggregation import aggregate_observations
from src.pipeline.adjudication import adjudicate
from src.pipeline.strategy_staged import run_staged_pipeline
from src.pipeline.strategy_escalation import run_escalation_pipeline
from src.models import MockAdapter

def test_aggregate_observations_basic():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg;img_2.jpg",
        user_claim="Laptop screen has a scratch.",
        claim_object="laptop"
    )
    parsed_claim = ParsedClaim(
        primary_object="laptop",
        primary_part="screen",
        issue_hypothesis="scratch",
        confidence=0.9
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=True,
            object_type_seen="laptop",
            relevant_part_visible=True,
            part_seen="screen",
            issue_observed="scratch",
            issue_matches_claim=True,
            severity_estimate="low",
            is_usable=True,
            confidence=0.8
        ),
        ImageObservation(
            image_id="img_2",
            object_visible=True,
            object_type_seen="laptop",
            relevant_part_visible=True,
            part_seen="keyboard",
            issue_observed="none",
            issue_matches_claim=False,
            severity_estimate="none",
            is_usable=True,
            confidence=0.7
        )
    ]
    
    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    
    assert evidence.any_object_visible is True
    assert evidence.any_part_visible is True
    assert evidence.best_issue_observed == "scratch"
    assert evidence.best_severity == "low"
    assert evidence.supporting_image_ids == ["img_1"]
    assert "claim_mismatch" not in evidence.risk_flags
    assert evidence.evidence_sufficient is True
    assert evidence.confidence == 0.75

def test_aggregate_observations_insufficient():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg",
        user_claim="Laptop screen scratch",
        claim_object="laptop"
    )
    parsed_claim = ParsedClaim(
        primary_object="laptop",
        primary_part="screen",
        issue_hypothesis="scratch"
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=False,
            relevant_part_visible=False,
            is_usable=True,
            confidence=0.5
        )
    ]
    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    assert evidence.evidence_sufficient is False
    assert "manual_review_required" not in evidence.risk_flags
    assert "insufficient_evidence" in evidence.escalation_reasons

def test_adjudicate_wrong_object():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg",
        user_claim="Car front bumper dented",
        claim_object="car"
    )
    parsed_claim = ParsedClaim(
        primary_object="car",
        primary_part="front_bumper",
        issue_hypothesis="dent"
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=True,
            object_type_seen="laptop", # Mismatch: laptop instead of car
            relevant_part_visible=False,
            is_usable=True,
            confidence=0.9
        )
    ]
    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    output = adjudicate(evidence)
    
    assert output.claim_status == "contradicted"
    assert "wrong_object" in output.risk_flags
    assert output.evidence_standard_met == "false"
    assert output.supporting_image_ids == "img_1"

def test_adjudicate_no_damage():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg",
        user_claim="Car windshield cracked",
        claim_object="car"
    )
    parsed_claim = ParsedClaim(
        primary_object="car",
        primary_part="windshield",
        issue_hypothesis="crack"
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=True,
            object_type_seen="car",
            relevant_part_visible=True,
            part_seen="windshield",
            issue_observed="none", # Windshield is undamaged
            issue_matches_claim=False,
            is_usable=True,
            confidence=0.95
        )
    ]
    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    output = adjudicate(evidence)
    
    assert output.claim_status == "contradicted"
    assert output.issue_type == "none"
    assert output.severity == "none"
    assert output.evidence_standard_met == "true"
    assert output.supporting_image_ids == "img_1"

def test_adjudicate_supported():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg",
        user_claim="Laptop screen has crack",
        claim_object="laptop"
    )
    parsed_claim = ParsedClaim(
        primary_object="laptop",
        primary_part="screen",
        issue_hypothesis="crack"
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=True,
            object_type_seen="laptop",
            relevant_part_visible=True,
            part_seen="screen",
            issue_observed="crack",
            issue_matches_claim=True,
            severity_estimate="medium",
            is_usable=True,
            confidence=0.9
        )
    ]
    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    output = adjudicate(evidence)
    
    assert output.claim_status == "supported"
    assert output.issue_type == "crack"
    assert output.object_part == "screen"
    assert output.severity == "medium"
    assert output.evidence_standard_met == "true"
    assert output.supporting_image_ids == "img_1"

def test_adjudicate_authenticity():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg",
        user_claim="Laptop keyboard stain",
        claim_object="laptop"
    )
    parsed_claim = ParsedClaim(
        primary_object="laptop",
        primary_part="keyboard",
        issue_hypothesis="stain"
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=True,
            relevant_part_visible=True,
            is_usable=True,
            authenticity_concern=True, # Flagged as non-original / suspicious
            confidence=0.8
        )
    ]
    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    output = adjudicate(evidence)
    
    assert output.claim_status == "not_enough_information"
    assert output.valid_image == "false"
    assert "non_original_image" in output.risk_flags
    assert output.evidence_standard_met == "false"

def test_adjudicate_text_instruction():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg",
        user_claim="Laptop keyboard stain",
        claim_object="laptop"
    )
    # The claim text parser detected instruction-based manipulation
    parsed_claim = ParsedClaim(
        primary_object="laptop",
        primary_part="keyboard",
        issue_hypothesis="stain",
        has_instruction_text=True
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=True,
            relevant_part_visible=True,
            is_usable=True,
            confidence=0.8
        )
    ]
    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    output = adjudicate(evidence)
    
    assert "text_instruction_present" in output.risk_flags
    assert "manual_review_required" in output.risk_flags


def test_adjudicate_matching_closeup_with_conflicting_context_is_not_enough_information():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="img_1.jpg;img_2.jpg",
        user_claim="Front bumper scratch",
        claim_object="car"
    )
    parsed_claim = ParsedClaim(
        primary_object="car",
        primary_part="front_bumper",
        issue_hypothesis="scratch"
    )
    observations = [
        ImageObservation(
            image_id="img_1",
            object_visible=True,
            object_type_seen="car",
            relevant_part_visible=True,
            part_seen="front_bumper",
            issue_observed="scratch",
            issue_matches_claim=True,
            severity_estimate="low",
            is_usable=True,
            confidence=0.9
        ),
        ImageObservation(
            image_id="img_2",
            object_visible=True,
            object_type_seen="laptop",
            relevant_part_visible=False,
            part_seen="screen",
            issue_observed="crack",
            issue_matches_claim=False,
            severity_estimate="medium",
            is_usable=True,
            confidence=0.8
        ),
    ]

    evidence = aggregate_observations(claim_input, parsed_claim, observations)
    output = adjudicate(evidence)

    assert "wrong_object" in output.risk_flags
    assert output.claim_status == "not_enough_information"
    assert output.evidence_standard_met == "false"

def test_strategy_staged_run():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="dataset/images/sample/case_001/img_1.jpg",
        user_claim="Laptop keyboard stain",
        claim_object="laptop"
    )
    model = MockAdapter()
    
    # We can use a dummy/temporary Path for dataset_dir
    dataset_dir = Path(__file__).resolve().parent.parent.parent
    
    output = run_staged_pipeline(
        claim=claim_input,
        model=model,
        dataset_dir=dataset_dir
    )
    
    assert output.user_id == "user_123"
    assert output.claim_object == "laptop"
    assert output.claim_status in ("supported", "contradicted", "not_enough_information")

def test_strategy_escalation_run():
    claim_input = ClaimInput(
        user_id="user_123",
        image_paths="dataset/images/sample/case_001/img_1.jpg",
        user_claim="Laptop keyboard stain",
        claim_object="laptop"
    )
    # Both base and escalation models
    base_model = MockAdapter()
    escalation_model = MockAdapter()
    
    dataset_dir = Path(__file__).resolve().parent.parent.parent
    
    output = run_escalation_pipeline(
        claim=claim_input,
        model=base_model,
        escalation_model=escalation_model,
        dataset_dir=dataset_dir
    )
    
    assert output.user_id == "user_123"
    assert output.claim_object == "laptop"
