"""
Experiment registry for tracking runs, metrics, and prompt configurations.
Saves details to a JSON registry for comparison.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class ExperimentRun(BaseModel):
    """Represents a single evaluation run configuration and its metrics."""
    experiment_id: str = Field(description="Unique run ID, e.g. run_20260620_120000")
    strategy_name: str = Field(description="Name of the pipeline strategy, e.g. single_pass, staged")
    prompt_version: str = Field(description="Brief descriptor of the prompt version used")
    model_version: str = Field(description="Name/version of the LLM or adapter used")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metrics: dict[str, Any] = Field(description="Computed evaluation metrics (exact_match, set scores, etc.)")
    notes: str = Field(default="", description="Developer annotations for this run")


def save_experiment_run(run: ExperimentRun, registry_path: Path) -> None:
    """Append an experiment run to the registry JSON file."""
    runs = []
    if registry_path.exists() and registry_path.stat().st_size > 0:
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                runs = json.load(f)
        except Exception as e:
            # If JSON is corrupt, print warning and initialize a new list
            print(f"Warning: Failed to load existing experiment registry: {e}. Reinitializing.")
            runs = []
            
    runs.append(run.model_dump())
    
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2)
    print(f"Experiment run '{run.experiment_id}' recorded successfully in {registry_path}")


def load_experiment_history(registry_path: Path) -> list[dict[str, Any]]:
    """Load the list of all recorded experiments."""
    if not registry_path.exists():
        return []
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading experiment registry: {e}")
        return []
