---
name: project-bootstrap
description: Bootstraps this repo on a fresh machine, checks prerequisites, installs missing dependencies, and runs a sample project startup flow. Use when cloning the repo to a new machine, verifying Python/Ollama setup, or reproducing the project end to end with visible status output.
---

# Project Bootstrap

## Quick Start

Run the bootstrap script from the repo root:

```bash
chmod +x scripts/bootstrap_and_run.sh
./scripts/bootstrap_and_run.sh
```

## Workflow

1. Check the machine first.
   Confirm `python3` is available.
   Confirm `ollama` is installed or install it if missing.
   Prefer the Homebrew Ollama binary on macOS and restart the daemon if an older `Ollama.app` server is holding port `11434`.

2. Create the Python environment.
   Make `.venv` if missing.
   Upgrade `pip`.
   Install `code/requirements.txt`.
   Install `code/` in editable mode so imports work like a library.
   Keep the install output visible so a fresh machine shows progress and failures.

3. Select a usable local model.
   Prefer `OLLAMA_MODEL` for the base local adapter when supplied.
   Prefer `OLLAMA_STAGE2_MODEL` for the image-review model when supplied.
   Default the base adapter to `qwen3-vl:4b` for the repo contract.
   Default the dedicated Stage 2 reviewer to `qwen3-vl:4b`.
   If the Stage 2 target cannot be used on this machine, fall back to a smaller local multimodal model first.
   If no multimodal runner stays resident, complete the bootstrap with the mock adapter as a smoke test and say so explicitly.

4. Preflight multimodal support.
   Send a tiny image request to Ollama before running the full flow.
   Fail fast if the selected model cannot accept images.
   Skip the preflight when the bootstrap is already using the mock fallback.

5. Show project output.
   Run sample inference on `dataset/sample_claims.csv`.
   Run sample evaluation and print the generated report paths.
   Prefer a dynamic sample-image preflight so the check works across dataset revisions.

## Operator Notes

- Keep the final repo default as `qwen3-vl:4b`.
- Use fallback multimodal models only to get local Stage 2 development started on machines where `qwen3-vl:4b` cannot be pulled yet.
- For judge readiness, report any environment gap instead of silently changing the frozen default.
- The bootstrap smoke test can finish on `mock`, but that does not replace the real local or hosted provider path for actual predictions.

## Useful Files

- [scripts/bootstrap_and_run.sh](/Users/meharaj/hackerrank-orchestrate-june26/scripts/bootstrap_and_run.sh)
- [code/README.md](/Users/meharaj/hackerrank-orchestrate-june26/code/README.md)
- [plan.md](/Users/meharaj/hackerrank-orchestrate-june26/plan.md)
