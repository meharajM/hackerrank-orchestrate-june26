# System Architecture: HackerRank Orchestrate Claims Verification

This document provides a deep architectural analysis of the claims verification system built so far. It outlines the design patterns, data flow, component boundaries, the Phase 5 operational work that is now in place, and the remaining gaps blocking submission quality. The current implementation now includes an importable claim-processing service, an importable batch runner, a composable prompt harness, and a standardized OpenAI-compatible transport layer that can drive the local `qwen3-vl:4b` Stage 2 path or any compatible hosted endpoint.

---

## 1. Architectural Blueprint

The system is designed around a **staged, pipeline-oriented architecture** that decouples claim parsing, per-image evidence review, cross-image aggregation, and final adjudication. This contrasts with a simple holistic single-pass LLM call, enabling better predictability, enum enforcement, and cost optimization.

```text
claims.csv Row
     │
     ▼
┌────────────────────────────────────────────────────────┐
│               Stage 1: Claim Parser                    │
│   (Extracts primary object, claimed part, and issue)   │
└────────────────────────┬───────────────────────────────┘
                         │ ParsedClaim
                         ▼
┌────────────────────────────────────────────────────────┐
│          Stage 2: Per-Image Evidence Review            │
│   (Lightweight Pillow precheck + qwen3-vl:4b review)   │
└────────────────────────┬───────────────────────────────┘
                         │ List[ImageObservation]
                         ▼
┌────────────────────────────────────────────────────────┐
│               Stage 3: Cross-Image Aggregation         │
│   (Merges findings, verifies requirements, flags risk) │
└────────────────────────┬───────────────────────────────┘
                         │ AggregatedEvidence
                         ▼
┌────────────────────────────────────────────────────────┐
│             Stage 4: Deterministic Adjudicator         │
│   (Applies 10 business precedence rules - no LLM)      │
└────────────────────────┬───────────────────────────────┘
                         │ Provisional ClaimOutput
                         ▼
┌────────────────────────────────────────────────────────┐
│           Stage 5: Conditional Gemini Escalation       │
│   (Runs Strategy C: hosted re-review on flagged rows)   │
└────────────────────────┬───────────────────────────────┘
                         │ Final ClaimOutput
                         ▼
                     output.csv
```

---

## 2. Component Design & Responsibilities

### 2.1 Schemas & Data Layer (`src/schemas.py`)
- **Single Source of Truth**: Houses all allowed enums (`ClaimObject`, `ClaimStatus`, `IssueType`, `Severity`, `RiskFlag`), field validation rules, and input/output mapping.
- **Strict Pydantic Validation**: `ClaimOutput` validates all fields (e.g., lowercase boolean serialization, canonical risk flag ordering, and object-specific part validation) before serialization to ensure compatibility with the evaluator.

### 2.2 Model Adapters (`src/models/`)
- **ModelAdapter Interface**: Abstract base class defining `text_call`, `multimodal_call`, `is_available`, and telemetry hook `get_stats`.
- **GeminiAdapter**: Communicates with Google's Developer API using `google-genai` and uses `system_instruction` in the generate configuration.
- **OpenAICompatibleAdapter**: Provides the standardized provider surface for OpenAI-compatible chat-completions endpoints, including custom base URLs, JSON-mode responses, and multimodal image payloads. This is the transport layer used to normalize local and remote chat-completions calls.
- **OllamaAdapter**: Sits on top of Ollama's OpenAI-compatible `/v1/chat/completions` API instead of a custom local-only request shape. The current local default uses `qwen3-vl:4b`, and Strategy `B`/`C` can still override Stage 2 independently when needed.
- **MockAdapter**: Simulates realistic, schema-valid JSON responses based on prompt keywords, enabling offline smoke tests and regressions at zero spend.

### 2.3 Evidence Pipelines (`src/pipeline/`)
- **Claim Parser (`claim_parser.py`)**: Converts free-form text transcripts into clean JSON containing structured hypotheses.
- **Image Quality (`image_quality.py`)**: Pillow-based heuristics checking for blur, glare, low light, and orientation prior to LLM execution.
- **Image Reviewer (`image_reviewer.py`)**: Synthesizes precheck findings with per-image multimodal observations, gracefully defaulting to a conservative fallback state on exceptions.
- **Aggregator (`aggregation.py`)**: Fuses per-image findings into `AggregatedEvidence`. It matches requirements from `evidence_requirements.csv` and collects user history risk modifiers.
- **Adjudication (`adjudication.py`)**: A deterministic rule engine running 10 precedence rules. It is entirely model-agnostic and free-form reasoning-free.
- **Strategy Portfolio**:
  - **Strategy A (Holistic)**: Direct single-pass LLM call (baseline).
  - **Strategy B (Staged)**: Decoupled Stage 1 + Stage 2 + Aggregator + Adjudicator (primary low-cost path).
  - **Strategy C (Escalation)**: Default to Strategy B; escalates to a hosted model (Gemini) on low confidence, authenticity concerns, or text instructions.

### 2.4 Application Service Boundary (`src/claim_processing.py`)
- **Single-claim orchestration API**: The codebase now exposes an importable `process_claim(...)` boundary plus `process_claim_batch(...)` for reusable batch execution.
- **Reusable context object**: `ClaimProcessingContext` packages dataset location, the base model, the dedicated Stage 2 model, repositories, cache, telemetry, and cost tracking so the same runtime can be shared across CLI, tests, and future hosted services.
- **Builder entrypoint**: `build_claim_processing_context(...)` centralizes dependency wiring, reducing the amount of orchestration logic left inside `code/main.py`.
- **Stage-aware local wiring**: Strategy `B` and Strategy `C` can now keep a cheaper base adapter while routing per-image validation through a stronger local vision model, typically `qwen3-vl:4b` on the local path.
- **Batch execution seam**: `process_claim_batch(...)` now supports a pluggable batch executor, with `SequentialClaimExecutor` as the default. This is the clean insertion point for future delegated or worker-based claim execution without leaking orchestration logic into the CLI.
- **Public package surface**: `src/__init__.py` now exports the core claim-processing entrypoints for import-based consumers.
- **Installable distribution metadata**: `code/pyproject.toml` now defines an editable-install path for the current `src` and `evaluation` packages, which reduces reliance on ad hoc path bootstrapping.

### 2.8 Batch Runner Boundary (`src/batch_runner.py`)
- **Importable batch execution API**: `run_batch(...)` now owns resumability, CSV output appends, telemetry flushing, and end-to-end batch summaries instead of leaving those concerns inside the CLI module.
- **Explicit batch request/response contract**: `BatchRunRequest` and `BatchRunResult` provide a service-friendly transport shape for CLI, job, and hosted batch execution.
- **Thin CLI wrapper**: `code/main.py` is now mostly argument parsing plus context construction around the reusable batch runner.

### 2.5 Repository Abstractions (`src/history.py`, `src/requirements.py`)
- **History repository interface**: claim processing now depends on a `HistoryRepository` protocol instead of assuming CSV-backed history lookups.
- **Requirements repository interface**: evidence lookup now depends on a `RequirementsRepository` protocol rather than directly binding orchestration to a local file loader.
- **File-backed defaults remain**: `FileHistoryRepository` and `FileRequirementsRepository` preserve current repo behavior while making hosted backends and test doubles injectable.

### 2.6 Cache And Telemetry Providers (`src/telemetry/*`)
- **Cache backend interface**: model adapters and claim processing can now depend on a `CacheBackend` protocol rather than directly on the file-backed `ResponseCache`.
- **Event sink interface**: per-claim telemetry emission can target any `EventSink`, with `EventLogger` remaining the current in-memory and JSON-flush implementation.
- **Cost recorder interface**: token and spend accounting now hangs off a `CostRecorder` protocol so hosted runtimes can swap the default `CostTracker` for external accounting sinks.
- **Injection path is active**: `build_claim_processing_context(...)` now accepts injected cache, telemetry, and cost components while preserving the existing local defaults.

### 2.7 Prompt And Runtime Settings Layer (`src/prompting.py`, `src/runtime.py`)
- **Prompt provider interface**: prompt templates and system prompts can now be sourced through a `PromptProvider` protocol instead of being read ad hoc inside pipeline modules.
- **Composable prompt harness**: `FilePromptProvider` now composes prompt fragments from `src/prompts/_shared/` plus stage-specific prompt files, so always-on security guidance is injected once and optional fragments are loaded only for the stages that need them.
- **Always-on core security**: `core_security.md` is included for every prompt, ensuring prompt-injection resistance across claim text, image text, and user-history context.
- **Need-based fragment loading**: sections such as `json_only`, `vision_grounding`, and `history_context` are requested at the call site instead of being duplicated wholesale across every prompt file.
- **Explicit runtime settings**: `RuntimeSettings` now carries system-prompt defaults and escalation thresholds so pipeline behavior is no longer controlled only by scattered literals.
- **Pipeline propagation is active**: claim parsing, image review, holistic review, and escalation now receive prompt/runtime dependencies through the claim-processing context.

---

## 3. Deep-Dive Code Review: Gaps & Identified Risks

Through a comprehensive review of the code developed across Phases 1-4, the following gaps have been analyzed:

### 3.0 Verified operational fixes landed during review
- **Resumable runner correctness**: `src/batch_runner.py` now checkpoints by full claim identity (`user_id + claim_object + image_paths + user_claim`) instead of `user_id` alone, with `code/main.py` acting as a thin wrapper. This prevents false skips on `dataset/claims.csv`, which contains repeated users across different claims.
- **Telemetry and cost accounting**: top-level telemetry now records per-row adapter deltas rather than cumulative totals, so Phase 5 cost and token reporting can be trusted.
- **Cache write safety**: `src/telemetry/caching.py` now writes cache files atomically and deletes corrupt entries on read failure, which is necessary before introducing real overlap or concurrency.

### 3.1 Pipeline Concurrency and Latency (High Priority for Phase 5)
- **Problem**: Claims and images are still processed sequentially inside [strategy_staged.py](file:///code/src/pipeline/strategy_staged.py). The batch runner is now reusable, but the per-claim image loop remains single-threaded, so remote multimodal review still pays full serialized latency.
- **Resolution**: Phase 5 should introduce request-level concurrency for per-claim image review or worker-level claim execution, capped by `config.max_concurrent_requests`, once the live-model behavior is stable.

### 3.2 Robustness of Mismatch Heuristics
- **Problem**: The aggregator [aggregation.py](file:///code/src/pipeline/aggregation.py) flags `wrong_object_part` if the claimed part is not visible. If an image is usable but shows a different part, it is flagged as a risk, which is correct. However, if the user submits multiple images and only one shows the correct part while others show different parts, the current aggregator may flag `wrong_object_part` for the whole claim because it aggregates via `any(...)` mismatch.
- **Resolution**: Mismatch checks should be refined. If at least one image successfully shows the correct part, we should verify the claim on that image and treat mismatching images as auxiliary context rather than marking the entire claim invalid.

### 3.3 Natural Sorting of Supporting Image IDs
- **Problem**: In [schemas.py](file:///code/src/schemas.py) line 172, `_image_id_sort_key` parses numbers at the end of stems. If image IDs are named non-canonically (e.g., `image_abc_v2` or UUIDs), the regex `^(.*?)(\d+)$` might not extract prefix/number correctly, falling back to lexicographical sorting.
- **Resolution**: While sufficient for the expected hackathon input (`img_1`, `img_2`), adding a try-except block or a robust natural sort fallback ensures it never crashes.

### 3.4 Fuzzy-Matching Logic on Requirements
- **Problem**: In [csv_io.py](file:///code/src/csv_io.py) line 118, filtering requirements uses a substring check: `if issue_family.lower() in applies or applies in issue_family.lower()`. This can match unintended requirements if name tokens overlap.
- **Resolution**: While requirements in `evidence_requirements.csv` are relatively sparse, explicit exact matching or category-based mapping is more robust.

### 3.5 Provider Default Alignment
- **Problem**: `Config.openai_compatible_stage2_model` still defaults to `gpt-4o-mini`, which is not fully aligned with the qwen-first local Stage 2 contract described elsewhere in the repo.
- **Resolution**: Either make the qwen default explicit for local runs or document the OpenAI-compatible path as a separate hosted fallback so the runtime defaults and architecture notes stay in sync.

---

## 4. Next Phase: Scale and Throughput Strategy (Phase 5)

To address the latency, cost, and reliability gaps, the next phase will operationalize the system:
1. **Caching Layer (`src/telemetry/caching.py`)**: Key model calls by input text + image hashes, bypassing LLM execution on identical reruns.
2. **Telemetry Tracker (`src/telemetry/events.py`, `costing.py`)**: Log token usage, latency, and cost dynamically to report detailed pipeline economics.
3. **Resumable Batch Output (`src/batch_runner.py`)**: Read existing target CSV paths to skip already processed claims on resume, ensuring safety from aborts.

## 5. Current State After Review

- The system is now operationally safer than the earlier Phase 5 snapshot: tests pass, cache warm-reruns work, and resume behavior is correct for repeated users.
- The first modularization slice is now in place: single-claim processing no longer lives only inside the CLI entrypoint; it is available as an importable application service.
- Packaging friction is lower than before: `evaluation/metrics.py` no longer mutates `sys.path`, and standalone scripts use fallback bootstrapping only when needed.
- Claim processing is less file-bound than before: the service layer now depends on repository interfaces for history and evidence requirements rather than concrete CSV manager classes.
- Runtime infrastructure is less local-only than before: cache, telemetry, and cost tracking can now be injected behind protocols instead of being hard-coded file-backed classes.
- Prompt and behavior configuration are less ad hoc than before: prompt sourcing and escalation settings are now explicit dependencies rather than local file reads and hard-coded thresholds inside pipeline modules.
- Model transport is standardized across providers: the OpenAI-compatible adapter now normalizes local and remote chat-completions calls so the same request shape can target Ollama or a compatible hosted endpoint.
- Batch transport is now reusable: the same batch path can be called from the CLI or from imported code, and it has been validated end to end against the required output contract.
- Verified contract status: mock runs successfully generated `20/20` sample rows and `44/44` test rows with exact required columns, and the evaluation runner successfully consumed the generated sample predictions.
- The main blocker is no longer basic plumbing; it is prediction quality. The checked-in Strategy B evaluation report currently shows `0/20` exact matches on the labeled sample set.
- The highest-leverage next work is in prompt quality, mismatch handling, and adjudication quality, not more infrastructure expansion.
