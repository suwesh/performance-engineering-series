#!/usr/bin/env bash
set -euo pipefail

MODE="${1:?Usage: $0 <normal|mtp> <workload> <prompt_id> <repetition>}"
WORKLOAD="${2:?Missing workload}"
PROMPT_ID="${3:?Missing prompt ID}"
REPETITION="${4:?Missing repetition}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GPU_PROF_ROOT:-$SCRIPT_DIR}"
CLIENT="${GPU_PROF_CLIENT:-$ROOT/gpu_prof_client.py}"
PROTOCOL="${GPU_PROF_PROTOCOL:-$ROOT/protocol_v1.2.yaml}"
PYTHON="${GPU_PROF_PYTHON:-/home/cbotadmin/env312-vllm024/bin/python}"
API_BASE="http://127.0.0.1:8000"
CLIENT_ROOT="$ROOT/profile_client_runs/torch"
TORCH_WARMUP_ROOT="$ROOT/profile_client_runs/torch_warmups"

case "$MODE" in
  normal) SERVICE="torchprof-gemma4vllm.service" ;;
  mtp) SERVICE="torchprof-gemma4vllm-mtp.service" ;;
  *) echo "ERROR: mode must be normal or mtp" >&2; exit 2 ;;
esac

systemctl is-active --quiet "$SERVICE" || {
  echo "ERROR: expected service is not active: $SERVICE" >&2
  exit 3
}

[[ -f "$CLIENT" ]] || { echo "ERROR: client not found: $CLIENT" >&2; exit 2; }
[[ -f "$PROTOCOL" ]] || { echo "ERROR: protocol not found: $PROTOCOL" >&2; exit 2; }
[[ -x "$PYTHON" ]] || { echo "ERROR: Python is not executable: $PYTHON" >&2; exit 2; }
[[ -f "${PROTOCOL%.yaml}.sha256" ]] || { echo "ERROR: protocol checksum not found" >&2; exit 2; }
mkdir -p "$CLIENT_ROOT" "$TORCH_WARMUP_ROOT" "$ROOT/profiles/torch/$MODE"

case "$WORKLOAD" in
    plain_text)
        SHORT_NAME="plain"
        ;;
    reasoning_intensive)
        SHORT_NAME="reasoning"
        ;;
    tool_calling)
        SHORT_NAME="tool"
        ;;
    *)
        echo "ERROR: unsupported workload: $WORKLOAD " >&2
        exit 2
        ;;
esac
echo "Running three unprofiled warm-ups before Torch profiling..."
for WARM_REP in 971 972 973; do
    WARM_DIR="$TORCH_WARMUP_ROOT/runs/v1-${MODE}-${SHORT_NAME}-${PROMPT_ID}-r${WARM_REP}"
    rm -rf "$WARM_DIR"
    echo "WARM-up: mode=$MODE workload=$WORKLOAD repetition=$WARM_REP"
    set +e
    "$PYTHON" "$CLIENT" \
        --mode "$MODE" \
        --workload "$WORKLOAD" \
        --prompt-id "$PROMPT_ID" \
        --repetition "$WARM_REP" \
        --run-type warmup \
        --protocol "$PROTOCOL" \
        --output-root "$TORCH_WARMUP_ROOT"
    WARM_RC=$?
    set -e
    if [[ "$WARM_RC" != "0" && "$WARM_RC" != 2 ]]; then
        echo "ERROR: Torch warm-up failed with exit code $WARM_RC" >&2
        exit "$WARM_RC"
    fi
done
echo "Torch warm-ups completed."
echo "Starting PyTorch Profiler..."

HTTP_CODE="$(curl -sS -o /tmp/gpu-prof-start-profile.out -w '%{http_code}' \
  -X POST "$API_BASE/start_profile" || true)"
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "ERROR: /start_profile returned HTTP $HTTP_CODE" >&2
  cat /tmp/gpu-prof-start-profile.out >&2 || true
  echo "The active vLLM service must be launched with --profiler-config." >&2
  exit 5
fi

STOP_NEEDED=1
cleanup() {
  if [[ "${STOP_NEEDED:-0}" == "1" ]]; then
    echo "Stopping and flushing PyTorch Profiler..."
    curl -sS --max-time 1800 -X POST "$API_BASE/stop_profile" || true
  fi
}
trap cleanup EXIT INT TERM

"$PYTHON" "$CLIENT" \
  --mode "$MODE" \
  --workload "$WORKLOAD" \
  --prompt-id "$PROMPT_ID" \
  --repetition "$REPETITION" \
  --run-type profile \
  --protocol "$PROTOCOL" \
  --output-root "$CLIENT_ROOT"

echo "Stopping and flushing PyTorch Profiler..."
curl -fSs --max-time 1800 -X POST "$API_BASE/stop_profile"
STOP_NEEDED=0
trap - EXIT INT TERM

echo "PyTorch profile complete."
echo "Client correlation artifacts: $CLIENT_ROOT/runs/"
echo "Worker traces are in the torch_profiler_dir configured on the vLLM service."
