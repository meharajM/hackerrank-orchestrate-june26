# Phase 3: Evidence Understanding Components

## Goal

Build the structured reasoning components that understand claim text and inspect images without jumping straight to final repo outputs.

## Agent Mission

Implement Stage 1 and the core of Stage 2:
claim parsing, image loading, image-quality checks, and per-image structured evidence extraction.

## Why This Phase Exists

High-performing final predictions depend on strong intermediate observations. This phase makes the system see the same row through multiple structured lenses before adjudication.

## Files To Read Before Starting

1. `dataset/sample_claims.csv`
2. `dataset/evidence_requirements.csv`
3. `dataset/user_history.csv`
4. `plans/phase-02-evaluation.md`

## Files To Create Or Edit

1. `code/src/prompts/claim_parser.md`
2. `code/src/prompts/image_reviewer.md`
3. `code/src/prompts/holistic_reviewer.md`
4. `code/src/models/base.py`
5. `code/src/models/gemini_adapter.py`
6. `code/src/models/ollama_adapter.py`
7. `code/src/models/mock_adapter.py`
8. `code/src/pipeline/claim_parser.py`
9. `code/src/pipeline/image_quality.py`
10. `code/src/pipeline/image_reviewer.py`
11. `code/src/utils/text.py`
12. `code/src/utils/retry.py`

## Python Stack For This Phase

1. `python3`
2. provider SDKs or `httpx`
3. `pydantic`
4. `Pillow`
5. optional `opencv-python`
6. `Ollama` for local `gemma4:e4b` fallback

## Implementation Steps

1. Define intermediate schemas for:
   parsed claim target, language notes, instruction-like text flags, image quality findings, part visibility, observed issue candidates, and confidence markers.
2. Build a provider-agnostic model interface for:
   text-only structured calls and multimodal structured calls.
3. Implement Stage 1 claim parsing with the selected no-spend model path first.
4. Write a claim-parser prompt that extracts:
   primary part, issue hypothesis, secondary targets, multilingual notes, and manipulation cues.
5. Implement Stage 2 primary evidence review with the chosen free or local model path.
6. Write an image-review prompt that runs per image and extracts:
   object presence, relevant part visibility, issue observations, severity hints, quality defects, mismatch cues, and usable-image status.
7. Add a lightweight image-quality module for:
   blur, glare, darkness, and obvious unreadability checks before or alongside the model.
8. Add prompt hardening for:
   in-claim instruction text and image text that tries to manipulate the reviewer.
9. Create an adapter test harness that can swap providers with the same intermediate schema contract.
10. Implement the hosted no-spend path and local fallback path behind the same adapter interface.
11. Run the components on a labeled subset and inspect failures before wiring them into final adjudication.
12. Add mock adapter tests that validate schema contracts without live provider credentials.
13. Make live Gemini smoke tests credential-dependent and skippable when `GEMINI_API_KEY` is absent.
14. Implement the local adapter through Ollama and model `gemma4:e4b`.
15. Use the Google Gen AI SDK package `google-genai` for hosted Gemini calls.

## Deliverables

1. Stage 1 claim parser module.
2. Stage 2 per-image reviewer module.
3. Image-quality precheck module.
4. Structured intermediate outputs saved for representative rows.

## Agent Notes

1. Do not emit final repo rows in this phase.
2. Every model result must parse into `pydantic` objects before use.
3. Make confidence and ambiguity explicit fields, because Stage 3 escalation will depend on them.
4. Include a field that explains why escalation might be needed:
   mismatch, ambiguity, weak part visibility, multilingual complexity, or conflicting images.

## Verification Gate

Phase 3 is complete only if all of the following are true:

1. Claim parsing returns schema-valid structured outputs on a representative sample set.
2. Per-image review returns schema-valid outputs for every image in the sample set.
3. Provider adapters can be swapped without changing downstream parsing logic.
4. At least one multilingual case and one instruction-like case are handled intentionally.

## Required Evidence To Capture

1. Saved intermediate JSON outputs for representative rows.
2. A prompt/version registry entry for each active component.
3. Example failures categorized by parser failure, image-review failure, and image-quality failure.

## Risks

1. Free-form reasoning text will become untestable and brittle.
2. A single holistic prompt may miss cross-image contradictions or part-level visibility issues.
3. Without provider abstraction, later optimization will require large rewrites.

## Locked Defaults

1. Make Gemini free tier the first real hosted integration target.
2. Use OCR-style preprocessing only as fallback support.
3. Delay Gemini escalation tuning until the staged primary pipeline is stable.
4. Do not implement Anthropic in this phase.
5. Do not implement OpenAI in this phase.
6. Use Ollama as the concrete local runtime and `gemma4:e4b` as the concrete local model.

## Slices

### Slice 3.1: Intermediate schemas

Scope:
define claim-parse, image-observation, confidence, and escalation-candidate schemas.

Verification:
schema tests cover representative valid and invalid payloads.

### Slice 3.2: Adapter base and Gemini hosted adapter

Scope:
implement `models/base.py`, `models/mock_adapter.py`, and the Gemini adapter for structured text and image calls.

Verification:
mock adapter tests pass without credentials, and the Gemini adapter can perform one text-only and one image-enabled schema-valid call when `GEMINI_API_KEY` is set.

### Slice 3.3: Claim parser module

Scope:
implement prompt plus parser module for Stage 1.

Verification:
sample subset produces structured claim-parse outputs.

### Slice 3.4: Image quality prechecks

Scope:
implement blur, glare, darkness, and load-error checks.

Verification:
precheck outputs are generated for a sample subset.

### Slice 3.5: Per-image reviewer module

Scope:
implement Stage 2 per-image review on the Gemini hosted path.

Verification:
all sample images return schema-valid observation objects.

### Slice 3.6: Local Gemma adapter

Scope:
implement `models/ollama_adapter.py` behind the same interface, targeting local model `gemma4:e4b`.

Verification:
one sample subset can run through Ollama `gemma4:e4b` and return schema-valid observations.
If Ollama is missing or the model is not pulled, the adapter must fail with the exact setup command needed.

### Slice 3.7: Escalation-candidate signals

Scope:
add explicit ambiguity, mismatch, and weak-evidence fields needed by Stage 3.

Verification:
saved intermediate outputs include escalation reasons.

## Phase Command Targets

1. Run Stage 1 parsing on a sample subset and save structured outputs.
2. Run Stage 2 per-image review on a sample subset and save structured outputs.

Use venv command forms from `plan.md`.
Live provider smoke tests must be skipped, not failed, when required environment variables are missing.

## Exit Criteria

Do not start Phase 4 until intermediate outputs are stable enough that adjudication bugs are distinguishable from extraction bugs.
