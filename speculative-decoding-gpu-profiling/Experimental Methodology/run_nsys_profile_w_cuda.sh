#!/usr/bin/env bash
set -euo pipefail

# Combined Nsight Systems launcher for vLLM + gpu_prof_client.py.
#
# User invocation:
#   ./run_nsys_profile_w_cuda.sh normal reasoning_intensive reasoning_001 98
#
# Internal invocation is performed automatically beneath `nsys profile`.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GPU_PROF_ROOT:-$SCRIPT_DIR}"
CLIENT="${GPU_PROF_CLIENT:-$ROOT/gpu_prof_client.py}"
PROTOCOL="${GPU_PROF_PROTOCOL:-$ROOT/protocol_v1.2.yaml}"
PYTHON="${GPU_PROF_PYTHON:-/home/cbotadmin/env312-vllm024/bin/python}"
NSYS="${NSYS_BIN:-/usr/local/bin/nsys}"
RUN_USER="${GPU_PROF_USER:-cbotadmin}"
API_BASE="http://127.0.0.1:8000"
CLIENT_ROOT="$ROOT/profile_client_runs/nsys"
GPU_IDLE_MAX_MIB="${GPU_IDLE_MAX_MIB:-1024}"
MIN_AVAILABLE_GIB="${MIN_AVAILABLE_GIB:-8}"

usage() {
  echo "Usage: $0 <normal|mtp> <plain_text|reasoning_intensive|tool_calling> <prompt_id> <repetition>" >&2
}

workload_short() {
  case "$1" in
    plain_text) echo "plain" ;;
    reasoning_intensive) echo "reasoning" ;;
    tool_calling) echo "tool" ;;
    *) return 1 ;;
  esac
}

wait_for_vllm_exit() {
  local limit="${1:-150}"
  local i
  for i in $(seq 1 "$limit"); do
    if ! pgrep -f 'vllm.entrypoints.openai.api_server|VLLM::EngineCore' >/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

stop_known_vllm_services() {
  local service
  for service in \
    gemma4vllm.service \
    gemma4vllm-mtp.service \
    prof-gemma4vllm.service \
    prof-gemma4vllm-mtp.service \
    torchprof-gemma4vllm.service \
    torchprof-gemma4vllm-mtp.service; do
    if systemctl list-unit-files "$service" --no-legend 2>/dev/null | grep -q "^${service}"; then
      sudo systemctl stop "$service" || true
    fi
  done
}

inside_nsys() {
  local mode="$1"
  local workload="$2"
  local prompt_id="$3"
  local repetition="$4"
  local short
  local server_pid=""
  local server_log
  local target_dir
  local client_rc

  short="$(workload_short "$workload")" || {
    echo "ERROR: unsupported workload: $workload" >&2
    exit 2
  }

  mkdir -p "$ROOT/profiles/nsys/$mode/logs" "$CLIENT_ROOT"

  server_log="$ROOT/profiles/nsys/$mode/logs/v1.2-${mode}-${workload}-${prompt_id}-r$(printf '%02d' "$repetition").server.log"

  local vllm_args=(
    -m vllm.entrypoints.openai.api_server
    --model /home/cbotadmin/models/gemma4-w4a16ct
    --served-model-name google/gemma-4-e4b
    --host 0.0.0.0
    --port 8000
    --dtype auto
    --gpu-memory-utilization 0.80
    --max-model-len 8192
    --enable-chunked-prefill
    --max-num-batched-tokens 2048
    --max-num-seqs 1
    --kv-cache-dtype bfloat16
    --enable-prefix-caching
    --enable-auto-tool-choice
    --tool-call-parser gemma4
    --reasoning-parser gemma4
    --generation-config vllm
    --chat-template /home/cbotadmin/models/gemma4-w4a16ct/tool_chat_template_gemma4.jinja
    --chat-template-content-format openai
  )

  if [[ "$mode" == "mtp" ]]; then
    vllm_args+=(
      --speculative-config
      '{"method":"mtp","model":"/home/cbotadmin/models/gemma4-drafter","num_speculative_tokens":2}'
    )
  fi

  cleanup_profiled_server() {
    if [[ -n "${server_pid:-}" ]] && kill -0 "$server_pid" 2>/dev/null; then
      echo "Stopping temporary profiled vLLM process group..."
      kill -TERM -- "-$server_pid" 2>/dev/null || kill -TERM "$server_pid" 2>/dev/null || true

      local i
      for i in $(seq 1 150); do
        kill -0 "$server_pid" 2>/dev/null || break
        sleep 2
      done

      if kill -0 "$server_pid" 2>/dev/null; then
        echo "WARNING: escalating temporary vLLM shutdown" >&2
        kill -KILL -- "-$server_pid" 2>/dev/null || kill -KILL "$server_pid" 2>/dev/null || true
      fi
    fi
  }
  trap cleanup_profiled_server EXIT INT TERM

  echo "Launching temporary $mode vLLM beneath Nsight Systems..."
  setsid env \
    HOME="/home/cbotadmin" \
    USER="cbotadmin" \
    LOGNAME="cbotadmin" \
    XDG_CACHE_HOME="/home/cbotadmin/.cache" \
    HF_HOME="/home/cbotadmin/.cache/huggingface" \
    TORCH_HOME="/home/cbotadmin/.cache/torch" \
    TRITON_CACHE_DIR="/home/cbotadmin/.cache/triton" \
    PATH="/home/cbotadmin/env312-vllm024/bin:/home/cbotadmin/.local/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin" \
    PYTHONUNBUFFERED=1 \
  "$PYTHON" "${vllm_args[@]}" >"$server_log" 2>&1 &
  server_pid=$!

  echo "Temporary launcher PID: $server_pid"
  echo "Server log: $server_log"

  local healthy=0
  local i
  for i in $(seq 1 300); do
    if ! kill -0 "$server_pid" 2>/dev/null; then
      echo "ERROR: temporary vLLM exited before becoming healthy" >&2
      tail -100 "$server_log" >&2 || true
      exit 5
    fi

    if curl -fsS "$API_BASE/health" >/dev/null 2>&1; then
      healthy=1
      echo "Health check passed after ${i}s"
      break
    fi
    sleep 1
  done

  if [[ "$healthy" != "1" ]]; then
    echo "ERROR: temporary vLLM did not become healthy within 300 seconds" >&2
    tail -100 "$server_log" >&2 || true
    exit 5
  fi

  echo "Allowing 30 seconds for runtime settling..."
  sleep 30

  echo "Running three workload-matched warm-up requests..."
  local warm_rep
  for warm_rep in 981 982 983; do
    rm -rf "$CLIENT_ROOT/runs/v1-${mode}-${short}-${prompt_id}-r${warm_rep}"

    set +e
    "$PYTHON" "$CLIENT" \
        --mode "$mode" \
        --workload "$workload" \
        --prompt-id "$prompt_id" \
        --repetition "$warm_rep" \
        --run-type warmup \
        --protocol "$PROTOCOL" \
        --output-root "$CLIENT_ROOT"
    client_rc=$?
    set -e

    # Exit 2 is expected because direct vLLM launch means the equivalent
    # systemd service is intentionally inactive during this diagnostic run.
    if [[ "$client_rc" != "0" && "$client_rc" != "2" ]]; then
      echo "ERROR: warm-up request failed with exit code $client_rc" >&2
      exit "$client_rc"
    fi
  done

  target_dir="$CLIENT_ROOT/runs/v1-${mode}-${short}-${prompt_id}-r$(printf '%02d' "$repetition")"
  rm -rf "$target_dir"

  echo "Running target request with client NVTX markers..."
  set +e
  "$PYTHON" "$CLIENT" \
      --mode "$mode" \
      --workload "$workload" \
      --prompt-id "$prompt_id" \
      --repetition "$repetition" \
      --run-type profile \
      --protocol "$PROTOCOL" \
      --output-root "$CLIENT_ROOT"
  client_rc=$?
  set -e

  if [[ "$client_rc" != "0" && "$client_rc" != "2" ]]; then
    echo "ERROR: target client failed with exit code $client_rc" >&2
    exit "$client_rc"
  fi

  [[ -s "$target_dir/raw.jsonl" ]] || {
    echo "ERROR: target raw.jsonl was not created" >&2
    exit 6
  }
  [[ -s "$target_dir/summary.json" ]] || {
    echo "ERROR: target summary.json was not created" >&2
    exit 6
  }

  "$PYTHON" - "$target_dir/summary.json" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    summary = json.load(handle)

validity = summary["validity"]
print("Target validity:", validity)

if not validity["phase_mapping_valid"]:
    raise SystemExit("ERROR: phase mapping validation failed")
if not validity["output_valid"]:
    raise SystemExit("ERROR: output validation failed")
PY

  cleanup_profiled_server
  server_pid=""
  trap - EXIT INT TERM

  echo "Temporary vLLM stopped. Internal profiled condition completed."
}

# Internal branch: this entire branch executes beneath `nsys profile`.
if [[ "${1:-}" == "--inside-nsys" ]]; then
  shift
  [[ "$#" -eq 4 ]] || { usage; exit 2; }
  inside_nsys "$1" "$2" "$3" "$4"
  exit 0
fi

# Outer user-facing branch.
[[ "$#" -eq 4 ]] || { usage; exit 2; }
MODE="$1"
WORKLOAD="$2"
PROMPT_ID="$3"
REPETITION="$4"

[[ "$MODE" == "normal" || "$MODE" == "mtp" ]] || {
  echo "ERROR: mode must be normal or mtp" >&2
  exit 2
}
workload_short "$WORKLOAD" >/dev/null || {
  echo "ERROR: unsupported workload: $WORKLOAD" >&2
  exit 2
}
[[ "$REPETITION" =~ ^[1-9][0-9]*$ ]] || {
  echo "ERROR: repetition must be a positive integer" >&2
  exit 2
}

[[ -x "$NSYS" ]] || { echo "ERROR: nsys not executable: $NSYS" >&2; exit 2; }
[[ -x "$PYTHON" ]] || { echo "ERROR: Python not executable: $PYTHON" >&2; exit 2; }
[[ -f "$CLIENT" ]] || { echo "ERROR: client missing: $CLIENT" >&2; exit 2; }
[[ -f "$PROTOCOL" ]] || { echo "ERROR: protocol missing: $PROTOCOL" >&2; exit 2; }
[[ -f "${PROTOCOL%.yaml}.sha256" ]] || { echo "ERROR: protocol checksum missing" >&2; exit 2; }

RUN_TAG="v1.2-${MODE}-${WORKLOAD}-${PROMPT_ID}-nsys-r$(printf '%02d' "$REPETITION")"
REPORT_DIR="$ROOT/profiles/nsys/$MODE"
REPORT_BASE="$REPORT_DIR/$RUN_TAG"
REPORT="${REPORT_BASE}.nsys-rep"
mkdir -p "$REPORT_DIR" "$CLIENT_ROOT"

if [[ -e "$REPORT" || -e "${REPORT_BASE}.qdstrm" ]]; then
  echo "ERROR: report artifacts already exist for $RUN_TAG" >&2
  exit 3
fi

cat <<EOF
WARNING
  This capture will stop all known vLLM services.
  A temporary reduced-memory vLLM instance will run beneath Nsight Systems.
  Production service restoration will remain manual after capture.
  Planned report: $REPORT
EOF

stop_known_vllm_services

if ! wait_for_vllm_exit 150; then
  echo "ERROR: prior vLLM processes did not terminate" >&2
  pgrep -af 'vllm.entrypoints.openai.api_server|VLLM::EngineCore' >&2 || true
  exit 4
fi
echo "All prior vLLM processes stopped."

if ss -lnt | awk '{print $4}' | grep -q ':8000$'; then
  echo "ERROR: port 8000 is still in use" >&2
  ss -lntp | grep ':8000' >&2 || true
  exit 4
fi

GPU_USED_MIB="$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits 2>/dev/null | awk '{sum+=$1} END {print sum+0}')"
if (( GPU_USED_MIB > GPU_IDLE_MAX_MIB )); then
  echo "ERROR: GPU compute memory remains in use: ${GPU_USED_MIB} MiB" >&2
  nvidia-smi >&2
  exit 4
fi

AVAILABLE_KIB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
MIN_KIB=$((MIN_AVAILABLE_GIB * 1024 * 1024))
if (( AVAILABLE_KIB < MIN_KIB )); then
  echo "ERROR: insufficient host RAM available" >&2
  free -h >&2
  exit 4
fi

echo "Preflight passed: GPU=${GPU_USED_MIB} MiB; host available=$((AVAILABLE_KIB / 1024 / 1024)) GiB"

NSYS_ARGS=(
  profile
  --trace=cuda,nvtx,osrt
  --trace-fork-before-exec=true
  --sample=none
  --force-overwrite=true
  --output="$REPORT_BASE"
)

if "$NSYS" profile --help 2>/dev/null | grep -q -- '--cuda-graph-trace'; then
  NSYS_ARGS+=(--cuda-graph-trace=node)
fi

echo "Starting combined CUDA + NVTX capture..."
sudo env \
  GPU_PROF_ROOT="$ROOT" \
  GPU_PROF_CLIENT="$CLIENT" \
  GPU_PROF_PROTOCOL="$PROTOCOL" \
  GPU_PROF_PYTHON="$PYTHON" \
  GPU_PROF_USER="$RUN_USER" \
  "$NSYS" "${NSYS_ARGS[@]}" \
  "$SCRIPT_DIR/run_nsys_profile_w_cuda.sh" \
    --inside-nsys "$MODE" "$WORKLOAD" "$PROMPT_ID" "$REPETITION"

[[ -s "$REPORT" ]] || {
  echo "ERROR: Nsight Systems report was not created: $REPORT" >&2
  exit 6
}

if pgrep -f 'vllm.entrypoints.openai.api_server|VLLM::EngineCore' >/dev/null; then
  echo "ERROR: a temporary vLLM process remains after capture" >&2
  pgrep -af 'vllm.entrypoints.openai.api_server|VLLM::EngineCore' >&2 || true
  exit 7
fi

POST_GPU_MIB="$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits 2>/dev/null | awk '{sum+=$1} END {print sum+0}')"

echo
echo "Combined Nsight Systems report created: $REPORT"
echo "Post-capture GPU compute memory: ${POST_GPU_MIB} MiB"
echo "Production service was NOT restarted. Restore the required service manually."
echo
echo "Quick CUDA summary:"
"$NSYS" stats \
  --report cuda_gpu_kern_sum \
  "$REPORT" 2>/dev/null | head -25 || true
