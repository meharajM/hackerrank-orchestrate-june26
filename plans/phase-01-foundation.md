# Phase 1: Foundation And Contracts

## Goal

Create the non-negotiable foundation so every later phase builds on strict contracts instead of ad hoc scripts.

## Status

Complete. The foundation smoke run and the contract tests both passed after the Phase 1 implementation was validated.

## Agent Mission

Build the Python project skeleton, schema layer, data loaders, and smoke path so later coding agents can work without rediscovering repo constraints.

## Why This Phase Exists

This repo can be lost before model quality becomes relevant if the pipeline mishandles CSV parsing, image paths, enums, or output order. Phase 1 removes those failure modes first.

## Files To Read Before Starting

1. `AGENTS.md`
2. `README.md`
3. `problem_statement.md`
4. `dataset/sample_claims.csv`
5. `dataset/claims.csv`
6. `dataset/user_history.csv`
7. `dataset/evidence_requirements.csv`

## Files To Create Or Edit

1. `code/main.py`
2. `code/src/config.py`
3. `code/src/schemas.py`
4. `code/src/csv_io.py`
5. `code/src/image_io.py`
6. `code/src/history.py`
7. `code/src/requirements.py`
8. `code/requirements.txt`
9. `code/tests/test_schemas.py`
10. `code/tests/test_pipeline_smoke.py`
11. `code/README.md`

## Python Stack For This Phase

1. `python3`
2. `pydantic`
3. `pytest`
4. `Pillow`
5. `csv` or `pandas`

## Implementation Steps

1. Create a canonical schema layer for:
   input rows, history rows, evidence requirement rows, intermediate outputs, and final output rows.
2. Encode all repo enums in one place and validate:
   `claim_status`, `issue_type`, `object_part`, `risk_flags`, and `severity`.
3. Build CSV readers using the standard library or a stable tabular library.
4. Build path-resolution utilities so all `image_paths` are converted to absolute local paths safely.
5. Build image-loading helpers that:
   verify file existence, record dimensions, and return structured load errors.
6. Build lookup loaders for:
   `user_history.csv` keyed by `user_id`, and `evidence_requirements.csv` keyed by object and rule family.
7. Create a minimal `code/main.py` that:
   loads `dataset/claims.csv`, resolves image paths, emits placeholder structured rows, and writes schema-valid output.
8. Create `code/requirements.txt` with only the dependencies needed for the current implemented code.
9. Add tests that fail on:
   missing columns, wrong column order, invalid enums, and missing files.
10. Document how to run the foundation smoke path in `code/README.md`.
11. Include the judge setup commands in `code/README.md`:
   Python venv, dependency install, `GEMINI_API_KEY`, Ollama install, and `ollama pull qwen3-vl:4b`.

## Deliverables

1. A Python package layout under `code/src/`.
2. Canonical enums and output-column order in one place only.
3. A smoke command that reads inputs and writes a schema-valid placeholder output.
4. Tests that prove contract failures are caught.

## Agent Notes

1. Keep provider logic out of this phase.
2. Do not guess final prompt shapes yet.
3. Make schema classes granular enough for later staged outputs:
   claim parse result, image observation, aggregated evidence, escalation request, final row.

## Verification Gate

Phase 1 is complete only if all of the following are true:

1. A smoke run reads all repo CSV files without parser errors.
2. Image-path resolution succeeds for every row in `dataset/sample_claims.csv` and `dataset/claims.csv`.
3. The pipeline can write a schema-valid CSV with the exact required output columns in the exact order.
4. Contract tests fail when a required enum or column is intentionally broken.

## Required Evidence To Capture

1. Row counts for all four CSV files.
2. Image-count distribution for sample and test rows.
3. A generated schema-valid dummy output file for a small sample run.
4. Test results proving the schema guardrails work.

## Risks

1. Naive CSV parsing will break on multiline claim transcripts.
2. Image-path handling may silently fail if relative paths are resolved inconsistently.
3. Duplicating enum definitions across files will cause drift later.

## Locked Defaults

1. Use `pydantic` as the schema foundation.
2. Use `pytest` as the default test runner.
3. Use `python3` and venv-based commands:
   `python3 -m venv .venv`,
   `.venv/bin/python -m pip install -r code/requirements.txt`,
   and `.venv/bin/python -m pytest code/tests`.
4. `code/requirements.txt` must include at minimum:
   `google-genai`, `pydantic`, `pytest`, and `Pillow` once provider code is implemented.

## Slices

### Slice 1.1: Project skeleton

Scope:
create `code/src/`, `code/tests/`, and minimal module files.

Verification:
repo contains the expected package layout.

Command:
after creating the skeleton and dependency file, the venv setup command must complete:
`.venv/bin/python -m pip install -r code/requirements.txt`.

### Slice 1.2: Canonical enums and schemas

Scope:
implement `schemas.py` with input, intermediate, and final row models plus canonical enum sets.

Verification:
schema tests pass for valid and invalid enum values.

Required details:
booleans serialize as `true`/`false`, `risk_flags` serialize in canonical problem-statement order, and `supporting_image_ids` serialize as deterministic filename stems.

### Slice 1.3: CSV and path loaders

Scope:
implement `csv_io.py`, `history.py`, `requirements.py`, and path resolution in `image_io.py`.

Verification:
a smoke command can read all repo CSV files and resolve all image paths.

### Slice 1.4: Placeholder output writer

Scope:
implement a minimal `code/main.py` that writes schema-valid placeholder predictions.

Verification:
generated output has exact required columns in exact order.

### Slice 1.5: Contract tests and README

Scope:
add `pytest` smoke and schema tests plus run instructions in `code/README.md`.

Verification:
test command passes and README documents the smoke path.

## Phase Command Targets

1. Foundation smoke run:
   a command that loads all repo data and writes a valid placeholder CSV.
2. Contract test run:
   a command that runs schema and smoke tests.

Use these command forms:

1. `python3 -m venv .venv`
2. `.venv/bin/python -m pip install -r code/requirements.txt`
3. `.venv/bin/python code/main.py --input dataset/claims.csv --output output.csv`
4. `.venv/bin/python -m pytest code/tests`

## Exit Criteria

Do not start Phase 2 until this phase can be rerun from a clean checkout and produce the same smoke result.
