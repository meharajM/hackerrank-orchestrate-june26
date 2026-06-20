"""
Smoke tests for the full pipeline run and path resolutions.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.batch_runner import claim_identity, load_completed_claim_keys
from src.config import get_config
from src.csv_io import read_claims, write_output
from src.image_io import resolve_all_image_paths
from src.models import MockAdapter
from src.pipeline.smoke_evidence import run_smoke
from src.pipeline.reviewer import review_claim
from src.schemas import OUTPUT_COLUMNS


def test_resolve_paths_for_all_rows():
    """Verify that all image paths resolve for sample and test claim files."""
    config = get_config()
    for csv_path in (config.sample_claims_csv, config.claims_csv):
        claims = read_claims(csv_path)
        assert len(claims) > 0
        for claim in claims:
            image_info = resolve_all_image_paths(claim.image_paths, config.dataset_dir)
            assert len(image_info) > 0
            for img_id, path, exists in image_info:
                assert img_id != ""
                assert path.is_absolute()
                assert "images" in path.parts
                assert exists, f"Missing image for claim {claim.user_id}: {path}"


def test_mock_pipeline_run():
    """Verify the pipeline runs successfully end-to-end with MockAdapter."""
    config = get_config()
    claims = read_claims(config.sample_claims_csv)
    claim = claims[0]
    model = MockAdapter()
    
    output = review_claim(
        claim=claim,
        model=model,
        dataset_dir=config.dataset_dir,
    )
    
    # Assert output conforms to expected types and values
    assert output.user_id == claim.user_id
    assert output.claim_object == claim.claim_object
    assert output.evidence_standard_met in ("true", "false")
    assert output.valid_image in ("true", "false")
    assert output.supporting_image_ids != ""


def test_smoke_output_has_exact_columns(tmp_path):
    """Verify a written smoke output uses the exact required columns."""
    config = get_config()
    claims = read_claims(config.sample_claims_csv)
    model = MockAdapter()
    outputs = [
        review_claim(claim=claim, model=model, dataset_dir=config.dataset_dir)
        for claim in claims[:2]
    ]

    output_path = tmp_path / "smoke.csv"
    write_output(outputs, output_path)

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == OUTPUT_COLUMNS


def test_resume_identity_uses_full_claim_row_not_just_user_id(tmp_path):
    """Rows from repeated users in claims.csv must still be processed independently."""
    row_a = {
        "user_id": "user_045",
        "claim_object": "car",
        "image_paths": "images/test/case_045/img_1.jpg",
        "user_claim": "Rear bumper dent after parking impact.",
    }
    row_b = {
        "user_id": "user_045",
        "claim_object": "car",
        "image_paths": "images/test/case_046/img_1.jpg",
        "user_claim": "Front bumper scratch from another incident.",
    }

    output_path = tmp_path / "resume_output.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerow(
            {
                **row_a,
                "evidence_standard_met": "true",
                "evidence_standard_met_reason": "ok",
                "risk_flags": "none",
                "issue_type": "dent",
                "object_part": "rear_bumper",
                "claim_status": "supported",
                "claim_status_justification": "ok",
                "supporting_image_ids": "img_1",
                "valid_image": "true",
                "severity": "low",
            }
        )

    completed = load_completed_claim_keys(output_path)
    assert claim_identity(row_a) in completed
    assert claim_identity(row_b) not in completed


def test_stage2_harness_dumps_do_not_overwrite_repeated_users(tmp_path):
    run_smoke(adapter_name="mock", limit=5, output_dir=tmp_path)

    dumped = sorted(tmp_path.glob("claim_*.json"))
    assert len(dumped) == 5
    assert len({path.name for path in dumped}) == 5

    payload = json.loads(dumped[0].read_text(encoding="utf-8"))
    assert "stage_2_observations" in payload
