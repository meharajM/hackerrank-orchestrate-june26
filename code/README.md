# Multimodal Claims Review Solution

This directory contains the runnable solution for the HackerRank Orchestrate multimodal evidence review challenge.

## Setup

Run from the repository root on macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r code/requirements.txt
.venv/bin/python -m pip install -e ./code

export GEMINI_API_KEY="your-google-ai-studio-api-key"

if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

bash scripts/bootstrap_and_run.sh
```

Optional local-model overrides:

```bash
export OLLAMA_MODEL="qwen3-vl:4b"
export OLLAMA_STAGE2_MODEL="qwen3-vl:4b"
export OLLAMA_BASE_URL="http://localhost:11434"
```

`OLLAMA_MODEL` remains the base local adapter for text-first and holistic Ollama runs.
`OLLAMA_STAGE2_MODEL` is the dedicated local image-review model used by Strategy `B` and the provisional stage inside Strategy `C`; the default is `qwen3-vl:4b`.
The local Ollama path now uses Ollama's OpenAI-compatible `/v1/chat/completions` surface, so the same adapter shape can be reused with other OpenAI-compatible endpoints later.
If the requested Stage 2 model is unavailable on the current machine, the bootstrap flow falls back to a locally usable multimodal model such as `llava` or `moondream`.
If no local multimodal runner can stay resident on the machine, the bootstrap script finishes with a mock smoke test so setup still completes end to end.
If a local multimodal model is slow but healthy, raise `OLLAMA_MULTIMODAL_TIMEOUT` above the default `300` seconds for Stage 2 validation runs.

## Provider Policy

- Primary hosted path: Gemini Developer API through `google-genai`.
- Stage 3 escalation: Gemini re-review only, gated to hard rows.
- Local base adapter: Ollama model `qwen3-vl:4b`.
- Local Stage 2 reviewer: Ollama model `qwen3-vl:4b`.
- Direct paid API spend defaults to zero.
- If `GEMINI_API_KEY` or free-tier quota is unavailable, the pipeline must still produce schema-valid rows by disabling hosted calls or using the local fallback where available.

## Commands

Final command targets:

```bash
.venv/bin/python code/main.py --input dataset/claims.csv --output output.csv
.venv/bin/python code/evaluation/main.py --predictions <sample_predictions.csv> --gold dataset/sample_claims.csv
.venv/bin/python -m pytest code/tests
scripts/run_local_ollama_eval.sh
```

## Local Evaluation Workflow

Use the local operator script when Gemini is unavailable and you want a real multimodal sample pass instead of the mock adapter:

```bash
chmod +x scripts/run_local_ollama_eval.sh
OLLAMA_MODEL=qwen3-vl:4b OLLAMA_STAGE2_MODEL=qwen3-vl:4b scripts/run_local_ollama_eval.sh
```

This script:

1. prefers the Homebrew Ollama client on macOS and stops a legacy `Ollama.app` server if it is holding the port
2. starts a fresh Ollama server only when the API endpoint is unavailable
3. pulls the base local model if missing
4. pulls the requested Stage 2 local vision model if missing
5. falls back to the first usable multimodal Stage 2 model if the requested one cannot be pulled
6. checks that the selected Stage 2 model actually accepts image input through Ollama
7. runs `code/evaluation/main.py` on `dataset/sample_claims.csv` with `--model ollama --strategy B`
8. writes local-model artifacts to:
   `code/evaluation/evaluation_report.local-ollama.md`
  `code/evaluation/metrics.local-ollama.json`
  `code/evaluation/experiments.local-ollama.json`

## Stage 2 Harness

Use the Stage 2 harness when you want claim-by-claim inspection of parsed claim facts, per-image observations, aggregated evidence, and provisional outputs before running the full sample metrics pass:

```bash
chmod +x scripts/run_stage2_harness.sh
scripts/run_stage2_harness.sh
```

This command writes intermediate JSON dumps under `code/evaluation/stage2_local_intermediate/`.
By default it targets `qwen3-vl:4b` for both the base local adapter and the Stage 2 reviewer; override `OLLAMA_MODEL` or `OLLAMA_STAGE2_MODEL` only when the current machine requires a different local model split.
Each file contains:

1. the raw claim row
2. the Stage 1 parsed claim
3. the Stage 2 per-image observations
4. aggregated evidence
5. the provisional Strategy B output

Harness dump filenames include the batch position plus `user_id`, for example `claim_001_user_001.json`, so repeated users do not overwrite each other.

## Fresh Machine Bootstrap

Use the bootstrap skill and script when cloning this repo onto a new machine or judge environment:

```bash
bash scripts/bootstrap_and_run.sh
```

This command:

1. checks `python3`, `curl`, and `ollama`
2. creates `.venv` if needed
3. upgrades `pip`
4. installs `code/requirements.txt`
5. installs `code/` in editable mode
6. starts or installs Ollama when missing
7. verifies the selected multimodal model can read a real sample image
8. runs sample inference and sample evaluation
9. prints the generated output file paths

If the dedicated Stage 2 model cannot be used on the current machine, the script may fall back to a local multimodal model for bootstrap verification only. The final local default remains `qwen3-vl:4b`.
Set `BOOTSTRAP_STAGE2_FALLBACK_MODELS` if you want to change the local Stage 2 fallback list.

The implementation phases in `../plan.md` define the exact behavior each command must support.

## Library Usage

The solution can now be imported as a reusable library after editable install:

```bash
.venv/bin/python -m pip install -e ./code
```

Example:

```python
from src import build_claim_processing_context, process_claim
from src.csv_io import read_claims
from src.config import get_config

config = get_config()
claim = read_claims(config.sample_claims_csv)[0]
context = build_claim_processing_context(
    config=config,
    model_name="mock",
    strategy="B",
    cache_enabled=False,
)
result = process_claim(claim, context)
print(result.output.to_row_dict())
```

This keeps the CLI entrypoints available while allowing single-claim and batch processing from other Python modules or hosted services.

## Prompt Harness

Prompt assembly is now modular rather than one large repeated blob:

- `code/src/prompts/_shared/core_security.md` is always injected
- stage-specific sections such as `json_only`, `vision_grounding`, and `history_context` are loaded only when the current stage needs them
- task prompts stay in their own files under `code/src/prompts/`

This keeps prompt-injection defenses and output-discipline rules consistent while reducing repeated context across Stage 1, Stage 2, and holistic review calls.

## Packaging

Include this directory in `code.zip`.

Do not include:

- `.venv`
- `.env`
- API keys or secrets
- Ollama model files
- generated caches
- provider response dumps
- large experiment artifacts
