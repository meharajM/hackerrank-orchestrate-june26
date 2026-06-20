# Multimodal Claims Review Solution

Runnable solution for the HackerRank Orchestrate multimodal evidence review challenge.

**Frozen Strategy**: Strategy B (staged pipeline) — default production path.

## Approach Overview

Staged evidence-review pipeline for verifying damage claims from images and conversation transcripts:

1. **Stage 1 — Claim Parser**: Structured extraction (object, part, issue) from conversation via model adapter.
2. **Stage 2 — Evidence Review**: Per-image visual inspection → cross-image aggregation → deterministic adjudication (supported / contradicted / not_enough_information).
3. **Stage 3 — Escalation (optional)**: Conditional re-review on flagged rows.

Key decisions: modular adapters (mock/ollama/gemini), deterministic post-processing via Pydantic schemas, composable prompt harness with security fragments, resumable batch runner with identity-based dedup, content-addressed response caching.

## Setup

Run from the **repository root** (where `dataset/` and `code/` live):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r code/requirements.txt
```

**No API key required for mock mode** (default). For Gemini: `export GEMINI_API_KEY="your-key"`.

For local multimodal inference with Ollama:

```bash
# Install Ollama if missing
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama and pull the model
ollama list >/dev/null 2>&1 || (ollama serve >/tmp/ollama.log 2>&1 & sleep 3)
ollama pull qwen3-vl:4b
```

## Commands

```bash
# Run inference on the test set (default: mock model, Strategy B)
.venv/bin/python code/main.py --input dataset/claims.csv --output output.csv

# Run inference with specific model and strategy
.venv/bin/python code/main.py --model mock --strategy B --input dataset/claims.csv --output output.csv

# Evaluate predictions against sample labels
.venv/bin/python code/evaluation/main.py --predictions predictions.csv --gold dataset/sample_claims.csv

# Run the test suite
.venv/bin/python -m pytest code/tests
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `mock` | Adapter: `mock`, `ollama`, `gemini`, `openai_compat` |
| `AI_MODEL` | — | Model name for the chosen provider |
| `GEMINI_API_KEY` | — | Google AI Studio API key (for Gemini) |
| `OLLAMA_MODEL` | `qwen3-vl:4b` | Local base model |
| `OLLAMA_STAGE2_MODEL` | `qwen3-vl:4b` | Local Stage 2 image-review model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `AI_PROVIDER=mock` | — | Runs without any API keys |

## Library Usage

After setup, the pipeline can be imported:

```python
from src import build_claim_processing_context, process_claim
from src.csv_io import read_claims
from src.config import get_config

config = get_config()
claim = read_claims(config.sample_claims_csv)[0]
context = build_claim_processing_context(config=config, model_name="mock", strategy="B", cache_enabled=False)
result = process_claim(claim, context)
print(result.output.to_row_dict())
```

## Project Structure

```
code/
  main.py                      # CLI entry point
  requirements.txt            # Python dependencies
  README.md                   # This file
  src/                        # Core library
    config.py                 # Environment-based configuration
    schemas.py                # Pydantic output schemas
    csv_io.py                 # CSV read/write
    claim_processing.py       # Single-claim service API
    batch_runner.py           # Batch orchestration
    prompting.py              # Composable prompt harness
    runtime.py                # Runtime settings
    models/                   # Adapters: mock, ollama, gemini, openai_compat
    pipeline/                 # Stages: claim_parser, image_reviewer, aggregation, adjudication
    telemetry/                # Caching, cost tracking, event logging
    utils/                    # Shared utilities
    prompts/                  # Prompt templates and shared fragments
  evaluation/
    main.py                   # Evaluation entry point
    metrics.py                # Metric computation
    reporting.py              # Markdown report generation
    evaluation_report.md      # Final evaluation report
  tests/                      # pytest suite (82 tests)
```

## Evaluation

The system was evaluated on `dataset/sample_claims.csv` (20 rows). Results are in `code/evaluation/evaluation_report.md`.

## Packaging

`code.zip` includes this directory with runnable source, prompts, evaluation folder, README, and requirements.txt.

Excluded: `.venv`, `.env`, API keys, Ollama model files, generated caches, provider response dumps.
