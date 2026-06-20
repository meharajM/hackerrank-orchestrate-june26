#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT_DIR}/.venv/bin/python"
BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
BIND_HOST="${BASE_URL#http://}"
BIND_HOST="${BIND_HOST#https://}"
MODEL="${OLLAMA_MODEL:-qwen3-vl:4b}"
STAGE2_MODEL="${OLLAMA_STAGE2_MODEL:-qwen3-vl:4b}"
LIMIT="${STAGE2_HARNESS_LIMIT:-6}"
OUTPUT_DIR="${STAGE2_HARNESS_OUTPUT_DIR:-${ROOT_DIR}/code/evaluation/stage2_local_intermediate}"
OLLAMA_BIN="${OLLAMA_BIN:-}"

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

ensure_server() {
  OLLAMA_BIN="$(resolve_ollama_bin)"
  if ! curl -fsS "${BASE_URL%/}/api/tags" >/dev/null 2>&1; then
    echo "Starting Ollama server on ${BIND_HOST}..." >&2
    nohup env OLLAMA_HOST="${BIND_HOST}" OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 "${OLLAMA_BIN}" serve >/tmp/ollama-stage2-harness.log 2>&1 &
    sleep 3
  fi

  if ! curl -fsS "${BASE_URL%/}/api/tags" >/dev/null 2>&1; then
    echo "Ollama server is not ready at ${BASE_URL}" >&2
    exit 1
  fi
}

ensure_model() {
  local model="$1"
  if ! "${OLLAMA_BIN}" ls | awk '{print $1}' | grep -qx "${model}"; then
    echo "Pulling ${model}..." >&2
    "${OLLAMA_BIN}" pull "${model}" >/dev/null
  fi
}

ensure_server
ensure_model "${MODEL}"
ensure_model "${STAGE2_MODEL}"

echo "Running Stage 2 harness with base=${MODEL} stage2=${STAGE2_MODEL} base_url=${BASE_URL}" >&2
OLLAMA_BASE_URL="${BASE_URL}" \
OLLAMA_MODEL="${MODEL}" \
OLLAMA_STAGE2_MODEL="${STAGE2_MODEL}" \
  "${VENV_PY}" "${ROOT_DIR}/code/src/pipeline/smoke_evidence.py" \
  --model ollama \
  --claims "${ROOT_DIR}/dataset/sample_claims.csv" \
  --limit "${LIMIT}" \
  --output-dir "${OUTPUT_DIR}"
