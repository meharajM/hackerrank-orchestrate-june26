"""
Importable batch orchestration for claim processing.
Keeps CLI, jobs, and future hosted transports on the same execution path.
"""
from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from .claim_processing import ClaimProcessingContext, process_claim_batch
from .csv_io import read_claims
from .schemas import OUTPUT_COLUMNS


@dataclass(frozen=True)
class BatchRunRequest:
    """Input contract for batch claim execution."""

    input_path: Path
    output_path: Path
    force: bool = False
    resume: bool = True
    telemetry_log_path: Optional[Path] = None


@dataclass
class BatchRunResult:
    """Summary of a completed batch run."""

    input_path: Path
    output_path: Path
    total_claims: int
    processed_claims: int
    skipped_claims: int
    total_time_seconds: float
    telemetry_summary: dict
    cost_summary: dict
    cache_summary: Optional[dict]
    telemetry_log_path: Optional[Path]


def claim_identity(row: Mapping[str, str]) -> str:
    """Return a deterministic identity for an input or output row."""
    return "||".join(
        [
            row.get("user_id", "").strip(),
            row.get("claim_object", "").strip().lower(),
            row.get("image_paths", "").strip(),
            row.get("user_claim", "").strip(),
        ]
    )


def load_completed_claim_keys(output_path: Path) -> set[str]:
    """Read an existing output CSV and return processed claim identities."""
    completed: set[str] = set()
    if output_path.exists() and output_path.stat().st_size > 0:
        try:
            with open(output_path, "r", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    row_key = claim_identity(row)
                    if row_key.strip("|"):
                        completed.add(row_key)
        except Exception:
            # Resume is best-effort; the CLI prints errors separately if needed.
            return completed
    return completed


def append_output_row(output_path: Path, row_dict: dict) -> None:
    """Append a single row to the output CSV, creating the header if needed."""
    write_header = not output_path.exists() or output_path.stat().st_size == 0
    with open(output_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_ALL)
        if write_header:
            writer.writeheader()
        writer.writerow(row_dict)


def run_batch(request: BatchRunRequest, context: ClaimProcessingContext) -> BatchRunResult:
    """Run a batch of claims from CSV input to CSV output through a shared context."""
    claims = read_claims(request.input_path)

    if request.force and request.output_path.exists():
        request.output_path.unlink()

    completed_claim_keys: set[str] = set()
    if request.resume and not request.force:
        completed_claim_keys = load_completed_claim_keys(request.output_path)

    remaining_claims = [
        claim
        for claim in claims
        if claim_identity(
            {
                "user_id": claim.user_id,
                "claim_object": claim.claim_object,
                "image_paths": claim.image_paths,
                "user_claim": claim.user_claim,
            }
        )
        not in completed_claim_keys
    ]

    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    run_start = time.monotonic()

    for result in process_claim_batch(remaining_claims, context):
        append_output_row(request.output_path, result.output.to_row_dict())

    total_time = round(time.monotonic() - run_start, 2)
    telemetry_summary = context.event_logger.summary() if context.event_logger else {}
    cost_summary = context.cost_tracker.summary() if context.cost_tracker else {}
    cache_summary = context.cache.summary() if context.cache else None

    telemetry_log_path = request.telemetry_log_path
    if telemetry_log_path is None and context.event_logger is not None:
        telemetry_log_path = request.output_path.parent / "telemetry_log.json"
    if telemetry_log_path is not None and context.event_logger is not None:
        context.event_logger.flush(telemetry_log_path)

    return BatchRunResult(
        input_path=request.input_path,
        output_path=request.output_path,
        total_claims=len(claims),
        processed_claims=len(remaining_claims),
        skipped_claims=len(completed_claim_keys),
        total_time_seconds=total_time,
        telemetry_summary=telemetry_summary,
        cost_summary=cost_summary,
        cache_summary=cache_summary,
        telemetry_log_path=telemetry_log_path,
    )


__all__ = [
    "BatchRunRequest",
    "BatchRunResult",
    "append_output_row",
    "claim_identity",
    "load_completed_claim_keys",
    "run_batch",
]
