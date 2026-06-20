# Phase 6: Finalization, Freeze, And Submission Readiness

## Goal

Freeze the best system, generate final artifacts, and make the repo submission-ready without last-minute ambiguity.

## Agent Mission

Finalize the chosen strategy, produce submission-grade artifacts, and leave a reproducible operator path for future reruns.

## Why This Phase Exists

High-quality experimentation is wasted if the final artifacts are inconsistent, undocumented, or non-reproducible.

## Files To Read Before Starting

1. `README.md`
2. `problem_statement.md`
3. `plans/phase-05-scale-and-optimization.md`
4. `code/evaluation/evaluation_report.md`

## Files To Create Or Edit

1. `code/README.md`
2. `code/main.py`
3. `code/evaluation/main.py`
4. `code/evaluation/evaluation_report.md`
5. `output.csv`
6. `code.zip`
7. Any final prompt or config files required by the selected strategy

## Python Stack For This Phase

1. `python3`
2. `pydantic`
3. `pytest`
4. provider SDKs only as needed for the final run

## Implementation Steps

1. Freeze the final strategy selection and record:
   provider, model, prompt versions, adjudication rules, and escalation policy.
2. Generate final predictions for `dataset/claims.csv` and validate:
   row count, column order, enums, booleans, and image IDs.
3. Run the full evaluation flow on `dataset/sample_claims.csv` one last time and store the report.
4. Update `code/README.md` with:
   environment variables, install steps, inference command, evaluation command, and cache behavior.
5. Remove dead strategy code only if doing so does not harm reproducibility of the reported comparisons.
6. Perform a final audit against repo requirements:
   no secrets, no hardcoded sample labels, evaluation folder present, and submission artifacts complete.
7. Create `code.zip` from the runnable `code/` directory and verify it includes:
   source files, prompts/configs, `code/README.md`, `code/requirements.txt`, and `code/evaluation/`.
8. Produce a short release note for the final run so the strategy choice is defensible in review or interview.
9. Verify that `code.zip` does not include:
   `.venv`, Ollama model files, generated cache directories, API responses, or secrets.

## Deliverables

1. Final `output.csv`.
2. Final `code/evaluation/evaluation_report.md`.
3. Final `code/README.md`.
4. Final `code.zip`.
5. Final reproducibility note.

## Agent Notes

1. If Stage 3 remains enabled, document the exact escalation gates and expected escalation rate.
2. Freeze prompt versions, model identifiers, and schema versions in the final report.
3. Do not leave benchmark-only provider branches ambiguous in the README.
4. The final README must state which environment variables are optional and which are required for the frozen strategy.
5. The final README must include the macOS/Linux setup sequence:
   Python venv setup, dependency install, `GEMINI_API_KEY`, Ollama install, and `ollama pull qwen3-vl:4b`.

## Verification Gate

Phase 6 is complete only if all of the following are true:

1. `output.csv` exists and is schema-valid for every row in `dataset/claims.csv`.
2. `code/evaluation/evaluation_report.md` explains compared strategies and the final chosen one.
3. `code/README.md` is sufficient for another engineer to rerun inference and evaluation.
4. `code.zip` exists and contains the runnable code plus `code/evaluation/`.
5. `code.zip` excludes venvs, model weights, generated caches, provider response dumps, and secrets.
6. A final audit confirms the repo meets the submission contract.

## Required Evidence To Capture

1. Final sample-set metrics.
2. Final operational analysis.
3. Final artifact checklist.

## Risks

1. Late prompt changes without reevaluation can invalidate the final report.
2. Cleaning too aggressively can remove evidence needed for reproducibility.
3. Failing to freeze config versions can make final outputs non-repeatable.

## Locked Defaults

1. Freeze one best production strategy, with escalation enabled only if it measurably improves final evaluation metrics.
2. Preserve summarized comparison artifacts and reports while keeping large run artifacts out of version control.

## Slices

### Slice 6.1: Final strategy freeze

Scope:
record final provider choices, prompt versions, and escalation gates.

Verification:
final configuration note is written.

### Slice 6.2: Final inference

Scope:
run the chosen pipeline on `dataset/claims.csv`.

Verification:
`output.csv` is produced and schema-valid.

### Slice 6.3: Final evaluation

Scope:
rerun the sample evaluation with the frozen pipeline.

Verification:
final `evaluation_report.md` is updated.

### Slice 6.4: README and reproducibility

Scope:
finalize `code/README.md` with exact commands and environment expectations.

Verification:
README includes inference, evaluation, cache, and escalation documentation.

### Slice 6.5: Submission audit

Scope:
run the final checklist for artifacts, schema, zip contents, and repo compliance.

Verification:
a final audit note confirms submission readiness, including `code.zip` contents.

## Phase Command Targets

1. Final inference run on `dataset/claims.csv`.
2. Final evaluation run on `dataset/sample_claims.csv`.
3. Final `code.zip` creation and inspection.
4. Final submission audit command set.

## Exit Criteria

The work is complete only when a fresh operator can run the documented commands and reproduce evaluation and inference outputs without tribal knowledge.
