# HackerRank Orchestrate

Starter repository for the **HackerRank Orchestrate** 24-hour hackathon.

Build a system that verifies visual evidence for damage claims across three object types: **cars**, **laptops**, and **packages**.

Your system will receive claim conversations, one or more submitted images, user claim history, and minimum evidence requirements. It must decide whether the submitted images support the claim, contradict it, or do not provide enough information.

Read [`problem_statement.md`](./problem_statement.md) for the full task spec, input/output schema, and allowed values.

---

## Contents

1. [Repository layout](#repository-layout)
2. [What you need to build](#what-you-need-to-build)
3. [Where your code goes](#where-your-code-goes)
4. [Quickstart](#quickstart)
5. [Mac/Linux setup](#maclinux-setup)
6. [Evaluation](#evaluation)
7. [Chat transcript logging](#chat-transcript-logging)
8. [Submission](#submission)
9. [Judge interview](#judge-interview)

---

## Repository layout

```text
.
├── AGENTS.md                         # Rules for AI coding tools + transcript logging
├── problem_statement.md              # Full task description and I/O schema
├── README.md                         # You are here
├── code/                             # Build your solution here
│   ├── main.py                       # Suggested terminal entry point
│   └── evaluation/
│       └── main.py                   # Suggested evaluation entry point
└── dataset/
    ├── sample_claims.csv             # Inputs + expected outputs for development
    ├── claims.csv                    # Inputs only; run your system on these rows
    ├── user_history.csv              # Historical claim counts and risk context
    ├── evidence_requirements.csv     # Minimum image evidence requirements
    └── images/
        ├── sample/                   # Images referenced by sample_claims.csv
        └── test/                     # Images referenced by claims.csv
```

---

## What you need to build

A system that, for each row in `dataset/claims.csv`, produces one row in `output.csv`.

Input fields:

| Column | Meaning |
|---|---|
| `user_id` | User submitting the claim; use this to look up `dataset/user_history.csv` |
| `image_paths` | One or more submitted image paths, separated by semicolons |
| `user_claim` | Chat transcript describing the issue |
| `claim_object` | `car`, `laptop`, or `package` |

Required output fields:

| Column | Meaning |
|---|---|
| `evidence_standard_met` | Whether the image set is sufficient to evaluate the claim |
| `evidence_standard_met_reason` | Short reason for the evidence decision |
| `risk_flags` | Semicolon-separated risk flags, or `none` |
| `issue_type` | Visible issue type |
| `object_part` | Relevant object part |
| `claim_status` | `supported`, `contradicted`, or `not_enough_information` |
| `claim_status_justification` | Concise explanation grounded in the image evidence |
| `supporting_image_ids` | Image IDs supporting the decision, or `none` |
| `valid_image` | Whether the image set is usable for automated review |
| `severity` | `none`, `low`, `medium`, `high`, or `unknown` |

Hard requirements:

- Must read the provided CSV files and local images.
- Must produce `output.csv` with the exact schema in `problem_statement.md`.
- Must include an evaluation workflow
- Must avoid hardcoded test labels or file-specific answers.

Beyond that you are free to bring your own approach: VLMs, LLMs, structured prompting, rule layers, batching, caching, evaluation pipelines, model comparison, or anything else.

---

## Where your code goes

All of your work belongs in [`code/`](./code/). The repo ships with empty starter files that you can grow into your full solution.

Suggested conventions:

- Put your main runnable solution in `code/main.py`, or document your own entry point clearly.
- Put evaluation code under `code/evaluation/` or an `evaluation/` folder included in your final `code.zip`.
- Write final predictions to `output.csv`.

---

## Quickstart

Clone this repository:

```bash
git clone git@github.com:interviewstreet/hackerrank-orchestrate-june26.git
cd hackerrank-orchestrate-june26
```

You are free to use any language or runtime. Python, JavaScript, and TypeScript are all reasonable choices.

---

## Mac/Linux setup

The planned solution is Python-based, with Gemini as the hosted multimodal path and Ollama `gemma4:e4b` as the local benchmark/fallback. Run this setup from the repo root:

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

Provider choices:

- Primary hosted model path: Gemini Developer API via the `google-genai` Python package.
- Stage 3 escalation: Gemini re-review only, gated to hard rows and disabled if the API key or free-tier quota is unavailable.
- Local fallback and benchmark: Ollama model `gemma4:e4b`.
- Direct paid API spend defaults to zero; report quota and cost assumptions in `code/evaluation/evaluation_report.md`.

Do not commit or submit `.env`, API keys, `.venv`, Ollama model files, generated caches, or provider response dumps.

---

## Evaluation

The evaluation report should include:

- metrics on `dataset/sample_claims.csv`
- at least two strategies, prompts, or model configurations compared
- the final strategy used for `output.csv`
- operational analysis covering model calls, token usage, image usage, approximate cost, runtime, and TPM/RPM considerations

---

## Chat transcript logging

This repo ships with an `AGENTS.md` that modern AI coding tools may read. It instructs the tool to append conversation turns to a shared log file:

| Platform | Path |
|---|---|
| macOS / Linux | `$HOME/hackerrank_orchestrate/log.txt` |
| Windows | `%USERPROFILE%\hackerrank_orchestrate\log.txt` |

You will upload this log as your chat transcript at submission time. The chat transcript means your conversation with the AI coding tool you used to build the system. It is not the runtime logs, reasoning trace, or conversation history produced by the claim-verification agent you are building.

If you use multiple AI tools, include the relevant conversation logs from all of them in the same transcript file. Separate each tool's section with a clear divider and label it with the tool name.

Never paste secrets into the chat. If secrets are needed, use environment variables.

---

## Submission

Submit the following files as instructed by HackerRank:

1. **Code zip**: zip your runnable solution, README, prompts/configs, and evaluation folder. Exclude virtualenvs, `node_modules`, build artifacts, and unnecessary generated files.
2. **Predictions CSV**: your final `output.csv` for all rows in `dataset/claims.csv`.
3. **Chat transcript**: the `log.txt` from the path in [Chat transcript logging](#chat-transcript-logging).

Before submitting, confirm:

- `output.csv` has one row per row in `dataset/claims.csv`.
- `output.csv` has the exact required columns in the exact required order.
- Your evaluation files are included in `code.zip`.

---

## Judge interview

After submission, the AI Judge may ask about your approach, implementation decisions, model usage, evaluation strategy, and how you used AI while building the solution.

Be prepared to explain your solution in detail.
