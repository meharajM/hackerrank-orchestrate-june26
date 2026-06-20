#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
VENV_PY="${VENV_DIR}/bin/python"
TARGET_MODEL="${OLLAMA_MODEL:-qwen3-vl:4b}"
TARGET_STAGE2_MODEL="${OLLAMA_STAGE2_MODEL:-qwen3-vl:4b}"
FALLBACK_MODELS="${BOOTSTRAP_FALLBACK_MODELS:-qwen3-vl:4b,llava,moondream}"
STAGE2_FALLBACK_MODELS="${BOOTSTRAP_STAGE2_FALLBACK_MODELS:-llava,moondream}"
ALLOW_FALLBACK="${ALLOW_BOOTSTRAP_FALLBACK:-1}"
ALLOW_MOCK_FALLBACK="${ALLOW_BOOTSTRAP_MOCK_FALLBACK:-1}"
BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
HOST="${BASE_URL%/}"
BIND_HOST="${HOST#http://}"
BIND_HOST="${BIND_HOST#https://}"
OLLAMA_BIN="${OLLAMA_BIN:-}"
SAMPLE_OUTPUT="${ROOT_DIR}/output.bootstrap.sample.csv"
SAMPLE_REPORT="${ROOT_DIR}/code/evaluation/evaluation_report.bootstrap.md"
SAMPLE_METRICS="${ROOT_DIR}/code/evaluation/metrics.bootstrap.json"
SAMPLE_REGISTRY="${ROOT_DIR}/code/evaluation/experiments.bootstrap.json"

log() {
  printf '%s\n' "$*" >&2
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "Missing required command: ${cmd}"
    exit 1
  fi
}

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

ensure_python_venv() {
  require_cmd python3
  require_cmd curl
  if [[ ! -x "${VENV_PY}" ]]; then
    log "[python] Creating virtual environment at ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
  fi
  log "[python] Upgrading pip"
  "${VENV_PY}" -m pip install --upgrade pip
  log "[python] Installing runtime requirements"
  "${VENV_PY}" -m pip install -r "${ROOT_DIR}/code/requirements.txt"
  log "[python] Installing editable package"
  "${VENV_PY}" -m pip install -e "${ROOT_DIR}/code"
}

ensure_ollama() {
  if ! command -v ollama >/dev/null 2>&1; then
    log "[ollama] Ollama not found; installing via official installer"
    curl -fsSL https://ollama.com/install.sh | sh
  fi

  OLLAMA_BIN="$(resolve_ollama_bin)"
  log "[ollama] Client binary: ${OLLAMA_BIN}"
  log "[ollama] Version: $(${OLLAMA_BIN} --version 2>/dev/null || true)"

  local legacy_pids
  legacy_pids="$(ps -eo pid=,command= | awk '/\/Applications\/Ollama.app\/Contents\/Resources\/ollama serve/ {print $1}')"
  if [[ -n "${legacy_pids}" ]]; then
    log "[ollama] Stopping legacy Ollama.app server"
    pkill -9 -f '/Applications/Ollama.app/Contents/Resources/ollama serve' >/dev/null 2>&1 || true
    sleep 2
  fi

  if ! curl -fsS "${HOST}/api/tags" >/dev/null 2>&1; then
    log "[ollama] Starting Ollama server from ${OLLAMA_BIN}"
    nohup env OLLAMA_HOST="${BIND_HOST}" OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 "${OLLAMA_BIN}" serve >/tmp/ollama.log 2>&1 &
    sleep 3
  fi

  if ! curl -fsS "${HOST}/api/tags" >/dev/null 2>&1; then
    log "[ollama] Ollama server is not ready at ${HOST}"
    exit 1
  fi
}

ensure_model() {
  local model="$1"
  log "[ollama] Pulling or verifying ${model}"
  if ! "${OLLAMA_BIN}" ls | awk '{print $1}' | grep -qx "${model}"; then
    if ! "${OLLAMA_BIN}" pull "${model}"; then
      return 1
    fi
  fi
  return 0
}

preflight_model() {
  local model="$1"
  log "[ollama] Preflighting multimodal support for ${model}"
  OLLAMA_MODEL="${model}" OLLAMA_BASE_URL="${BASE_URL}" "${VENV_PY}" - <<'PY'
import base64
import csv
import os
import sys
from pathlib import Path

import httpx

model = os.environ["OLLAMA_MODEL"]
base_url = os.environ["OLLAMA_BASE_URL"].rstrip("/")

sample_claims = Path("dataset/sample_claims.csv")
with sample_claims.open(newline="") as f:
    reader = csv.DictReader(f)
    first_row = next(reader)

image_rel = first_row["image_paths"].split(";")[0].strip()
image = (Path("dataset") / image_rel).read_bytes()

payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": "What visible damage is present in this image? Be concise.",
            "images": [base64.b64encode(image).decode("utf-8")],
        }
    ],
    "stream": False,
}
resp = httpx.post(f"{base_url}/api/chat", json=payload, timeout=120.0)
if resp.status_code != 200:
    sys.stderr.write(resp.text[:500] + "\n")
    sys.exit(1)
PY
}

select_model() {
  local target_model="$1"
  local fallback_models="$2"
  if ensure_model "${target_model}" && preflight_model "${target_model}"; then
    log "[ollama] Using target model ${target_model}"
    printf '%s' "${target_model}"
    return 0
  fi

  if [[ "${ALLOW_FALLBACK}" == "1" ]]; then
    IFS=',' read -r -a fallback_candidates <<< "${fallback_models}"
    for candidate in "${fallback_candidates[@]}"; do
      candidate="${candidate//[[:space:]]/}"
      [[ -z "${candidate}" || "${candidate}" == "${target_model}" ]] && continue
      log "[ollama] Target model unavailable or not multimodal here; trying fallback ${candidate}"
      if ensure_model "${candidate}" && preflight_model "${candidate}"; then
        log "[ollama] Using fallback model ${candidate} for local startup only"
        printf '%s' "${candidate}"
        return 0
      fi
    done
  fi

  log "[ollama] No usable local multimodal model found"
  if [[ "${ALLOW_MOCK_FALLBACK}" == "1" ]]; then
    log "[ollama] Falling back to mock adapter for bootstrap smoke test"
    printf '%s' "mock"
    return 0
  fi

  return 1
}

select_base_model() {
  local candidate
  if ensure_model "${TARGET_MODEL}"; then
    printf '%s' "${TARGET_MODEL}"
    return 0
  fi

  if [[ "${ALLOW_FALLBACK}" == "1" ]]; then
    IFS=',' read -r -a fallback_candidates <<< "${FALLBACK_MODELS}"
    for candidate in "${fallback_candidates[@]}"; do
      candidate="${candidate//[[:space:]]/}"
      [[ -z "${candidate}" || "${candidate}" == "${TARGET_MODEL}" ]] && continue
      log "[ollama] Base model unavailable; trying fallback ${candidate}"
      if ensure_model "${candidate}"; then
        printf '%s' "${candidate}"
        return 0
      fi
    done
  fi

  if [[ "${ALLOW_MOCK_FALLBACK}" == "1" ]]; then
    printf '%s' "mock"
    return 0
  fi

  return 1
}

run_sample_inference() {
  local model="$1"
  local stage2_model="$2"
  local adapter="ollama"
  if [[ "${model}" == "mock" ]]; then
    adapter="mock"
  fi
  log "[run] Sample inference with base=${model} stage2=${stage2_model}"
  OLLAMA_MODEL="${model}" OLLAMA_STAGE2_MODEL="${stage2_model}" OLLAMA_BASE_URL="${BASE_URL}" \
    "${VENV_PY}" "${ROOT_DIR}/code/main.py" \
    --input "${ROOT_DIR}/dataset/sample_claims.csv" \
    --output "${SAMPLE_OUTPUT}" \
    --model "${adapter}" \
    --strategy B \
    --force \
    --no-cache
  log "[run] Sample predictions written to ${SAMPLE_OUTPUT}"
}

run_sample_eval() {
  local model="$1"
  local stage2_model="$2"
  log "[run] Sample evaluation with base=${model} stage2=${stage2_model}"
  OLLAMA_MODEL="${model}" OLLAMA_STAGE2_MODEL="${stage2_model}" OLLAMA_BASE_URL="${BASE_URL}" \
    "${VENV_PY}" "${ROOT_DIR}/code/evaluation/main.py" \
    --predictions "${SAMPLE_OUTPUT}" \
    --gold "${ROOT_DIR}/dataset/sample_claims.csv" \
    --report "${SAMPLE_REPORT}" \
    --metrics-json "${SAMPLE_METRICS}" \
    --registry "${SAMPLE_REGISTRY}" \
    --notes "Bootstrap startup evaluation with dedicated Stage 2 model"
  log "[run] Evaluation report: ${SAMPLE_REPORT}"
}

main() {
  cd "${ROOT_DIR}"
  log "[check] Repo root: ${ROOT_DIR}"
  log "[check] Python: $(python3 --version 2>/dev/null || true)"
  ensure_python_venv
  ensure_ollama
  local model stage2_model
  model="$(select_base_model)"
  if [[ "${model}" == "mock" ]]; then
    stage2_model="mock"
  else
    stage2_model="$(select_model "${TARGET_STAGE2_MODEL}" "${STAGE2_FALLBACK_MODELS}")"
  fi
  log "[check] Selected base model: ${model}"
  log "[check] Selected stage2 model: ${stage2_model}"
  log "[check] GEMINI_API_KEY present: $([[ -n "${GEMINI_API_KEY:-}" ]] && echo yes || echo no)"
  run_sample_inference "${model}" "${stage2_model}"
  run_sample_eval "${model}" "${stage2_model}"
  log "[done] Bootstrap complete"
  log "[done] Outputs:"
  log "  ${SAMPLE_OUTPUT}"
  log "  ${SAMPLE_REPORT}"
  log "  ${SAMPLE_METRICS}"
}

main "$@"
