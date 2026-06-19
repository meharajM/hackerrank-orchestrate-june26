"""
Tests for enums, schemas, validation, and serialization.
"""
from __future__ import annotations

import csv

import pytest
from pydantic import ValidationError

from src.schemas import (
    ClaimOutput,
    OUTPUT_COLUMNS,
    serialize_risk_flags,
    serialize_image_ids,
)
from src.csv_io import write_output


def test_valid_claim_output():
    """Verify that a fully valid output dict can be instantiated."""
    out = ClaimOutput(
        user_id="user_001",
        image_paths="images/sample/case_001/img_1.jpg",
        user_claim="My car bumper is dented.",
        claim_object="car",
        evidence_standard_met="true",
        evidence_standard_met_reason="Bumper damage visible.",
        risk_flags="none",
        issue_type="dent",
        object_part="front_bumper",
        claim_status="supported",
        claim_status_justification="The front bumper has a clear dent.",
        supporting_image_ids="img_1",
        valid_image="true",
        severity="medium",
    )
    assert out.claim_status == "supported"
    assert out.issue_type == "dent"
    assert out.severity == "medium"
    assert out.evidence_standard_met == "true"
    assert out.valid_image == "true"
    assert out.risk_flags == "none"
    assert out.supporting_image_ids == "img_1"


def test_invalid_claim_status():
    """Verify that invalid claim_status raises ValidationError."""
    with pytest.raises(ValidationError):
        ClaimOutput(
            user_id="user_001",
            image_paths="images/sample/case_001/img_1.jpg",
            user_claim="My car bumper is dented.",
            claim_object="car",
            evidence_standard_met="true",
            evidence_standard_met_reason="Bumper damage visible.",
            risk_flags="none",
            issue_type="dent",
            object_part="front_bumper",
            claim_status="invalid_status_value",  # Invalid
            claim_status_justification="Explanation.",
            supporting_image_ids="img_1",
            valid_image="true",
            severity="medium",
        )


def test_invalid_issue_type():
    """Verify that invalid issue_type raises ValidationError."""
    with pytest.raises(ValidationError):
        ClaimOutput(
            user_id="user_001",
            image_paths="images/sample/case_001/img_1.jpg",
            user_claim="My car bumper is dented.",
            claim_object="car",
            evidence_standard_met="true",
            evidence_standard_met_reason="Bumper damage visible.",
            risk_flags="none",
            issue_type="exploded",  # Invalid
            object_part="front_bumper",
            claim_status="supported",
            claim_status_justification="Explanation.",
            supporting_image_ids="img_1",
            valid_image="true",
            severity="medium",
        )


def test_invalid_severity():
    """Verify that invalid severity raises ValidationError."""
    with pytest.raises(ValidationError):
        ClaimOutput(
            user_id="user_001",
            image_paths="images/sample/case_001/img_1.jpg",
            user_claim="My car bumper is dented.",
            claim_object="car",
            evidence_standard_met="true",
            evidence_standard_met_reason="Bumper damage visible.",
            risk_flags="none",
            issue_type="dent",
            object_part="front_bumper",
            claim_status="supported",
            claim_status_justification="Explanation.",
            supporting_image_ids="img_1",
            valid_image="true",
            severity="extreme",  # Invalid
        )


def test_invalid_bool_fields():
    """Verify that invalid boolean strings raise ValidationError."""
    with pytest.raises(ValidationError):
        ClaimOutput(
            user_id="user_001",
            image_paths="images/sample/case_001/img_1.jpg",
            user_claim="My car bumper is dented.",
            claim_object="car",
            evidence_standard_met="yes",  # Invalid - must be "true" or "false"
            evidence_standard_met_reason="Bumper damage visible.",
            risk_flags="none",
            issue_type="dent",
            object_part="front_bumper",
            claim_status="supported",
            claim_status_justification="Explanation.",
            supporting_image_ids="img_1",
            valid_image="true",
            severity="medium",
        )


def test_serialize_risk_flags():
    """Verify risk flags serialization and sorting."""
    # Empty / none
    assert serialize_risk_flags([]) == "none"
    assert serialize_risk_flags(["none"]) == "none"
    
    # Sorting and deduping
    # Order should be blurry_image, low_light_or_glare, user_history_risk (as per RISK_FLAG_ORDER)
    dirty = ["user_history_risk", "blurry_image", "blurry_image", "low_light_or_glare"]
    serialized = serialize_risk_flags(dirty)
    assert serialized == "blurry_image;low_light_or_glare;user_history_risk"


def test_serialize_image_ids():
    """Verify image IDs serialization and cleaning."""
    assert serialize_image_ids([]) == "none"
    assert serialize_image_ids(["none"]) == "none"
    
    # Clean extensions, deduplicate, and sort deterministically
    dirty = ["img_10.jpg", "img_2.png", "img_1.jpeg", "none"]
    serialized = serialize_image_ids(dirty)
    assert serialized == "img_1;img_2;img_10"


def test_invalid_risk_flags():
    """Verify invalid risk flags raise ValidationError."""
    with pytest.raises(ValidationError):
        ClaimOutput(
            user_id="user_001",
            image_paths="images/sample/case_001/img_1.jpg",
            user_claim="My car bumper is dented.",
            claim_object="car",
            evidence_standard_met="true",
            evidence_standard_met_reason="Bumper damage visible.",
            risk_flags="not_a_real_flag",
            issue_type="dent",
            object_part="front_bumper",
            claim_status="supported",
            claim_status_justification="Explanation.",
            supporting_image_ids="img_1",
            valid_image="true",
            severity="medium",
        )


def test_invalid_object_part_for_claim_object():
    """Verify object_part must match the claim_object enum family."""
    with pytest.raises(ValidationError):
        ClaimOutput(
            user_id="user_001",
            image_paths="images/sample/case_001/img_1.jpg",
            user_claim="My car bumper is dented.",
            claim_object="car",
            evidence_standard_met="true",
            evidence_standard_met_reason="Bumper damage visible.",
            risk_flags="none",
            issue_type="dent",
            object_part="screen",
            claim_status="supported",
            claim_status_justification="Explanation.",
            supporting_image_ids="img_1",
            valid_image="true",
            severity="medium",
        )


def test_claim_output_normalizes_serialized_fields():
    """Verify serialized output fields are normalized deterministically."""
    out = ClaimOutput(
        user_id="user_001",
        image_paths="images/sample/case_001/img_1.jpg",
        user_claim="My car bumper is dented.",
        claim_object="car",
        evidence_standard_met="TRUE",
        evidence_standard_met_reason="Bumper damage visible.",
        risk_flags="user_history_risk;blurry_image;user_history_risk",
        issue_type="dent",
        object_part="Front Bumper",
        claim_status="supported",
        claim_status_justification="Explanation.",
        supporting_image_ids="img_10.jpg;img_2.png;img_1.jpeg",
        valid_image="FALSE",
        severity="medium",
    )
    assert out.evidence_standard_met == "true"
    assert out.valid_image == "false"
    assert out.risk_flags == "blurry_image;user_history_risk"
    assert out.object_part == "front_bumper"
    assert out.supporting_image_ids == "img_1;img_2;img_10"


def test_write_output_uses_exact_column_order(tmp_path):
    """Verify output CSV header matches the problem statement exactly."""
    output_path = tmp_path / "output.csv"
    row = ClaimOutput(
        user_id="user_001",
        image_paths="images/sample/case_001/img_1.jpg",
        user_claim="My car bumper is dented.",
        claim_object="car",
        evidence_standard_met="true",
        evidence_standard_met_reason="Bumper damage visible.",
        risk_flags="none",
        issue_type="dent",
        object_part="front_bumper",
        claim_status="supported",
        claim_status_justification="Explanation.",
        supporting_image_ids="img_1",
        valid_image="true",
        severity="medium",
    )

    write_output([row], output_path)

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)

    assert header == OUTPUT_COLUMNS
