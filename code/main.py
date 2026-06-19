#!/usr/bin/env python3
"""
Main entry point for the HackerRank Orchestrate Claims Verification system.
Loads input files, runs the evidence review pipeline, and writes schema-valid output.csv.

Features:
  - Resumable: skips rows already present in the output CSV (by full claim identity).
  - Cached: wires a content-addressed ResponseCache into the model adapter.
  - Telemetry: logs per-call events and estimated cost to JSON.
  - Strategies A/B/C with --strategy flag.
"""
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Mapping

from src.claim_processing import build_claim_processing_context, process_claim
from src.config import get_config
from src.csv_io import read_claims
from src.schemas import OUTPUT_COLUMNS


def _claim_identity(row: Mapping[str, str]) -> str:
    """Return a deterministic identity for an input or output row."""
    return "||".join(
        [
            row.get("user_id", "").strip(),
            row.get("claim_object", "").strip().lower(),
            row.get("image_paths", "").strip(),
            row.get("user_claim", "").strip(),
        ]
    )


def _load_completed_claim_keys(output_path: Path) -> set[str]:
    """Read existing output CSV and return the set of processed claim identities."""
    completed: set[str] = set()
    if output_path.exists() and output_path.stat().st_size > 0:
        try:
            with open(output_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    claim_key = _claim_identity(row)
                    if claim_key.strip("|"):
                        completed.add(claim_key)
        except Exception as e:
            print(f"Warning: could not read existing output for resume: {e}")
    return completed


def _append_row(output_path: Path, row_dict: dict) -> None:
    """Append a single row to the output CSV, writing header if file is empty/new."""
    write_header = not output_path.exists() or output_path.stat().st_size == 0
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_ALL)
        if write_header:
            writer.writeheader()
        writer.writerow(row_dict)
def main():
    parser = argparse.ArgumentParser(description="Multi-Modal Evidence Review System")
    parser.add_argument(
        "--input",
        type=str,
        help="Path to input claims CSV file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save output predictions CSV file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mock",
        choices=["gemini", "ollama", "mock"],
        help="Model adapter to use (gemini, ollama, or mock)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="B",
        choices=["A", "B", "C"],
        help="Pipeline strategy to use (A: holistic, B: staged pipeline, C: conditional escalation)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force fresh run: overwrite existing output file instead of resuming.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the response cache.",
    )
    args = parser.parse_args()

    # Load configuration
    config = get_config()

    # Resolve paths
    input_path = Path(args.input) if args.input else config.claims_csv
    output_path = Path(args.output) if args.output else config.output_csv

    print(f"Loading claims from: {input_path}")
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist.")
        sys.exit(1)

    # Read claims
    claims = read_claims(input_path)
    print(f"Loaded {len(claims)} claims.")

    # ── Checkpoint resumption ────────────────────────────────────────────
    if args.force and output_path.exists():
        output_path.unlink()
        print("Forced fresh run: existing output cleared.")

    completed_claim_keys = _load_completed_claim_keys(output_path)
    if completed_claim_keys:
        print(f"Resuming: {len(completed_claim_keys)} claims already processed. Skipping them.")
    remaining_claims = [
        c for c in claims
        if _claim_identity(
            {
                "user_id": c.user_id,
                "claim_object": c.claim_object,
                "image_paths": c.image_paths,
                "user_claim": c.user_claim,
            }
        ) not in completed_claim_keys
    ]

    if not remaining_claims:
        print("All claims already processed. Use --force to re-run from scratch.")
        return

    context = build_claim_processing_context(
        config=config,
        model_name=args.model,
        strategy=args.strategy,
        cache_enabled=not args.no_cache,
    )
    if not args.no_cache:
        print(f"Response cache enabled: {context.cache.cache_dir}")
    if args.model == "gemini" and not config.has_gemini:
        print("Warning: GEMINI_API_KEY environment variable is not set. Falling back to MockAdapter.")
    if args.strategy == "C" and not config.has_gemini:
        print("Warning: GEMINI_API_KEY is not set. Strategy C escalation will fallback to the base model.")

    print(f"Using model adapter: {context.model.name} with strategy: {args.strategy}")

    # ── Process claims ───────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(remaining_claims)
    run_start = time.monotonic()

    for i, claim in enumerate(remaining_claims, 1):
        print(f"[{i}/{total}] Processing claim for user: {claim.user_id}")
        result = process_claim(claim, context)
        _append_row(output_path, result.output.to_row_dict())

    # ── Post-run reporting ───────────────────────────────────────────────
    total_time = round(time.monotonic() - run_start, 2)
    print(f"\n{'='*60}")
    print(f"Run complete: {total} claims processed in {total_time}s")
    print(f"Output written to: {output_path}")

    # Telemetry summary
    tel = context.event_logger.summary()
    c_sum = context.cost_tracker.summary()
    print(f"  Events: {tel['total_events']}  |  Latency: {tel['total_latency_seconds']}s")
    print(f"  Estimated Cost: ${c_sum['estimated_cost_usd']:.6f} USD")
    if not args.no_cache:
        cs = context.cache.summary()
        print(f"  Cache: {cs['hits']} hits / {cs['misses']} misses  ({cs['hit_rate']*100:.1f}% hit rate)")

    # Flush telemetry log
    tel_path = output_path.parent / "telemetry_log.json"
    context.event_logger.flush(tel_path)
    print(f"  Telemetry log: {tel_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
