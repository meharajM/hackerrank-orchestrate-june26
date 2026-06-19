# Phase 5: Scale, Throughput, And Cost Optimization

## Goal

Make the best strategy production-capable for larger batches while preserving or improving quality.

## Agent Mission

Turn the selected strategy into a reliable batch system with telemetry, caching, and bounded escalation economics.

## Why This Phase Exists

An optimal solution is not only accurate. It must also process the full test set reliably, avoid unnecessary cost, and expose operational analysis that is credible.

## Files To Read Before Starting

1. `plans/phase-04-adjudication-and-ensemble.md`
2. `code/evaluation/evaluation_report.md`

## Files To Create Or Edit

1. `code/src/telemetry/events.py`
2. `code/src/telemetry/caching.py`
3. `code/src/telemetry/costing.py`
4. `code/src/utils/files.py`
5. `code/src/pipeline/strategy_escalation.py`
6. `code/main.py`
7. `code/evaluation/evaluation_report.md`

## Python Stack For This Phase

1. `python3`
2. provider SDKs or `httpx`
3. local file cache or `sqlite3`
4. optional concurrency primitives from `asyncio` or thread pools

## Implementation Steps

1. Add request-level telemetry for:
   provider, model, prompt version, tokens, images, latency, retries, and cache hits.
2. Add content-addressed caching for:
   claim-parser outputs, per-image reviews, and final row predictions when inputs are unchanged.
3. Add bounded concurrency with provider-aware throttling and retry policies.
4. Add selective escalation triggers based on:
   low confidence, cross-component disagreement, poor image quality, or unsupported compound claims.
5. Build runtime and cost estimation for:
   sample runs, test runs, and projected larger-scale runs.
6. Add resumable batch execution so partial failures do not force full reruns.
7. Run throughput rehearsals on the full test input and capture operational stats.
8. Update the evaluation report with real operational analysis, not guesses.
9. Separate labeled-sample quality lift from unlabeled-test operational telemetry.
   Stage 3 quality gain can be computed on `sample_claims.csv`; for `claims.csv`, report only escalation rate, latency, cost, and reasons.

## Deliverables

1. Telemetry and cache layer.
2. Resumable batch runner.
3. Escalation-rate report.
4. Operational analysis inputs for the evaluation report.

## Agent Notes

1. Measure how many rows trigger Stage 3.
2. Record average images per escalated row and average latency impact.
3. If Gemini escalation uses too much free-tier quota, tune gates before changing provider.
4. Keep caches keyed by:
   prompt version, model id, input content hash, and image hash list.
5. Do not inspect or manually tune final `claims.csv` predictions after seeing Gemini escalation outputs.
   Final test behavior must come from frozen gates and deterministic merge policy.
6. Keep generated caches local only.
   Do not include cache directories, Ollama model files, or provider response dumps in `code.zip`.

## Verification Gate

Phase 5 is complete only if all of the following are true:

1. The chosen strategy can process the full test input end to end.
2. Reruns benefit from caching and resumability.
3. The system emits enough telemetry to justify the operational report.
4. Escalation improves quality or cost-adjusted quality measurably on labeled sample rows, or it is disabled for final inference.

## Required Evidence To Capture

1. Runtime and cost summary for sample and test processing.
2. Cache-hit statistics from repeated runs.
3. A failure-and-retry log proving the batch runner is resilient.

## Risks

1. Concurrency without throttling will create avoidable provider errors.
2. Caching without input hashing will serve stale results.
3. Optimization before telemetry will produce false confidence about cost and latency.

## Locked Defaults

1. Optimize without a hard spend ceiling at first, while requiring escalation to justify itself with measured gains.
2. Keep cached artifacts local-only and out of version control.
3. Default direct paid API spend is zero; use Gemini free-tier quota when available and document quota assumptions.

## Slices

### Slice 5.1: Telemetry events

Scope:
record provider, model, latency, tokens, cache hits, and escalation counts.

Verification:
one run emits telemetry for every processed row.

### Slice 5.2: Caching layer

Scope:
cache Stage 1, Stage 2, and Stage 3 outputs by input hash and prompt version.

Verification:
warm rerun shows cache hits.

### Slice 5.3: Resumable batch runner

Scope:
make the main pipeline resumable after interruption.

Verification:
partial run can resume without recomputing completed rows.

### Slice 5.4: Stage 3 economics

Scope:
measure escalation frequency, cost, and row-level lift.

Verification:
report shows escalation rate and marginal benefit on labeled sample rows, plus projected test-set cost based on frozen gates.

### Slice 5.5: Throughput rehearsal

Scope:
run the selected strategy on the full test file and collect operational numbers.

Verification:
full test-set run completes with operational summary.

## Phase Command Targets

1. Run the selected strategy across the full test set.
2. Re-run it with cache warm and capture the delta.

## Exit Criteria

Do not start Phase 6 until the chosen system can be rerun predictably with credible operational numbers.
