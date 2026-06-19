# Phase 2: Evaluation Harness And Error Analysis

## Goal

Build the measurement layer first so model and rule changes can be ranked by evidence instead of intuition.

## Agent Mission

Build the evaluation harness that becomes the source of truth for model, prompt, and rule comparisons.

## Why This Phase Exists

Without a trustworthy evaluator, later prompt or architecture changes will be random motion. This phase creates the scoreboard that decides what "better" means.

## Files To Read Before Starting

1. `problem_statement.md`
2. `dataset/sample_claims.csv`
3. `plans/phase-01-foundation.md`

## Files To Create Or Edit

1. `code/evaluation/main.py`
2. `code/evaluation/metrics.py`
3. `code/evaluation/reporting.py`
4. `code/evaluation/evaluation_report.md`
5. `code/tests/test_metrics.py`
6. `code/src/telemetry/experiments.py`

## Python Stack For This Phase

1. `python3`
2. `pytest`
3. optional `pandas`
4. `pydantic`

## Implementation Steps

1. Define the evaluation outputs:
   row exact match, per-field accuracy, `risk_flags` set score, `supporting_image_ids` set score, and slice metrics.
2. Add a runner that:
   reads predictions and gold labels from `dataset/sample_claims.csv`, then emits machine-readable metrics plus a human-readable summary.
3. Build an error report grouped by:
   `claim_object`, image count, `claim_status`, `risk_flags`, and evidence-sufficiency failures.
4. Add an experiment-record format that stores:
   strategy name, prompt version, model version, run timestamp, metrics, and notes.
5. Create a simple non-LLM baseline for calibration:
   deterministic placeholders or heuristics that exercise the evaluator end to end.
6. Generate the first evaluation report so later phases only replace the prediction source, not the measurement layer.
7. Add tests for set scoring, exact-match logic, and CSV-to-metrics wiring.
8. Add serialization tests that compare exact output strings for:
   booleans, `risk_flags`, and `supporting_image_ids`.

## Deliverables

1. Machine-readable metrics output.
2. Markdown evaluation summary.
3. Experiment registry format.
4. Baseline run artifact.

## Agent Notes

1. The evaluator must be independent of provider choice.
2. Slice analysis should at minimum include:
   `claim_object`, image-count bucket, multilingual rows, mismatch rows, and history-risk rows.
3. Keep row exact match as the headline score, but expose enough secondary metrics to debug real gains.
4. Evaluate both set quality and exact serialized CSV quality.
   The evaluator can use set metrics for diagnosis, but final output must match canonical strings.

## Verification Gate

Phase 2 is complete only if all of the following are true:

1. A single command can evaluate a predictions CSV against `dataset/sample_claims.csv`.
2. The evaluator emits both machine-readable results and a markdown summary.
3. The experiment registry stores comparable runs.
4. At least one baseline run exists and is recorded.

## Required Evidence To Capture

1. A baseline evaluation report.
2. A sample confusion or error breakdown per critical field.
3. Proof that metrics change when predictions are intentionally perturbed.

## Risks

1. Over-optimizing for one aggregate metric can hide regressions on `risk_flags` or image attribution.
2. Using only row exact match will make it too hard to learn from partial improvements.
3. Failing to persist experiment metadata will make later comparisons untrustworthy.

## Locked Defaults

1. Make row exact match the headline metric.
2. Include per-field accuracy and set scores for `risk_flags` and `supporting_image_ids` as secondary metrics.
3. Keep large experiment artifacts out of version control while storing small reports in the repo.
4. Use the canonical `risk_flags` order from `problem_statement.md`.
5. Treat `supporting_image_ids` as images supporting the final decision.
   Contradicted decisions may legitimately include image IDs.

## Slices

### Slice 2.1: Metric definitions

Scope:
implement exact-match, field-accuracy, and set-metric functions in `metrics.py`.

Verification:
unit tests cover metric behavior on small fixtures.

Must include:
exact string checks for `risk_flags`, `supporting_image_ids`, and lowercase boolean fields.

### Slice 2.2: Evaluation runner

Scope:
implement `code/evaluation/main.py` to compare a predictions CSV against `dataset/sample_claims.csv`.

Verification:
one command emits machine-readable metrics.

### Slice 2.3: Markdown reporting

Scope:
implement `reporting.py` and baseline `evaluation_report.md`.

Verification:
runner emits a readable markdown summary.

### Slice 2.4: Experiment registry

Scope:
implement `experiments.py` format and storage for run metadata.

Verification:
a baseline run is persisted with strategy name and metrics.

### Slice 2.5: Error slicing

Scope:
add grouped error reports by object type, image count, and key failure categories.

Verification:
report includes slice breakdowns and changed-metric proof on perturbed predictions.

## Phase Command Targets

1. Evaluate a predictions CSV against `dataset/sample_claims.csv`.
2. Produce a markdown report from the evaluation output.

Use venv command forms from `plan.md`, for example:

1. `.venv/bin/python code/evaluation/main.py --predictions <predictions.csv> --gold dataset/sample_claims.csv`
2. `.venv/bin/python -m pytest code/tests/test_metrics.py`

## Exit Criteria

Do not start Phase 3 until you can compare two prediction files and explain exactly why one is better.
