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
from pathlib import Path

from src import BatchRunRequest, build_claim_processing_context, run_batch
from src.config import get_config


def _describe_context_models(context) -> str:
    label = context.model.name
    if context.stage2_model is not None and context.stage2_model is not context.model:
        label = f"{label}; stage2={context.stage2_model.name}"
    if context.escalation_model is not None and context.escalation_model not in {context.model, context.stage2_model}:
        label = f"{label}; escalation={context.escalation_model.name}"
    return label


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
        choices=["gemini", "ollama", "openai_compat", "mock"],
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

    if not input_path.exists():
        raise SystemExit(f"Error: Input file {input_path} does not exist.")

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

    print(f"Using model adapter(s): {_describe_context_models(context)} with strategy: {args.strategy}")
    result = run_batch(
        BatchRunRequest(
            input_path=input_path,
            output_path=output_path,
            force=args.force,
            resume=not args.force,
        ),
        context,
    )

    print(f"\n{'='*60}")
    print(
        f"Run complete: {result.processed_claims} claims processed"
        f" ({result.skipped_claims} skipped, {result.total_claims} total)"
        f" in {result.total_time_seconds}s"
    )
    print(f"Output written to: {result.output_path}")
    if result.telemetry_summary:
        print(
            f"  Events: {result.telemetry_summary['total_events']}  |  "
            f"Latency: {result.telemetry_summary['total_latency_seconds']}s"
        )
    if result.cost_summary:
        print(f"  Estimated Cost: ${result.cost_summary['estimated_cost_usd']:.6f} USD")
    if not args.no_cache and result.cache_summary is not None:
        print(
            f"  Cache: {result.cache_summary['hits']} hits / {result.cache_summary['misses']} misses  "
            f"({result.cache_summary['hit_rate']*100:.1f}% hit rate)"
        )
    if result.telemetry_log_path is not None:
        print(f"  Telemetry log: {result.telemetry_log_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
