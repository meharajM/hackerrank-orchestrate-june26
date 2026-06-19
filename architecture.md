# System Architecture: HackerRank Orchestrate Claims Verification

This document provides a deep architectural analysis of the claims verification system built so far. It outlines the design patterns, data flow, component boundaries, the Phase 5 operational work that is now in place, and the remaining gaps blocking submission quality.

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
│   (Lightweight Pillow precheck + Multimodal review)    │
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
- **OllamaAdapter**: Leverages local HTTP requests (`httpx`) to communicate with a local Ollama server running lightweight open models (`gemma4:e4b`).
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
- **Reusable context object**: `ClaimProcessingContext` packages dataset location, models, repositories, cache, telemetry, and cost tracking so the same runtime can be shared across CLI, tests, and future hosted services.
- **Builder entrypoint**: `build_claim_processing_context(...)` centralizes dependency wiring, reducing the amount of orchestration logic left inside `code/main.py`.
- **Public package surface**: `src/__init__.py` now exports the core claim-processing entrypoints for import-based consumers.
- **Installable distribution metadata**: `code/pyproject.toml` now defines an editable-install path for the current `src` and `evaluation` packages, which reduces reliance on ad hoc path bootstrapping.

### 2.5 Repository Abstractions (`src/history.py`, `src/requirements.py`)
- **History repository interface**: claim processing now depends on a `HistoryRepository` protocol instead of assuming CSV-backed history lookups.
- **Requirements repository interface**: evidence lookup now depends on a `RequirementsRepository` protocol rather than directly binding orchestration to a local file loader.
- **File-backed defaults remain**: `FileHistoryRepository` and `FileRequirementsRepository` preserve current repo behavior while making hosted backends and test doubles injectable.

---

## 3. Deep-Dive Code Review: Gaps & Identified Risks

Through a comprehensive review of the code developed across Phases 1-4, the following gaps have been analyzed:

### 3.0 Verified operational fixes landed during review
- **Resumable runner correctness**: `code/main.py` now checkpoints by full claim identity (`user_id + claim_object + image_paths + user_claim`) instead of `user_id` alone. This prevents false skips on `dataset/claims.csv`, which contains repeated users across different claims.
- **Telemetry and cost accounting**: top-level telemetry now records per-row adapter deltas rather than cumulative totals, so Phase 5 cost and token reporting can be trusted.
- **Cache write safety**: `src/telemetry/caching.py` now writes cache files atomically and deletes corrupt entries on read failure, which is necessary before introducing real overlap or concurrency.

### 3.1 Pipeline Concurrency and Latency (High Priority for Phase 5)
- **Problem**: Claims and images are currently processed sequentially in loops inside [main.py](file:///code/main.py) and [strategy_staged.py](file:///code/src/pipeline/strategy_staged.py). When executing with remote APIs (Gemini), a sequential loop will result in substantial latency (e.g., 20 claims with multiple images will take over a minute).
- **Resolution**: Phase 5 should introduce request-level concurrency (using python's `ThreadPoolExecutor` or `asyncio` for model adapter calls) capped by `config.max_concurrent_requests` to speed up runtime.

### 3.2 Robustness of Mismatch Heuristics
- **Problem**: The aggregator [aggregation.py](file:///code/src/pipeline/aggregation.py) flags `wrong_object_part` if the claimed part is not visible. If an image is usable but shows a different part, it is flagged as a risk, which is correct. However, if the user submits multiple images and only one shows the correct part while others show different parts, the current aggregator may flag `wrong_object_part` for the whole claim because it aggregates via `any(...)` mismatch.
- **Resolution**: Mismatch checks should be refined. If at least one image successfully shows the correct part, we should verify the claim on that image and treat mismatching images as auxiliary context rather than marking the entire claim invalid.

### 3.3 Natural Sorting of Supporting Image IDs
- **Problem**: In [schemas.py](file:///code/src/schemas.py) line 172, `_image_id_sort_key` parses numbers at the end of stems. If image IDs are named non-canonically (e.g., `image_abc_v2` or UUIDs), the regex `^(.*?)(\d+)$` might not extract prefix/number correctly, falling back to lexicographical sorting.
- **Resolution**: While sufficient for the expected hackathon input (`img_1`, `img_2`), adding a try-except block or a robust natural sort fallback ensures it never crashes.

### 3.4 Fuzzy-Matching Logic on Requirements
- **Problem**: In [csv_io.py](file:///code/src/csv_io.py) line 118, filtering requirements uses a substring check: `if issue_family.lower() in applies or applies in issue_family.lower()`. This can match unintended requirements if name tokens overlap.
- **Resolution**: While requirements in `evidence_requirements.csv` are relatively sparse, explicit exact matching or category-based mapping is more robust.

---

## 4. Next Phase: Scale and Throughput Strategy (Phase 5)

To address the latency, cost, and reliability gaps, the next phase will operationalize the system:
1. **Caching Layer (`src/telemetry/caching.py`)**: Key model calls by input text + image hashes, bypassing LLM execution on identical reruns.
2. **Telemetry Tracker (`src/telemetry/events.py`, `costing.py`)**: Log token usage, latency, and cost dynamically to report detailed pipeline economics.
3. **Resumable Batch Output (`main.py`)**: Read existing target CSV paths to skip already processed claims on resume, ensuring safety from aborts.

## 5. Current State After Review

- The system is now operationally safer than the earlier Phase 5 snapshot: tests pass, cache warm-reruns work, and resume behavior is correct for repeated users.
- The first modularization slice is now in place: single-claim processing no longer lives only inside the CLI entrypoint; it is available as an importable application service.
- Packaging friction is lower than before: `evaluation/metrics.py` no longer mutates `sys.path`, and standalone scripts use fallback bootstrapping only when needed.
- Claim processing is less file-bound than before: the service layer now depends on repository interfaces for history and evidence requirements rather than concrete CSV manager classes.
- The main blocker is no longer basic plumbing; it is prediction quality. The checked-in Strategy B evaluation report currently shows `0/20` exact matches on the labeled sample set.
- The highest-leverage next work is in prompt quality, mismatch handling, and adjudication quality, not more infrastructure expansion.
