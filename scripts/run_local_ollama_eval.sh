#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT_DIR}/.venv/bin/python"
BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
HOST="${BASE_URL%/}"
BIND_HOST="${HOST#http://}"
BIND_HOST="${BIND_HOST#https://}"
OLLAMA_BIN="${OLLAMA_BIN:-}"
TARGET_MODEL="${OLLAMA_MODEL:-qwen3-vl:4b}"
TARGET_STAGE2_MODEL="${OLLAMA_STAGE2_MODEL:-qwen3-vl:4b}"
FALLBACK_MODELS="${OLLAMA_FALLBACK_MODELS:-qwen3-vl:4b,llava,moondream}"
STAGE2_FALLBACK_MODELS="${OLLAMA_STAGE2_FALLBACK_MODELS:-llava,moondream}"

if [[ ! -x "${VENV_PY}" ]]; then
  echo "Missing ${VENV_PY}. Create the repo venv first." >&2
  exit 1
fi

resolve_ollama_bin() {
  if [[ -n "${OLLAMA_BIN}" && -x "${OLLAMA_BIN}" ]]; then
    printf '%s' "${OLLAMA_BIN}"
    return 0
  fi

  for candidate in /opt/homebrew/bin/ollama /usr/local/bin/ollama; do
    if [[ -x "${candidate}" ]]; then
      printf '%s' "${candidate}"
      return 0
    fi
  done

  command -v ollama
}

ensure_legacy_server_stopped() {
  local legacy_pids
  legacy_pids="$(ps -eo pid=,command= | awk '/\/Applications\/Ollama.app\/Contents\/Resources\/ollama serve/ {print $1}')"
  if [[ -n "${legacy_pids}" ]]; then
    echo "Stopping legacy Ollama.app server..." >&2
    pkill -9 -f '/Applications/Ollama.app/Contents/Resources/ollama serve' >/dev/null 2>&1 || true
    sleep 2
  fi
}

ensure_server() {
  if ! curl -fsS "${HOST}/api/tags" >/dev/null 2>&1; then
    echo "Starting Ollama server from ${OLLAMA_BIN}..." >&2
    nohup env OLLAMA_HOST="${BIND_HOST}" OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 "${OLLAMA_BIN}" serve >/tmp/ollama.log 2>&1 &
    sleep 3
  fi

  if ! curl -fsS "${HOST}/api/tags" >/dev/null 2>&1; then
    echo "Ollama server is not ready at ${HOST}" >&2
    exit 1
  fi
}

select_multimodal_model() {
  local target_model="$1"
  local fallback_models="$2"
  local candidate
  ensure_legacy_server_stopped
  ensure_server

  if "${OLLAMA_BIN}" ls | awk '{print $1}' | grep -qx "${target_model}"; then
    printf '%s' "${target_model}"
    return 0
  fi

  echo "Pulling ${target_model}..." >&2
  if "${OLLAMA_BIN}" pull "${target_model}" >/dev/null 2>&1; then
    printf '%s' "${target_model}"
    return 0
  fi

  IFS=',' read -r -a fallback_candidates <<< "${fallback_models}"
  for candidate in "${fallback_candidates[@]}"; do
    candidate="${candidate//[[:space:]]/}"
    [[ -z "${candidate}" || "${candidate}" == "${target_model}" ]] && continue
    echo "Trying fallback model ${candidate}..." >&2
    if ! "${OLLAMA_BIN}" ls | awk '{print $1}' | grep -qx "${candidate}"; then
      if ! "${OLLAMA_BIN}" pull "${candidate}" >/dev/null 2>&1; then
        continue
      fi
    fi
    printf '%s' "${candidate}"
    return 0
  done

  echo "No usable multimodal Ollama model found for ${target_model}." >&2
  exit 1
}

ensure_base_model() {
  OLLAMA_BIN="$(resolve_ollama_bin)"
  ensure_legacy_server_stopped
  ensure_server
  if "${OLLAMA_BIN}" ls | awk '{print $1}' | grep -qx "${TARGET_MODEL}"; then
    printf '%s' "${TARGET_MODEL}"
    return 0
  fi
  echo "Pulling base model ${TARGET_MODEL}..." >&2
  if "${OLLAMA_BIN}" pull "${TARGET_MODEL}" >/dev/null 2>&1; then
    printf '%s' "${TARGET_MODEL}"
    return 0
  fi

  local candidate
  IFS=',' read -r -a fallback_candidates <<< "${FALLBACK_MODELS}"
  for candidate in "${fallback_candidates[@]}"; do
    candidate="${candidate//[[:space:]]/}"
    [[ -z "${candidate}" || "${candidate}" == "${TARGET_MODEL}" ]] && continue
    echo "Trying base-model fallback ${candidate}..." >&2
    if ! "${OLLAMA_BIN}" ls | awk '{print $1}' | grep -qx "${candidate}"; then
      if ! "${OLLAMA_BIN}" pull "${candidate}" >/dev/null 2>&1; then
        continue
      fi
    fi
    printf '%s' "${candidate}"
    return 0
  done

  echo "No usable base Ollama model found." >&2
  exit 1
}

BASE_MODEL="$(ensure_base_model)"
MODEL="$(select_multimodal_model "${TARGET_STAGE2_MODEL}" "${STAGE2_FALLBACK_MODELS}")"

echo "Checking multimodal support for ${MODEL}..." >&2
OLLAMA_MODEL="${MODEL}" OLLAMA_BASE_URL="${BASE_URL}" "${VENV_PY}" - <<'PY'
import base64
import os
import sys
from pathlib import Path

import httpx

model = os.environ["OLLAMA_MODEL"]
base_url = os.environ["OLLAMA_BASE_URL"].rstrip("/")
sample_image = Path("dataset/images/sample/case_009/img_1.jpg").read_bytes()
payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": "What visible damage is present in this image?",
            "images": [base64.b64encode(sample_image).decode("utf-8")],
        }
    ],
    "stream": False,
}
response = httpx.post(f"{base_url}/api/chat", json=payload, timeout=120.0)
if response.status_code != 200:
    sys.stderr.write(
        f"Model {model} failed multimodal preflight with status {response.status_code}: "
        f"{response.text[:500]}\n"
    )
    sys.exit(1)
PY

REPORT_PATH="${ROOT_DIR}/code/evaluation/evaluation_report.local-ollama.md"
METRICS_PATH="${ROOT_DIR}/code/evaluation/metrics.local-ollama.json"
REGISTRY_PATH="${ROOT_DIR}/code/evaluation/experiments.local-ollama.json"

cd "${ROOT_DIR}"

echo "Running sample evaluation with base=${BASE_MODEL} stage2=${MODEL} strategy=B" >&2
OLLAMA_MODEL="${BASE_MODEL}" OLLAMA_STAGE2_MODEL="${MODEL}" OLLAMA_BASE_URL="${BASE_URL}" \
  "${VENV_PY}" code/evaluation/main.py \
  --gold dataset/sample_claims.csv \
  --model ollama \
  --strategy B \
  --report "${REPORT_PATH}" \
  --metrics-json "${METRICS_PATH}" \
  --registry "${REGISTRY_PATH}" \
  --notes "Local Ollama sample evaluation via scripts/run_local_ollama_eval.sh with dedicated Stage 2 model"

echo "Artifacts:" >&2
echo "  ${REPORT_PATH}" >&2
echo "  ${METRICS_PATH}" >&2
echo "  ${REGISTRY_PATH}" >&2
