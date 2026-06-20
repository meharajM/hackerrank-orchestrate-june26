import csv

from src import BatchRunRequest, build_claim_processing_context, run_batch
from src.config import get_config
from src.schemas import OUTPUT_COLUMNS


def test_run_batch_writes_contract_valid_output(tmp_path):
    """Batch runner should process sample claims into contract-valid CSV output."""
    config = get_config()
    output_path = tmp_path / "output.csv"
    telemetry_log_path = tmp_path / "telemetry.json"
    context = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=False,
    )

    result = run_batch(
        BatchRunRequest(
            input_path=config.sample_claims_csv,
            output_path=output_path,
            force=True,
            resume=False,
            telemetry_log_path=telemetry_log_path,
        ),
        context,
    )

    assert result.total_claims == 20
    assert result.processed_claims == 20
    assert result.skipped_claims == 0
    assert output_path.exists()
    assert telemetry_log_path.exists()

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == OUTPUT_COLUMNS
    assert len(rows) == 20
    assert rows[0]["user_id"]


def test_run_batch_resume_skips_previously_written_rows(tmp_path):
    """Batch runner should skip rows already present in the target output when resuming."""
    config = get_config()
    output_path = tmp_path / "resume_output.csv"

    context_first = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=False,
    )
    first_result = run_batch(
        BatchRunRequest(
            input_path=config.sample_claims_csv,
            output_path=output_path,
            force=True,
            resume=False,
        ),
        context_first,
    )
    assert first_result.processed_claims == 20

    context_second = build_claim_processing_context(
        config=config,
        model_name="mock",
        strategy="B",
        cache_enabled=False,
    )
    second_result = run_batch(
        BatchRunRequest(
            input_path=config.sample_claims_csv,
            output_path=output_path,
            force=False,
            resume=True,
        ),
        context_second,
    )

    assert second_result.processed_claims == 0
    assert second_result.skipped_claims == 20
