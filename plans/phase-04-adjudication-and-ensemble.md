# Phase 4: Adjudication And Strategy Portfolio

## Code Review Fixes (Slice 4.0)

Before executing the core adjudication and strategy implementation, the following concerns from Phase 1-3 review must be addressed:

1. **Remove hardcoded absolute path fallbacks**:
   - Locate and delete any absolute path fallback strings like `/Users/meharaj/...` in `code/src/pipeline/claim_parser.py` (L22) and `code/src/pipeline/image_reviewer.py` (L52).
2. **Make error fallback conservative instead of optimistic in `image_reviewer.py`**:
   - In `image_reviewer.py` exception handling, set default values to: `object_visible=False`, `relevant_part_visible=False`, `issue_observed="unknown"`, `issue_matches_claim=False`, and `part_seen="unknown"`.
3. **Expose Ollama adapter in `--model` CLI choices**:
   - In `code/main.py` and `code/evaluation/main.py`, add `"ollama"` to the model `choices` argument.
4. **Extract shared JSON cleaning utility**:
   - Create `code/src/utils/json_utils.py` with `clean_and_load_json(text: str) -> dict` to centralize markdown code fence removal, JSON brace extraction, and parsing.
   - Replace local `_clean_and_load_json` copies in `claim_parser.py`, `image_reviewer.py`, and `reviewer.py` with imports of the shared utility.
5. **Use SDK `system_instruction` in GeminiAdapter**:
   - In `code/src/models/gemini_adapter.py`, pass system prompt using `config=types.GenerateContentConfig(system_instruction=system_prompt, ...)` instead of prompt concatenation.

## Goal

Turn intermediate observations into final submission rows and build the strategy portfolio that competes on quality, not just simplicity.

## Agent Mission

Implement deterministic row construction from Stage 1 and Stage 2 outputs, and compare the main strategy variants without yet optimizing throughput.

## Why This Phase Exists

Intermediate observations are necessary but not sufficient. The repo is graded on final rows, so this phase converts evidence into exact evaluator-facing outputs and compares competing strategies rigorously.

## Files To Read Before Starting

1. `plans/phase-03-evidence-intelligence.md`
2. `dataset/sample_claims.csv`
3. `code/evaluation/evaluation_report.md`

## Files To Create Or Edit

1. `code/src/pipeline/aggregation.py`
2. `code/src/pipeline/adjudication.py`
3. `code/src/pipeline/strategy_single_pass.py`
4. `code/src/pipeline/strategy_staged.py`
5. `code/src/pipeline/strategy_escalation.py`
6. `code/src/utils/enums.py`
7. `code/src/models/gemini_adapter.py`
8. `code/tests/test_adjudication.py`
9. `code/evaluation/evaluation_report.md`
10. `code/src/utils/json_utils.py` (New JSON utility)
11. `code/src/pipeline/claim_parser.py` (Remove hardcoded path / use JSON utility)
12. `code/src/pipeline/image_reviewer.py` (Remove hardcoded path / use JSON utility / conservative fallback)
13. `code/src/pipeline/reviewer.py` (Use JSON utility)
14. `code/main.py` (Expose Ollama CLI option)
15. `code/evaluation/main.py` (Expose Ollama CLI option)

## Python Stack For This Phase

1. `python3`
2. `pydantic`
3. `pytest`
4. optional `pandas`

## Implementation Steps

1. Build a cross-image aggregator that merges per-image findings into row-level evidence:
   support signals, contradiction signals, insufficiency signals, and risk flags.
2. Write explicit adjudication rules for:
   `evidence_standard_met`, `valid_image`, `issue_type`, `object_part`, `claim_status`, `severity`, `risk_flags`, and `supporting_image_ids`.
3. Encode precedence rules so contradictions are handled consistently:
   wrong object, visible no-damage, ambiguous part, image unusable, and user-history-risk overlays.
4. Implement Strategy A:
   single-pass holistic prediction using the cheapest viable benchmark path.
5. Implement Strategy B:
   Stage 1 plus Stage 2 plus deterministic adjudicator as the main low-cost path.
6. Implement Strategy C:
   Strategy B plus conditional Gemini hosted re-review on flagged rows.
7. Run all strategies on `dataset/sample_claims.csv` and compare:
   row exact match, field metrics, slice metrics, and qualitative failure modes.
8. Add ablation runs:
   with and without history signals, with and without image-quality prechecks, and with and without escalation.
9. Freeze the current best adjudication logic only after the ablations explain why it wins.
10. Add explicit serialization rules for final rows:
   lowercase booleans, canonical `risk_flags` order, deterministic `supporting_image_ids`, and object-specific `object_part` validation.
11. Add anti-overfitting notes for every new rule:
   rules must be based on evidence patterns, not sample row IDs, filenames, user IDs, or exact transcript strings.

## Deliverables

1. Final-row adjudication engine.
2. Strategy A baseline.
3. Strategy B main path.
4. Strategy C conditional escalation path.
5. Strategy comparison table on `sample_claims.csv`.

## Agent Notes

1. Strategy C must never escalate all rows by default.
2. Escalation triggers should be explicit code, not prompt-only heuristics.
3. Keep the adjudicator provider-agnostic.
4. The merge policy after escalation must be deterministic:
   define when escalated output overrides provisional output and when it does not.
5. `supporting_image_ids` must identify images that support the final decision.
   For `contradicted`, this can be the image showing no relevant damage, wrong object, or mismatched part.
   For `not_enough_information`, use `none` unless an image directly supports the insufficiency reason.
6. Stage 3 quality lift can only be measured on labeled rows.
   For unlabeled `claims.csv`, use the frozen gates from sample evaluation and report the escalation rate.
7. Do not add OpenAI or Anthropic for Stage 3.
   Gemini is the only hosted provider unless the user explicitly changes this decision.

## Verification Gate

Phase 4 is complete only if all of the following are true:

1. All active strategies produce schema-valid final rows.
2. Strategy comparisons are stored in the experiment registry.
3. The best strategy is selected based on evidence, not intuition.
4. Adjudication tests cover the most important contradiction and insufficiency scenarios.

## Required Evidence To Capture

1. Strategy leaderboard table.
2. Ablation report showing what changed metrics and why.
3. Representative row-level explanations for key wins and failures.

## Risks

1. Directly tuning rules to sample IDs will overfit and damage hidden performance.
2. Weak precedence rules will create inconsistent combinations such as supported claims with insufficient evidence.
3. Escalation logic without clear triggers can raise cost with no measurable gain.
4. Treating `supporting_image_ids` as claim-support-only will mislabel contradicted rows.
5. Stage 3 can exhaust free-tier quota if gates are too broad.

## Locked Defaults

1. Prefer the best row-exact and field-accuracy strategy even if it uses more free-tier quota.
2. Treat quota use as a tiebreaker, not the primary selector.
3. Allow interpretability to matter, but not enough to choose a weaker strategy when the metric gap is real.

## Slices

### Slice 4.0: Code Review Fixes

Scope:
Address the 5 identified P1/P2 code review concerns (remove absolute paths, conservative fallback, Ollama CLI option, shared JSON utility, GeminiAdapter system_instruction).

Verification:
All code runs successfully, tests continue to pass, and CLI supports ollama.

### Slice 4.1: Aggregation layer

Scope:
merge per-image observations into row-level evidence structures.

Verification:
aggregator tests pass on hand-crafted cases.

### Slice 4.2: Deterministic adjudicator

Scope:
map aggregated evidence to final repo fields.

Verification:
adjudication tests cover support, contradiction, insufficiency, and mismatch cases.

Must include:
tests for contradicted rows with supporting image IDs, canonical risk flag ordering, lowercase booleans, and `issue_type=none` versus `issue_type=unknown`.

### Slice 4.3: Strategy A baseline

Scope:
implement a single-pass holistic baseline using the cheapest viable benchmark path.

Verification:
Strategy A produces schema-valid predictions on `sample_claims.csv`.

### Slice 4.4: Strategy B main path

Scope:
connect Stage 1 + Stage 2 + adjudicator into the main no-spend path.

Verification:
Strategy B produces schema-valid predictions and evaluation metrics on `sample_claims.csv`.

### Slice 4.5: Stage 3 escalation framework

Scope:
implement escalation trigger logic, escalation request object, and deterministic merge policy.

Verification:
flagged rows can be escalated and merged deterministically.

Required caveat:
measure quality lift on labeled sample rows only; on unlabeled test rows, record escalation count and reasons.
If `GEMINI_API_KEY` is absent or quota is unavailable, Strategy C must disable Stage 3 and still produce schema-valid rows.

### Slice 4.6: Strategy C end-to-end

Scope:
connect Strategy B with conditional Stage 3 escalation.

Verification:
Strategy C runs on `sample_claims.csv` and records escalation rate.

### Slice 4.7: Ablations and leaderboard

Scope:
run with and without history, prechecks, and escalation.

Verification:
leaderboard and ablation summary are produced.

## Phase Command Targets

1. Run all strategy variants on `dataset/sample_claims.csv`.
2. Produce a strategy leaderboard and ablation summary.

## Exit Criteria

Do not start Phase 5 until the chosen strategy is measurably stronger than the baseline and the reasons are documented.
