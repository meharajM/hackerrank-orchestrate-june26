#!/usr/bin/env python3
"""
Main entry point for the HackerRank Orchestrate Claims Verification system.
Loads input files, runs the evidence review pipeline, and writes schema-valid output.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add the parent directory of code/src to the python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import get_config
from src.csv_io import read_claims, write_output
from src.history import HistoryManager
from src.requirements import RequirementsManager
from src.models import GeminiAdapter, MockAdapter
from src.pipeline.reviewer import review_claim


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
        choices=["gemini", "mock"],
        help="Model adapter to use (gemini or mock)",
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

    # Load history and requirements
    history_manager = HistoryManager(config.user_history_csv)
    requirements_manager = RequirementsManager(config.evidence_requirements_csv)

    # Initialize model adapter
    if args.model == "gemini":
        if not config.has_gemini:
            print("Warning: GEMINI_API_KEY environment variable is not set. Falling back to MockAdapter.")
            model = MockAdapter()
        else:
            model = GeminiAdapter(model_name=config.gemini_model)
    else:
        model = MockAdapter()

    print(f"Using model adapter: {model.name}")

    # Process all claims
    output_rows = []
    for i, claim in enumerate(claims, 1):
        print(f"[{i}/{len(claims)}] Processing claim for user: {claim.user_id}")
        
        # Look up history
        user_history = history_manager.get_user_history(claim.user_id)
        
        # Look up relevant requirements
        reqs = requirements_manager.get_requirements_for_claim(claim.claim_object)

        # Run review
        output = review_claim(
            claim=claim,
            model=model,
            dataset_dir=config.dataset_dir,
            user_history=user_history,
            evidence_requirements=reqs,
        )
        output_rows.append(output)

    # Write output
    print(f"Writing {len(output_rows)} predictions to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_output(output_rows, output_path)
    print("Done.")


if __name__ == "__main__":
    main()
