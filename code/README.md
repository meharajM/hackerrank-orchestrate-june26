# Multimodal Claims Review Solution

This directory contains the runnable solution for the HackerRank Orchestrate multimodal evidence review challenge.

## Setup

Run from the repository root on macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r code/requirements.txt

export GEMINI_API_KEY="your-google-ai-studio-api-key"

if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

ollama list >/dev/null 2>&1 || (ollama serve >/tmp/ollama.log 2>&1 & sleep 3)
ollama pull gemma4:e4b
ollama run gemma4:e4b ""
```

## Provider Policy

- Primary hosted path: Gemini Developer API through `google-genai`.
- Stage 3 escalation: Gemini re-review only, gated to hard rows.
- Local fallback and benchmark: Ollama model `gemma4:e4b`.
- Direct paid API spend defaults to zero.
- If `GEMINI_API_KEY` or free-tier quota is unavailable, the pipeline must still produce schema-valid rows by disabling hosted calls or using the local fallback where available.

## Commands

Final command targets:

```bash
.venv/bin/python code/main.py --input dataset/claims.csv --output output.csv
.venv/bin/python code/evaluation/main.py --predictions <sample_predictions.csv> --gold dataset/sample_claims.csv
.venv/bin/python -m pytest code/tests
```

The implementation phases in `../plan.md` define the exact behavior each command must support.

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
