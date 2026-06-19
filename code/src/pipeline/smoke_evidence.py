"""
Smoke test to execute Stage 1 & Stage 2 pipeline components and dump intermediate JSONs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from src.config import get_config
    from src.csv_io import read_claims
    from src.models.mock_adapter import MockAdapter
    from src.pipeline.claim_parser import parse_claim
    from src.pipeline.image_reviewer import review_image
    from src.image_io import resolve_all_image_paths
except ImportError:
    # Standalone-script fallback for `python code/src/pipeline/smoke_evidence.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.config import get_config
    from src.csv_io import read_claims
    from src.models.mock_adapter import MockAdapter
    from src.pipeline.claim_parser import parse_claim
    from src.pipeline.image_reviewer import review_image
    from src.image_io import resolve_all_image_paths


def run_smoke():
    config = get_config()
    print("Loading config...")
    print(f"Dataset directory: {config.dataset_dir}")
    print(f"Sample claims: {config.sample_claims_csv}")

    # Read claims
    claims = read_claims(config.sample_claims_csv)
    print(f"Loaded {len(claims)} sample claims.")

    # Use mock model adapter
    model = MockAdapter()
    print(f"Using model: {model.name}")

    # Create output directory for intermediate results
    output_dir = config.repo_root / "code" / "evaluation" / "sample_intermediate"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Intermediate outputs will be saved to: {output_dir}")

    # Take first 3 claims for smoke testing (representing car, laptop, package)
    test_claims = claims[:3]

    for idx, claim in enumerate(test_claims, 1):
        print(f"\n--- Claim {idx}: User {claim.user_id} ({claim.claim_object}) ---")
        print(f"User claim text: {claim.user_claim}")
        
        # Run Stage 1 parsing
        parsed = parse_claim(claim, model)
        print("Stage 1 Parsed Claim Result:")
        print(json.dumps(parsed.model_dump(), indent=2))

        # Resolve image paths
        image_info = resolve_all_image_paths(claim.image_paths, config.dataset_dir)
        
        observations = []
        for img_id, img_path, exists in image_info:
            print(f"Reviewing image: {img_id} (exists: {exists})")
            obs = review_image(img_path, parsed, model)
            observations.append(obs)
            print(f"  Observed part: {obs.part_seen}, issue: {obs.issue_observed}, matches: {obs.issue_matches_claim}")
        
        # Save holistic intermediate dump for this claim
        dump_data = {
            "claim": {
                "user_id": claim.user_id,
                "claim_object": claim.claim_object,
                "user_claim": claim.user_claim,
                "image_paths": claim.image_paths,
            },
            "stage_1_parsed_claim": parsed.model_dump(),
            "stage_2_observations": [obs.model_dump() for obs in observations]
        }
        
        dump_path = output_dir / f"claim_{claim.user_id}.json"
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)
        print(f"Saved intermediate dump to: {dump_path}")

    print("\nSmoke run completed successfully.")


if __name__ == "__main__":
    run_smoke()
