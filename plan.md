# Multimodal Claims Review Plan

## Objective

Build the highest-performing reproducible system in this repo for multimodal damage-claim verification, optimized for:

1. Maximum correctness on the required output schema and allowed enums.
2. Strong generalization beyond `dataset/sample_claims.csv`, without file-specific shortcuts.
3. Scalable inference, experiment tracking, and cost/runtime control.
4. Clean final artifacts: `output.csv`, `code/README.md`, and `evaluation/`.

## Strategy

The target solution should not be a single prompt wrapped in glue code. It should be a staged evidence-review system with:

1. Deterministic input and output contracts.
2. Structured multimodal extraction per image.
3. Claim parsing that is robust to multilingual, compound, and instruction-like text.
4. A decision engine that converts observations into final repo enums.
5. A portfolio of strategies with disagreement-aware escalation.
6. A measurable optimization loop tied to the repo evaluation requirements.

## Target Architecture

```text
claims.csv row
  -> contract-safe loader
  -> Stage 1: claim parser
  -> Stage 2: primary evidence review
       -> image quality and authenticity checks
       -> per-image evidence extraction
       -> cross-image aggregator
       -> deterministic provisional adjudication
  -> Stage 3: conditional Gemini escalation
       -> full-row re-review on flagged rows only
       -> escalation merge policy
  -> final schema validator
  -> output.csv row

sample_claims.csv
  -> experiment runner
  -> metrics and slice analysis
  -> strategy comparison
  -> evaluation report
```

## Proposed Repo Layout

```text
code/
  README.md
  main.py
  evaluation/
    main.py
    reporting.py
    metrics.py
  src/
    config.py
    schemas.py
    csv_io.py
    image_io.py
    history.py
    requirements.py
    prompts/
      claim_parser.md
      image_reviewer.md
      holistic_reviewer.md
      adjudicator.md
    models/
      base.py
      gemini_adapter.py
      ollama_adapter.py
      mock_adapter.py
    pipeline/
      claim_parser.py
      image_quality.py
      image_reviewer.py
      aggregation.py
      adjudication.py
      strategy_single_pass.py
      strategy_staged.py
      strategy_escalation.py
    telemetry/
      events.py
      caching.py
      costing.py
      experiments.py
    utils/
      enums.py
      text.py
      files.py
      retry.py
  tests/
    test_schemas.py
    test_metrics.py
    test_adjudication.py
    test_pipeline_smoke.py
```

## Python Stack Mapping

Python is the orchestration layer for the full system. Models are replaceable backends behind Python adapters.

| Layer | Responsibility | Python stack |
|---|---|---|
| IO and contracts | CSV loading, path resolution, output writing, schema validation | `python3`, `pydantic`, `csv` or `pandas` |
| Stage 1 | Claim parsing and structured extraction | provider SDK or `httpx`, `pydantic` |
| Stage 2 | Image loading, local or free inference, per-image observations | `Pillow`, optional `opencv-python`, provider SDKs or local inference runtime |
| Stage 3 | Conditional Gemini escalation and merge-back | provider SDK or `httpx`, `pydantic` |
| Adjudication | Deterministic business rules and enum mapping | pure Python |
| Telemetry | caching, cost tracking, retries, experiment metadata | pure Python, `json`, `sqlite3` or local files |
| Evaluation | metrics, slice analysis, markdown reporting | pure Python, optional `pandas` |
| Testing | schema, adjudication, pipeline, metrics regression tests | `pytest` |

## Runtime Command Contract

All coding agents must use these command conventions unless a later phase explicitly changes them.

1. Use `python3`, not bare `python`.
2. Create and use a repo-local virtual environment:
   `python3 -m venv .venv`.
3. Install dependencies from `code/requirements.txt`:
   `.venv/bin/python -m pip install -r code/requirements.txt`.
4. Run modules through the venv interpreter:
   `.venv/bin/python -m pytest code/tests`.
5. Do not assume global packages are installed.
6. If a provider SDK is optional, keep the import lazy and fail with a clear setup message.

## Judge Setup Contract

The project should be easy to set up on macOS or Linux during evaluation.
The default setup path is:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r code/requirements.txt

export GEMINI_API_KEY="your-google-ai-studio-api-key"

if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

ollama list >/dev/null 2>&1 || (ollama serve >/tmp/ollama.log 2>&1 & sleep 3)
ollama pull gemma4:e4b
ollama run gemma4:e4b ""
```

Implementation requirements:

1. `code/requirements.txt` must include `google-genai`, `pydantic`, `pytest`, `Pillow`, and any other implemented dependency.
2. Hosted Gemini calls must read `GEMINI_API_KEY` from the environment.
3. Local fallback calls must use Ollama with model `gemma4:e4b`.
4. If Ollama or `gemma4:e4b` is unavailable, the code must fail with a clear setup message or continue through the hosted Gemini path when configured.
5. Do not bundle local model weights or generated model caches in `code.zip`.

## Confirmed Architecture Direction

The intended production design is a three-stage system:

1. `Stage 1: Claim understanding`
   cheap text-first structured extraction.
2. `Stage 2: Primary evidence review`
   free or local multimodal review plus deterministic provisional adjudication.
3. `Stage 3: Conditional Gemini escalation`
   hosted Gemini re-review only for flagged hard rows.

Stage 3 is conditional. It must not run on every row by default.

## Phase Map

| Phase | Goal | Verification artifact | Playbook |
|---|---|---|---|
| 1 | Build the contract-safe foundation | Schema-valid dry run on sample rows | [plans/phase-01-foundation.md](/Users/meharaj/hackerrank-orchestrate-june26/plans/phase-01-foundation.md) |
| 2 | Build evaluation and error-analysis machinery | Repeatable sample-set metrics report | [plans/phase-02-evaluation.md](/Users/meharaj/hackerrank-orchestrate-june26/plans/phase-02-evaluation.md) |
| 3 | Build evidence-understanding components | Structured per-image and per-claim outputs | [plans/phase-03-evidence-intelligence.md](/Users/meharaj/hackerrank-orchestrate-june26/plans/phase-03-evidence-intelligence.md) |
| 4 | Build final decision engine and strategy portfolio | Strategy leaderboard with ablations | [plans/phase-04-adjudication-and-ensemble.md](/Users/meharaj/hackerrank-orchestrate-june26/plans/phase-04-adjudication-and-ensemble.md) |
| 5 | Optimize for scale, latency, and cost | Full test-set throughput rehearsal | [plans/phase-05-scale-and-optimization.md](/Users/meharaj/hackerrank-orchestrate-june26/plans/phase-05-scale-and-optimization.md) |
| 6 | Freeze, validate, and package the final system | Submission-grade artifacts and dry-run checklist | [plans/phase-06-finalization.md](/Users/meharaj/hackerrank-orchestrate-june26/plans/phase-06-finalization.md) |

## Execution Rules

1. Every phase must end with a written verification note and a machine-verifiable output.
2. Every model call should emit structured data, never free-form text that downstream code has to guess at.
3. Optimize for evaluator-visible quality first:
   exact enums, exact columns, image-grounded justifications, and consistent `supporting_image_ids`.
4. Avoid hidden overfitting:
   no case IDs, no path-based logic, no direct memorization of sample rows.
5. Treat user history as a risk modifier, not as evidence that overrides clear images.
6. Keep all provider-specific logic behind adapters so strategies can be compared cleanly.
7. Record experiment metadata for every prompt or rule change that affects outputs.

## Canonical Output Serialization Rules

These rules prevent agents from producing semantically correct but evaluator-hostile CSV strings.

1. Booleans must serialize as lowercase strings:
   `true` or `false`.
2. `risk_flags` must serialize as `none` or a semicolon-separated list in the allowed-value order from `problem_statement.md`.
3. `supporting_image_ids` means images that support the final decision, not only images that support the user's claim.
   For `contradicted`, include images that show the contradiction.
   For `not_enough_information`, use `none` unless a visible image directly supports the insufficiency reason.
4. `supporting_image_ids` must use filename stems such as `img_1`, preserve deterministic ascending image order, and never include file extensions.
5. `issue_type=none` is only for a visible relevant part with no damage.
   Use `issue_type=unknown` when the issue cannot be determined.
6. User-history risk can add `user_history_risk` and `manual_review_required`, but it must not override clear visual evidence by itself.

## Anti-Overfitting Rules

The sample set has only 20 labeled rows, so every sample-driven change must generalize.

1. Do not branch on case IDs, image paths, filenames, exact user IDs, row order, or exact claim text.
2. Any adjudication rule learned from a sample failure must be described as an object, part, evidence, or risk-pattern rule.
3. Keep one experiment note per prompt or rule change explaining why the change should generalize to hidden rows.
4. Treat sample row exact match as the development signal, not as permission to memorize labels.

## Recommended Strategy Portfolio

### Strategy A: Holistic single-pass baseline

One multimodal call consumes all row inputs and emits the final schema.

Purpose:
Establish a fast baseline and a fallback for comparison.

### Strategy B: Staged evidence pipeline

Separate claim parsing, per-image review, aggregation, and adjudication.

Purpose:
Improve enum control, explainability, and robustness to multi-image ambiguity.

### Strategy C: Disagreement-aware escalation

Run Strategy B by default, then escalate only hard rows to a stronger or second model when confidence is low or component outputs conflict.

Purpose:
Push accuracy higher without spending quota on every row.

This is the likely final path if Gemini access and quota allow it.

## Evaluation Optimization Goals

The repo explicitly requires strategy comparison and operational analysis, but the hidden ranking will likely be driven by prediction quality. The system should therefore optimize the following visible and likely-important dimensions:

1. Full-row exact match on `sample_claims.csv`.
2. Per-field accuracy on `claim_status`, `issue_type`, `object_part`, `severity`, and `valid_image`.
3. Set quality on `risk_flags` and `supporting_image_ids`.
4. Calibration quality on `evidence_standard_met` versus `claim_status`.
5. Cross-slice stability:
   object type, number of images, multilingual claims, claim mismatch cases, and user-history-risk cases.

## Locked Decisions

The following choices are now confirmed and should be treated as implementation constraints.

1. Language and tooling:
   use `Python`, `pydantic`, and `pytest`.
2. Core architecture:
   use the staged evidence pipeline as the production path, not a single-pass prompt.
3. Determinism policy:
   use strict structured outputs and deterministic post-processing; do not rely on free-form reasoning text.
4. Quota policy:
   use hosted escalation only through selective gates on hard rows.
5. OCR and preprocessing policy:
   allow OCR and classical image-quality checks only as supporting signals, not as primary decision-makers.
6. Fine-tuning policy:
   do not fine-tune on this dataset; prefer prompt, rule, and evaluation improvements.
7. Final system shape:
   prefer a strategy portfolio during experimentation, but freeze to one best production path plus optional bounded escalation if it measurably helps.

## Recommended Provider Direction

### Recommended primary no-spend hosted path: Gemini free tier direct

Reasoning:

1. It aligns with the no-spend goal better than additional hosted providers.
2. It still gives hosted multimodal quality, which is likely stronger than small local models on subtle visual review.
3. It supports structured JSON output and multimodal input, which fit the evaluator-facing schema constraints.

### Recommended local no-API baseline: Gemma 4 E4B through Ollama

Reasoning:

1. It is realistic on laptop-class hardware.
2. Ollama gives the simplest macOS/Linux setup and model download flow.
3. It provides an offline fallback and benchmark without API dependency.
4. It should be benchmarked, not assumed to beat the hosted path on evaluator-facing accuracy.

### Recommended escalation path: Gemini hosted re-review

Reasoning:

1. The user will use Gemini through a Google account, primarily on free-tier quota.
2. Hosted Gemini quality is expected to beat the local fallback on subtle visual evidence review.
3. Stage 3 remains conditional and should not run on every row by default.
4. If quota is exhausted, Stage 3 must disable cleanly or fall back to the local path.

### Recommended not to use as the main no-spend path: OpenRouter free router

Reasoning:

1. Free-router variance hurts reproducibility.
2. Free request caps are a poor fit for repeated evaluation and reruns.
3. Fixed-model OpenRouter usage can still be useful for benchmarking, but not as the main final-path assumption.

## Locked Provider Strategy

1. Primary Stage 2 hosted path:
   `Gemini free tier direct`.
2. Local baseline and fallback:
   `Ollama` running `gemma4:e4b`.
3. Stage 3 conditional escalation:
   use `Gemini hosted re-review` with the same Google provider path; do not implement OpenAI.
4. Local `gemma4:e4b` role:
   benchmark and fallback only, not the first-class default main path.
5. Stage 3 gate policy:
   `balanced gates`.
6. Stage 3 budget policy:
   `zero direct paid spend by default`; report quota usage and disable escalation if free quota is unavailable.
7. Initial provider implementation scope:
   `Gemini + Ollama gemma4:e4b + mock adapter`.
8. Do not implement OpenAI or Anthropic unless the user explicitly changes the provider scope.

## Recommended Model Stack

### No-spend primary path

1. Claim parser:
   Gemini through the Google Gen AI SDK, using structured JSON output.
2. Primary per-image reviewer:
   `Gemini free tier` direct.
3. Optional local-only baseline:
   `Ollama` with `gemma4:e4b`.

### Conditional escalation path

1. Escalation reviewer:
   Gemini hosted re-review with a stricter holistic prompt and the same final-row schema.
2. Escalation should run only on flagged rows and never as a full-dataset default.
3. Escalation must be disabled automatically if `GEMINI_API_KEY` is missing or quota is exhausted.

## Evaluation-Driven Selection Rules

Choose providers and models using these rules in order:

1. Highest row exact match on `dataset/sample_claims.csv`.
2. Best combined accuracy on `claim_status`, `issue_type`, `object_part`, and `supporting_image_ids`.
3. Fewest schema failures and enum drifts.
4. Best performance on multilingual rows, multi-image rows, contradiction rows, and instruction-like rows.
5. Lowest quota/cost use only as a tiebreaker after quality and schema reliability.
6. For Stage 3, measure marginal gain on escalated sample rows rather than full-dataset score.

## Confirmed Execution Decisions

1. Use `Gemini free tier direct` as the primary no-spend hosted path.
2. Use `Ollama` with `gemma4:e4b` as the local offline baseline and fallback.
3. Keep hosted re-review only as `Stage 3 escalation`, not as a full-dataset default.
4. Use Gemini as the only hosted provider unless the user later changes direction.
5. Treat free quota and no direct API spend as constraints; report quota usage in the operational analysis.
6. Enable OCR and classical image preprocessing only as supporting signals.
7. Fix the implementation to Python with `pydantic` and `pytest`.
8. Freeze one best production path, keeping automatic escalation only if evaluation proves it helps.
9. Exclude large experiment and cache artifacts from version control.

## Local Runtime Decision

The local runtime is locked to `Ollama` with model `gemma4:e4b`.

Implementation rules:

1. Use Ollama only as a local benchmark/fallback unless evaluation shows it beats Gemini on a specific slice.
2. Include setup commands in `README.md`, `code/README.md`, and `AGENTS.md`.
3. The setup command must download `gemma4:e4b` during setup with `ollama pull gemma4:e4b`.
4. Local model weights, Ollama caches, and generated provider caches must not be included in `code.zip`.
5. If local setup fails on a judge machine but `GEMINI_API_KEY` is available, the final system should still run through the Gemini path.

## Coding Agent Execution Contract

The implementation will be done by coding agents, so each phase should be treated as an executable contract.

1. Each phase must start by reading:
   `AGENTS.md`, `plan.md`, and the current phase file.
2. Each agent should only edit the files listed in its phase unless a dependency forces a documented expansion.
3. Each phase must end with:
   a runnable command, a produced artifact, and a short validation note.
4. No agent should introduce provider-specific logic directly into adjudication or evaluation modules.
5. Every model output consumed by Python must be validated through a `pydantic` schema before downstream use.
6. Any escalation rule added by an agent must be testable and recorded in the experiment notes.
7. If an agent changes prompt shape, schema shape, or adjudication logic, it must rerun the relevant phase verification gate.

## Slice Strategy

Every phase must be executable in small slices so a smaller coding model can complete the work without losing context. A slice should usually change one subsystem, produce one verification artifact, and avoid cross-phase scope creep.

Rules:

1. Each slice should touch a narrow file set.
2. Each slice should end with one concrete command or artifact proving completion.
3. Later slices may depend on earlier slices, but a slice should never assume unfinished work from a later slice.
4. If a slice cannot be verified independently, it is too large and should be split again.

## What To Do Next

1. Execute Phase 1 exactly as written.
2. Keep work slice-by-slice inside each phase.
3. Do not begin provider benchmarking until the Phase 2 harness is producing trustworthy metrics.
