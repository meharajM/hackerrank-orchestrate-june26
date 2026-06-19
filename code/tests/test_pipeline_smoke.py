"""
Smoke tests for the full pipeline run and path resolutions.
"""
from __future__ import annotations

import csv

from src.config import get_config
from src.csv_io import read_claims, write_output
from src.image_io import resolve_all_image_paths
from src.models import MockAdapter
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
