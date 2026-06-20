---
name: local-multimodal-eval
description: Runs the repo's local multimodal evaluation workflow with Ollama, sample metrics, and operator checks. Use when validating local model quality, starting Ollama-backed evaluation, freezing adjudication policy, or regenerating sample evaluation artifacts.
---

# Local Multimodal Eval

## Quick start

Run from the repo root:

```bash
chmod +x scripts/run_local_ollama_eval.sh
OLLAMA_MODEL=qwen3-vl:4b OLLAMA_STAGE2_MODEL=qwen3-vl:4b scripts/run_local_ollama_eval.sh
```

If `qwen3-vl:4b` is not available locally, set `OLLAMA_STAGE2_MODEL` to another pulled multimodal model and record that override in the evaluation notes. The operator script now performs a multimodal preflight and should fail fast if the chosen Stage 2 model cannot accept image input.

## Workflow

1. Confirm the plan state before tuning.
   Phase 5 stays open until local multimodal metrics and operational evidence are captured.
   Phase 6 stays open until final `output.csv`, final report, and `code.zip` are produced.

2. Freeze adjudication policy before rerunning.
   Cross-image identity conflicts should default to `not_enough_information`.
   Visible claim-vs-image mismatches should default to `contradicted`.
   `manual_review_required` should be reserved for substantive review blockers, not every blurry image.

3. Start local evaluation.
   The script starts `ollama serve` if needed, ensures the base local model is pulled, ensures the Stage 2 local vision model is pulled, and runs sample evaluation with Strategy B.

4. Review artifacts.
   Check `code/evaluation/evaluation_report.local-ollama.md`.
   Compare exact match, `claim_status`, `issue_type`, `object_part`, `risk_flags`, and `supporting_image_ids` against the prior baseline.

4.5. Use the Stage 2 harness before broad prompt changes when a few rows are failing for unclear reasons.
   Run `scripts/run_stage2_harness.sh`.
   Inspect `code/evaluation/stage2_local_intermediate/` for parsed claims, per-image observations, aggregated evidence, and provisional outputs.

5. Only then tune prompts or rules.
   Prefer image-grounded fixes that generalize.
   Do not branch on case IDs, exact user IDs, or image paths.

## Useful commands

```bash
ollama ls
ollama ps
curl http://localhost:11434/api/tags
.venv/bin/python -m pytest code/tests -q
```

## Notes

- Model selection is env-driven through `OLLAMA_MODEL` and `OLLAMA_BASE_URL`.
- Stage 2 model selection is env-driven through `OLLAMA_STAGE2_MODEL`.
- The base local model default is `qwen3-vl:4b`; the default Stage 2 local reviewer is also `qwen3-vl:4b`.
- If you temporarily use another local Stage 2 model, update the report notes and revert the env override before final freeze.
