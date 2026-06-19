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

## Documented Gaps After Review

These are the concrete gaps found while reviewing the implemented Phase 5 work. Keep this list current before starting the packaging or service-hosting refactor.

1. **Submission quality is still the primary blocker**.
   The checked-in Strategy B evaluation report currently shows very weak sample-set quality, so better operations alone will not make the system ready.
2. **Concurrency is still planned, not implemented**.
   Claim and image processing remain sequential in the main orchestration path.
3. **Stage 3 economics are not yet evidenced in a credible final artifact**.
   The phase requires escalation-rate, marginal-lift, and projected-cost reporting, but that operational evidence is not yet locked down in a final verified report.
4. **Full test-set throughput rehearsal is not yet captured as a stable phase artifact**.
   The phase contract calls for a real end-to-end rehearsal with operational summary, not only partial local smoke checks.
5. **Requirement filtering is still fuzzy and may over-match**.
   The current `csv_io.py` requirement filtering uses substring matching and should be tightened before treating it as reusable library logic.
6. **Aggregation mismatch handling is too coarse**.
   Mixed-image claims can be penalized too aggressively when one image is mismatched but another image correctly shows the claimed part.
7. **Top-level orchestration is still CLI-first instead of library-first**.
   `code/main.py` owns too much runtime wiring: loading datasets, constructing managers, selecting strategies, handling cache/telemetry, and writing rows.
8. **Entrypoints still depend on `sys.path` bootstrapping**.
   `code/main.py`, `code/evaluation/main.py`, `code/evaluation/metrics.py`, and `code/src/pipeline/smoke_evidence.py` rely on `sys.path.insert(...)`, which is a packaging smell and blocks clean library export.
9. **There is no stable public import surface for consumers**.
   Components exist under `src/`, but there is no curated top-level API for importing claim processors, repositories, strategies, or service-ready facades.
10. **Single-claim processing is implicit, not modeled as an application service**.
    Pipelines can process one claim, but there is no dedicated `process_claim(...)` service boundary that a web API, job worker, or external library consumer can call directly.
11. **Infrastructure dependencies are not fully injectable**.
    History loading, requirements loading, cache paths, telemetry paths, and model construction are still too coupled to local runtime wiring.
12. **Cache and telemetry are local-run oriented**.
    They work for current CLI runs, but they are not yet shaped as replaceable backends for service deployment.

## Improvements To Land Before Packaging And Service Hosting

Use this as the refactor backlog before exporting the project as a reusable library or hosting it as a service.

1. **Make the codebase package-first**.
   Add installable package metadata and remove `sys.path` hacks from runtime entrypoints.
2. **Create a public application API**.
   Expose a small stable surface such as:
   `process_claim`, `process_claim_batch`, `build_pipeline`, `build_model_adapter`, and `evaluate_predictions`.
3. **Separate CLI, library, and service layers**.
   Keep `main.py` as a thin CLI wrapper; move orchestration into importable application services.
4. **Introduce a claim-processing service boundary**.
   Add a dedicated service object or module that accepts one claim plus dependencies and returns a validated `ClaimOutput`.
5. **Extract dependency construction from business orchestration**.
   Model adapters, cache, telemetry, history store, and requirements store should be wired by factories or dependency-injection helpers, not directly inside the core execution loop.
6. **Introduce repository/provider abstractions for data sources**.
   User history, evidence requirements, prompts, cache storage, and telemetry sinks should be replaceable so the system can run from files today and a hosted backend later.
7. **Define service-safe request and response contracts**.
   Add explicit request DTOs for single-claim and batch processing so external callers do not need to know repo file layouts.
8. **Move runtime state to explicit configuration objects**.
   Cache directories, telemetry sinks, retry policies, model selection, and dataset roots should all be configurable without editing CLI code.
9. **Curate module exports**.
   Add meaningful `__init__.py` exports so consumers can import the intended building blocks without reaching deep into internal modules.
10. **Split evaluation concerns from production inference concerns**.
    Evaluation utilities should stay importable, but they should not be required for normal single-claim inference.
11. **Preserve per-claim idempotency and resumability semantics**.
    The full-claim identity checkpoint logic should become a reusable primitive so batch jobs and services share the same correctness rule.
12. **Add service-oriented tests**.
    After refactoring, cover import-based usage, single-claim invocation, dependency injection, and library-level output validation, not only CLI and file-based flows.
