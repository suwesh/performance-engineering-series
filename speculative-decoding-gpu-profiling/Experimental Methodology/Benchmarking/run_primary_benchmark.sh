#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./run_primary_benchmark.sh normal
#   ./run_primary_benchmark.sh mtp

MODE="${1:?Usage: $0 <normal|mtp>}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GPU_PROF_ROOT:-$SCRIPT_DIR}"

PYTHON="${GPU_PROF_PYTHON:-/home/cbotadmin/env312-vllm024/bin/python}"
CLIENT="${GPU_PROF_CLIENT:-$ROOT/gpu_prof_client.py}"
PROTOCOL="${GPU_PROF_PROTOCOL:-$ROOT/protocol_v1.2.yaml}"
BENCHMARK_RUNNER="$ROOT/run_benchmark.sh"
PRIMARY_ROOT="$ROOT/primary"
WARMUP_ROOT="$PRIMARY_ROOT/warmups"

case "$MODE" in 
    normal)
        SERVICE="prof-gemma4vllm.service"
        ;;
    mtp)
        SERVICE="prof-gemma4vllm-mtp.service"
        ;;
    *)
        echo "ERROR: mode must be normal or mtp" >&2
        exit 2
        ;;
esac

[[ -x "$PYTHON" ]] || {
    echo "ERROR: Python is not executable: $PYTHON" >&2
    exit 2
}
[[ -f "$CLIENT" ]] || {
    echo "ERROR: client not found: $CLIENT" >&2
    exit 2
}
[[ -f "$PROTOCOL" ]] || {
    echo "ERROR: protocol not found: $PROTOCOL" >&2
    exit 2
}
[[ -f "${PROTOCOL%.yaml}.sha256" ]] || {
    echo "ERROR: protocol checksum not found" >&2
    exit 2
}
[[ -x "$BENCHMARK_RUNNER" ]] || {
    echo "ERROR: benchmark runner is not executable: $BENCHMARK_RUNNER" >&2
    exit 2
}

systemctl is-active --quiet "$SERVICE" || {
    echo "ERROR: expected service is not active: $SERVICE" >&2
    exit 3
}

if pgrep -af 'nsys|ncu' \
    | grep -v -E 'grep|run_primary_benchmark.sh' \
    >/dev/null; then

    echo "ERROR: NVIDIA profiler process detected" >&2
    pgrep -af 'nsys|ncu' || true
    exit 4
fi

mkdir -p "$WARMUP_ROOT" "$PRIMARY_ROOT/runs" "$PRIMARY_ROOT/archives"

echo
echo "========================================"
echo "GPU inference primary benchmark"
echo "Mode:     $MODE"
echo "Service:  $SERVICE"
echo "Protocol: $PROTOCOL"
echo "========================================"
echo

run_warmups() {
    local workload="$1"
    local prompt_id="$2"
    local short_name
    local warm_rep
    local warm_dir

    case "$workload" in
        plain_text)
            short_name="plain"
            ;;
        reasoning_intensive)
            short_name="reasoning"
            ;;
        tool_calling)
            short_name="tool"
            ;;
        *)
            echo "ERROR: unsupported workload: $workload" >&2
            exit 2
            ;;
    esac

    echo "Running three warm-ups for $MODE + $workload..."
    for warm_rep in 991 992 993; do
        warm_dir="$WARMUP_ROOT/runs/v1-${MODE}-${short_name}-${prompt_id}-r${warm_rep}"
        rm -rf "$warm_dir"
        echo "Warm-up: workload=$workload repetition=$warm_rep"

        "$PYTHON" "$CLIENT" \
            --mode "$MODE" \
            --workload "$workload" \
            --prompt-id "$prompt_id" \
            --repetition "$warm_rep" \
            --run-type warmup \
            --protocol "$PROTOCOL" \
            --output-root "$WARMUP_ROOT"
    done
    echo "Warm-ups completed for $MODE + $workload."
    echo
}

run_measurements() {
    local workload="$1"
    local prompt_1="$2"
    local prompt_2="$3"
    local prompt_3="$4"
    local prompt_id
    local repetition

    echo "Running measured requests for $MODE + $workload..."
    for prompt_id in "$prompt_1" "$prompt_2" "$prompt_3"; do
        for repetition in $(seq 1 20); do
            echo 
            echo "Measurement:"
            echo "  mode=$MODE"
            echo "  workload=$workload"
            echo "  prompt=$prompt_id"
            echo "  repetition=$repetition"

            GPU_PROF_ROOT="$PRIMARY_ROOT" \
            GPU_PROF_CLIENT="$CLIENT" \
            GPU_PROF_PROTOCOL="$PROTOCOL" \
            GPU_PROF_PYTHON="$PYTHON" \
            "$BENCHMARK_RUNNER" \
                "$MODE" \
                "$workload" \
                "$prompt_id" \
                "$repetition"
        done
    done
    echo
    echo "Measurements completed for $MODE + $workload."
    echo
}

run_warmups \
    plain_text \
    plain_001
run_measurements \
    plain_text \
    plain_001 \
    plain_002 \
    plain_003

run_warmups \
    reasoning_intensive \
    reasoning_001
run_measurements \
    reasoning_intensive \
    reasoning_001 \
    reasoning_002 \
    reasoning_003

run_warmups \
    tool_calling \
    tool_001
run_measurements \
    tool_calling \
    tool_001 \
    tool_002 \
    tool_003

echo
echo "========================================"
echo "Primary benchmark completed"
echo "Mode: $MODE"
echo "Expected measured rows added: 180"
echo "Results file: $PRIMARY_ROOT/results.csv"
echo "========================================"
