#!/usr/bin/env python3
"""
Evaluation runner for HackerRank Orchestrate claims verification system.
Compares predictions against gold labels in dataset/sample_claims.csv
and generates markdown and JSON reports.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    from src import build_claim_processing_context, process_claim
    from src.csv_io import read_claims, read_claims_with_labels
    from src.telemetry.experiments import ExperimentRun, save_experiment_run
    from evaluation.metrics import evaluate_predictions
    from evaluation.reporting import generate_slice_metrics, build_markdown_report
except ImportError:
    # Standalone-script fallback for `python code/evaluation/main.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src import build_claim_processing_context, process_claim
    from src.csv_io import read_claims, read_claims_with_labels
    from src.telemetry.experiments import ExperimentRun, save_experiment_run
    from evaluation.metrics import evaluate_predictions
    from evaluation.reporting import generate_slice_metrics, build_markdown_report


def main():
    parser = argparse.ArgumentParser(description="HackerRank Orchestrate Evaluation Runner")
    parser.add_argument(
        "--predictions",
        type=str,
        help="Path to predictions CSV file to evaluate. If omitted and --model is provided, will run pipeline dynamically.",
    )
    parser.add_argument(
        "--gold",
        type=str,
        default="dataset/sample_claims.csv",
        help="Path to the gold labels CSV file (default: dataset/sample_claims.csv)",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="code/evaluation/evaluation_report.md",
        help="Path to save the generated markdown report (default: code/evaluation/evaluation_report.md)",
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["gemini", "ollama", "mock"],
        help="Optionally run the pipeline dynamically on gold rows with the specified model adapter.",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="B",
        choices=["A", "B", "C"],
        help="Pipeline strategy to use for dynamic run (A: holistic, B: staged pipeline, C: conditional escalation)",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default="",
        help="Optional notes to record in the experiment registry.",
    )
    parser.add_argument(
        "--registry",
        type=str,
        default="code/evaluation/experiments.json",
        help="Path to the experiment registry JSON file (default: code/evaluation/experiments.json)",
    )
    parser.add_argument(
        "--metrics-json",
        type=str,
        default="code/evaluation/metrics.json",
        help="Path to save computed metrics in JSON format (default: code/evaluation/metrics.json)",
    )

    args = parser.parse_args()

    gold_path = Path(args.gold)
    report_path = Path(args.report)
    registry_path = Path(args.registry)
    metrics_json_path = Path(args.metrics_json)

    if not gold_path.exists():
        print(f"Error: Gold labels file {gold_path} does not exist.")
        sys.exit(1)

    print(f"Loading gold labels from: {gold_path}")
    gold_rows = read_claims_with_labels(gold_path)
    print(f"Loaded {len(gold_rows)} gold rows.")

    pred_rows = []
    strategy_name = "unknown"
    model_version = "unknown"

    if args.predictions:
        pred_path = Path(args.predictions)
        if not pred_path.exists():
            print(f"Error: Predictions file {pred_path} does not exist.")
            sys.exit(1)
        print(f"Loading predictions from: {pred_path}")
        pred_rows = read_claims_with_labels(pred_path)
        strategy_name = "csv_import"
        model_version = pred_path.name
    elif args.model:
        # Run pipeline dynamically on gold rows
        from src.config import get_config
        config = get_config()
        claims = read_claims(gold_path)
        if args.model == "gemini" and not config.has_gemini:
            print("Error: GEMINI_API_KEY environment variable is not set. Cannot run dynamic Gemini review.")
            sys.exit(1)

        context = build_claim_processing_context(
            config=config,
            model_name=args.model,
            strategy=args.strategy,
            cache_enabled=False,
            allow_model_fallback=False,
        )

        strategy_name = f"dynamic_run_strategy_{args.strategy}"
        model_version = context.model.name

        print(f"Running pipeline dynamically with strategy {args.strategy} and model: {context.model.name}...")
        pred_outputs = []
        for i, claim in enumerate(claims, 1):
            print(f"[{i}/{len(claims)}] Processing: {claim.user_id} - {claim.claim_object}")
            pred_outputs.append(process_claim(claim, context).output)

        pred_rows = [p.to_row_dict() for p in pred_outputs]
    else:
        print("Error: Must specify either --predictions or --model.")
        parser.print_help()
        sys.exit(1)

    print(f"Evaluating {len(pred_rows)} predictions against gold labels...")
    try:
        results = evaluate_predictions(gold_rows, pred_rows)
    except Exception as e:
        print(f"Error during metrics evaluation: {e}")
        sys.exit(1)

    # Compute logical slices
    print("Computing slice metrics...")
    slice_metrics = generate_slice_metrics(results)

    # Build markdown report
    print("Generating evaluation report...")
    report_content = build_markdown_report(
        results=results,
        slice_metrics=slice_metrics,
        strategy_name=strategy_name,
        model_version=model_version,
        notes=args.notes,
    )

    # Write report and metrics files
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Evaluation report saved to: {report_path}")

    # Save JSON metrics file
    import json
    metrics_summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "exact_match_rate": results["exact_match_rate"],
        "exact_matches": results["exact_matches"],
        "total_evaluated": results["total_evaluated"],
        "field_accuracies": results["field_accuracies"],
        "risk_flags_metrics": results["risk_flags_metrics"],
        "supporting_image_ids_metrics": results["supporting_image_ids_metrics"],
    }
    metrics_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"JSON metrics saved to: {metrics_json_path}")

    # Record experiment run
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"run_{timestamp_str}"
    
    experiment_run = ExperimentRun(
        experiment_id=experiment_id,
        strategy_name=strategy_name,
        prompt_version="baseline",
        model_version=model_version,
        metrics=metrics_summary,
        notes=args.notes or f"Generated via evaluation runner on {gold_path.name}",
    )
    save_experiment_run(experiment_run, registry_path)


if __name__ == "__main__":
    main()
