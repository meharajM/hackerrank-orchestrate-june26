"""
Smoke test to execute Stage 1 & Stage 2 pipeline components and dump intermediate JSONs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from src.config import get_config
    from src.csv_io import read_claims
    from src.models import GeminiAdapter, MockAdapter, OllamaAdapter, OpenAICompatibleAdapter
    from src.pipeline.claim_parser import parse_claim
    from src.pipeline.image_reviewer import review_image
    from src.pipeline.aggregation import aggregate_observations
    from src.pipeline.adjudication import adjudicate
    from src.image_io import resolve_all_image_paths
    from src.history import FileHistoryRepository
    from src.requirements import FileRequirementsRepository
except ImportError:
    # Standalone-script fallback for `python code/src/pipeline/smoke_evidence.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.config import get_config
    from src.csv_io import read_claims
    from src.models import GeminiAdapter, MockAdapter, OllamaAdapter, OpenAICompatibleAdapter
    from src.pipeline.claim_parser import parse_claim
    from src.pipeline.image_reviewer import review_image
    from src.pipeline.aggregation import aggregate_observations
    from src.pipeline.adjudication import adjudicate
    from src.image_io import resolve_all_image_paths
    from src.history import FileHistoryRepository
    from src.requirements import FileRequirementsRepository


def run_smoke(
    *,
    adapter_name: str,
    dataset_path: Path | None = None,
    limit: int = 3,
    output_dir: Path | None = None,
) -> None:
    config = get_config()
    claims_path = dataset_path or config.sample_claims_csv
    print("Loading config...", flush=True)
    print(f"Dataset directory: {config.dataset_dir}", flush=True)
    print(f"Claims CSV: {claims_path}", flush=True)

    # Read claims
    claims = read_claims(claims_path)
    print(f"Loaded {len(claims)} claims.", flush=True)

    # Build adapters
    base_model, stage2_model = _build_models(adapter_name, config)
    print(f"Using base model: {base_model.name}", flush=True)
    print(f"Using stage 2 model: {stage2_model.name}", flush=True)

    history_repository = FileHistoryRepository(config.user_history_csv)
    requirements_repository = FileRequirementsRepository(config.evidence_requirements_csv)

    # Create output directory for intermediate results
    output_dir = output_dir or config.repo_root / "code" / "evaluation" / "sample_intermediate"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Intermediate outputs will be saved to: {output_dir}", flush=True)

    test_claims = claims[:limit]

    for idx, claim in enumerate(test_claims, 1):
        print(f"\n--- Claim {idx}: User {claim.user_id} ({claim.claim_object}) ---", flush=True)
        print(f"User claim text: {claim.user_claim}", flush=True)

        user_history = history_repository.get_user_history(claim.user_id)
        requirements = requirements_repository.get_requirements_for_claim(claim.claim_object)

        # Run Stage 1 parsing
        parsed = parse_claim(claim, base_model)
        print("Stage 1 Parsed Claim Result:", flush=True)
        print(json.dumps(parsed.model_dump(), indent=2), flush=True)

        # Resolve image paths
        image_info = resolve_all_image_paths(claim.image_paths, config.dataset_dir)

        observations = []
        for img_id, img_path, exists in image_info:
            print(f"Reviewing image: {img_id} (exists: {exists})", flush=True)
            obs = review_image(img_path, parsed, stage2_model)
            observations.append(obs)
            print(
                f"  Observed part: {obs.part_seen}, issue: {obs.issue_observed}, matches: {obs.issue_matches_claim}",
                flush=True,
            )

        evidence = aggregate_observations(
            claim_input=claim,
            parsed_claim=parsed,
            observations=observations,
            user_history=user_history,
            evidence_requirements=requirements,
        )
        output = adjudicate(evidence)

        # Save holistic intermediate dump for this claim
        dump_data = {
            "claim": {
                "user_id": claim.user_id,
                "claim_object": claim.claim_object,
                "user_claim": claim.user_claim,
                "image_paths": claim.image_paths,
            },
            "stage_1_parsed_claim": parsed.model_dump(),
            "stage_2_observations": [obs.model_dump() for obs in observations],
            "aggregated_evidence": evidence.model_dump(),
            "provisional_output": output.to_row_dict(),
        }

        dump_path = output_dir / f"claim_{idx:03d}_{claim.user_id}.json"
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)
        print(f"Saved intermediate dump to: {dump_path}", flush=True)

    print("\nSmoke run completed successfully.", flush=True)


def _build_models(adapter_name: str, config):
    if adapter_name == "mock":
        model = MockAdapter()
        return model, model

    if adapter_name == "ollama":
        base_model = OllamaAdapter(
            model_name=config.ollama_model,
            base_url=config.ollama_base_url,
        )
        stage2_name = config.ollama_stage2_model or config.ollama_model
        stage2_model = OllamaAdapter(
            model_name=stage2_name,
            base_url=config.ollama_base_url,
        )
        return base_model, stage2_model

    if adapter_name == "openai_compat":
        base_model = OpenAICompatibleAdapter(
            model_name=config.openai_compatible_model,
            base_url=config.openai_compatible_base_url,
            api_key=config.openai_compatible_api_key,
        )
        stage2_name = config.openai_compatible_stage2_model or config.openai_compatible_model
        stage2_model = OpenAICompatibleAdapter(
            model_name=stage2_name,
            base_url=config.openai_compatible_base_url,
            api_key=config.openai_compatible_api_key,
        )
        return base_model, stage2_model

    if not config.has_gemini:
        raise SystemExit("GEMINI_API_KEY is required for gemini smoke runs.")
    model = GeminiAdapter(model_name=config.gemini_model)
    return model, model


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1/2 smoke harness with intermediate dumps.")
    parser.add_argument("--model", choices=["mock", "ollama", "openai_compat", "gemini"], default="mock")
    parser.add_argument("--claims", type=Path, help="CSV path to inspect. Defaults to dataset/sample_claims.csv")
    parser.add_argument("--limit", type=int, default=3, help="Number of claims to inspect.")
    parser.add_argument("--output-dir", type=Path, help="Directory for intermediate JSON outputs.")
    args = parser.parse_args()
    run_smoke(
        adapter_name=args.model,
        dataset_path=args.claims,
        limit=args.limit,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
