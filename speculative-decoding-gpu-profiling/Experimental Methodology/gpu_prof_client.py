#!/usr/bin/env python3
"""Protocol-coupled streaming client for the GPU inference profiling study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests
import yaml

try:
    import nvtx
except ImportError:
    nvtx = None


REQUIRED_PROTOCOL_VERSION = "1.2"
RESULT_COLUMNS = [
    "run_id", "protocol_version", "mode", "workload", "prompt_id",
    "repetition", "run_type", "time_to_first_output_ms",
    "time_to_first_final_output_ms", "end_to_end_latency_ms",
    "reasoning_associated_duration_ms", "final_or_tool_associated_duration_ms",
    "prompt_tokens", "completion_tokens", "output_tokens_per_second",
    "finish_reason", "benchmark_valid", "phase_mapping_valid", "output_valid",
    "invalid_reasons",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("normal", "mtp"))
    parser.add_argument(
        "--workload",
        required=True,
        choices=("plain_text", "reasoning_intensive", "tool_calling"),
    )
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--repetition", required=True, type=int)
    parser.add_argument(
        "--run-type",
        required=True,
        choices=("parser-validation", "warmup", "benchmark", "profile"),
    )
    parser.add_argument("--protocol", default="protocol_v1.0.yaml")
    parser.add_argument("--output-root", default=".")
    parser.add_argument("--timeout", type=float, default=1800.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_checksum(protocol_path: Path) -> str:
    checksum_path = protocol_path.with_suffix(".sha256")
    if not checksum_path.exists():
        raise FileNotFoundError(f"Missing checksum file: {checksum_path}")
    expected = checksum_path.read_text(encoding="utf-8").split()[0].strip()
    actual = sha256(protocol_path)
    if expected != actual:
        raise RuntimeError(
            f"Protocol checksum mismatch: expected {expected}, calculated {actual}"
        )
    return actual


def load_protocol(path: Path) -> tuple[dict[str, Any], str]:
    checksum = verify_checksum(path)
    with path.open(encoding="utf-8") as handle:
        protocol = yaml.safe_load(handle)
    if protocol["protocol"]["version"] != REQUIRED_PROTOCOL_VERSION:
        raise ValueError("Unsupported protocol version")
    if protocol["protocol"]["status"] != "frozen":
        raise ValueError("Protocol is not frozen")
    return protocol, checksum


def find_prompt(protocol: dict[str, Any], workload: str, prompt_id: str) -> dict[str, Any]:
    prompts = protocol["workloads"][workload]["prompts"]
    for prompt in prompts:
        if prompt["id"] == prompt_id:
            return prompt
    raise ValueError(f"Prompt {prompt_id!r} does not belong to {workload!r}")


def expected_service_is_active(service: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", service],
        check=False,
    )
    return result.returncode == 0


def marker(name: str, run_type: str) -> None:
    if run_type != "profile":
        return
    if nvtx is None:
        raise RuntimeError("Profile mode requires the Python package 'nvtx'")
    nvtx.mark(name, domain="gpu-prof-client")


def meaningful_delta(reasoning: Any, content: Any, tool_calls: Any) -> bool:
    return bool(reasoning or content or tool_calls)


def append_jsonl(handle, record: dict[str, Any]) -> None:
    handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    handle.flush()


def merge_tool_calls(state: dict[int, dict[str, str]], fragments: list[dict[str, Any]]) -> None:
    for fragment in fragments:
        index = int(fragment.get("index", 0))
        current = state.setdefault(index, {"id": "", "name": "", "arguments": ""})
        if fragment.get("id"):
            current["id"] += fragment["id"]
        function = fragment.get("function") or {}
        if function.get("name"):
            current["name"] += function["name"]
        if function.get("arguments"):
            current["arguments"] += function["arguments"]


def validate_output(
    workload: str,
    prompt: dict[str, Any],
    final_text: str,
    tool_calls: list[dict[str, Any]],
    finish_reason: str | None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if finish_reason == "length":
        errors.append("output_truncated")

    if workload == "plain_text":
        lines = [line.strip() for line in final_text.splitlines() if line.strip()]
        if len(lines) != 8:
            errors.append("plain_text_not_exactly_eight_lines")
        elif any(not 6 <= len(line.split()) <= 12 for line in lines):
            errors.append("plain_text_line_word_count_out_of_range")

    elif workload == "reasoning_intensive":
        expected = prompt["expected_final"].strip()
        if expected not in final_text.strip():
            errors.append("expected_final_answer_missing")

    elif workload == "tool_calling":
        if len(tool_calls) != 1:
            errors.append("expected_exactly_one_tool_call")
        else:
            call = tool_calls[0]
            if call["name"] != prompt["expected_tool"]:
                errors.append("unexpected_tool_name")
            try:
                arguments = json.loads(call["arguments"])
            except json.JSONDecodeError:
                errors.append("tool_arguments_invalid_json")
            else:
                if arguments != prompt["expected_arguments"]:
                    errors.append("tool_arguments_mismatch")

    return not errors, errors


def ns_delta_ms(later: int | None, earlier: int | None) -> float | None:
    if later is None or earlier is None:
        return None
    return (later - earlier) / 1_000_000.0


def append_result(path: Path, row: dict[str, Any]) -> None:
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key) for key in RESULT_COLUMNS})


def main() -> int:
    args = parse_args()
    if args.repetition < 1:
        raise ValueError("--repetition must be positive")

    protocol_path = Path(args.protocol).resolve()
    protocol, protocol_checksum = load_protocol(protocol_path)
    prompt = find_prompt(protocol, args.workload, args.prompt_id)
    deployment = protocol["deployments"][args.mode]
    request_config = protocol["request"]

    workload_short = {
        "plain_text": "plain",
        "reasoning_intensive": "reasoning",
        "tool_calling": "tool",
    }[args.workload]
    run_id = (
        f"v1-{args.mode}-{workload_short}-{args.prompt_id}-r{args.repetition:02d}"
    )
    paired_instance_id = f"v1-{workload_short}-{args.prompt_id}-r{args.repetition:02d}"

    root = Path(args.output_root).resolve()
    run_dir = root / "runs" / run_id
    if run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    raw_path = run_dir / "raw.jsonl"
    summary_path = run_dir / "summary.json"

    expected_service = deployment["service"]
    service_active = expected_service_is_active(expected_service)

    user_message = (
        f"Experiment instance: {paired_instance_id}\n\n{prompt['user']}"
    )
    max_tokens_key = (
        "benchmark_max_tokens" if args.run_type == "benchmark"
        else "profile_max_tokens"
    )

    payload: dict[str, Any] = {
        "model": request_config["model"],
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": request_config["temperature"],
        "top_p": request_config["top_p"],
        "seed": request_config["seed"],
        "max_tokens": request_config[max_tokens_key],
        "chat_template_kwargs": request_config["chat_template_kwargs"],
    }
    if args.workload == "tool_calling":
        payload.update({
            "tools": protocol["tools"],
            "tool_choice": protocol["workloads"][args.workload]["tool_choice"],
            "parallel_tool_calls": request_config["parallel_tool_calls"],
        })

    timestamps: dict[str, int | None] = {
        "request_start_ns": None,
        "first_output_ns": None,
        "first_reasoning_ns": None,
        "first_final_answer_ns": None,
        "first_tool_call_ns": None,
        "request_end_ns": None,
    }
    reasoning_parts: list[str] = []
    content_parts: list[str] = []
    tool_state: dict[int, dict[str, str]] = {}
    usage: dict[str, Any] = {}
    finish_reason: str | None = None
    request_error: str | None = None

    with raw_path.open("w", encoding="utf-8") as raw:
        append_jsonl(raw, {
            "type": "request",
            "run_id": run_id,
            "paired_instance_id": paired_instance_id,
            "protocol_sha256": protocol_checksum,
            "expected_service": expected_service,
            "service_active": service_active,
            "payload": payload,
        })

        marker(f"RUN_START:{run_id}", args.run_type)
        timestamps["request_start_ns"] = time.perf_counter_ns()

        try:
            with requests.post(
                request_config["url"],
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "X-Request-Id": run_id,
                },
                json=payload,
                stream=True,
                timeout=(10.0, args.timeout),
            ) as response:
                response.raise_for_status()
                event_index = 0
                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        continue

                    observed_ns = time.perf_counter_ns()
                    chunk = json.loads(data)
                    choice = (chunk.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    reasoning = delta.get("reasoning") or delta.get("reasoning_content")
                    content = delta.get("content")
                    tool_fragments = delta.get("tool_calls") or []

                    phase = "metadata"
                    if tool_fragments:
                        phase = "tool_call"
                    elif reasoning:
                        phase = "reasoning"
                    elif content:
                        phase = "final_answer"
                    elif choice.get("finish_reason"):
                        phase = "finish"
                    elif chunk.get("usage"):
                        phase = "usage"

                    if meaningful_delta(reasoning, content, tool_fragments):
                        if timestamps["first_output_ns"] is None:
                            timestamps["first_output_ns"] = observed_ns
                            marker(f"FIRST_OUTPUT:{run_id}", args.run_type)

                    if reasoning:
                        if timestamps["first_reasoning_ns"] is None:
                            timestamps["first_reasoning_ns"] = observed_ns
                            marker(f"FIRST_REASONING:{run_id}", args.run_type)
                        reasoning_parts.append(reasoning)
                        if args.run_type == "parser-validation":
                            print(reasoning, end="", flush=True)

                    if content:
                        if timestamps["first_final_answer_ns"] is None:
                            timestamps["first_final_answer_ns"] = observed_ns
                            marker(f"FIRST_FINAL:{run_id}", args.run_type)
                            if args.run_type == "parser-validation":
                                print("\n\n[FINAL]\n", end="", flush=True)
                        content_parts.append(content)
                        if args.run_type == "parser-validation":
                            print(content, end="", flush=True)

                    if tool_fragments:
                        if timestamps["first_tool_call_ns"] is None:
                            timestamps["first_tool_call_ns"] = observed_ns
                            marker(f"FIRST_TOOL_CALL:{run_id}", args.run_type)
                            if args.run_type == "parser-validation":
                                print("\n\n[TOOL CALL]\n", end="", flush=True)
                        merge_tool_calls(tool_state, tool_fragments)

                    if choice.get("finish_reason") is not None:
                        finish_reason = choice["finish_reason"]
                    if chunk.get("usage"):
                        usage = chunk["usage"]

                    event_index += 1
                    append_jsonl(raw, {
                        "type": "stream_event",
                        "index": event_index,
                        "timestamp_ns": observed_ns,
                        "phase": phase,
                        "chunk": chunk,
                    })

        except Exception as exc:
            request_error = f"{type(exc).__name__}: {exc}"
            append_jsonl(raw, {
                "type": "error",
                "timestamp_ns": time.perf_counter_ns(),
                "error": request_error,
            })
        finally:
            timestamps["request_end_ns"] = time.perf_counter_ns()
            marker(f"RUN_END:{run_id}", args.run_type)

    reasoning_text = "".join(reasoning_parts)
    final_text = "".join(content_parts)
    tool_calls = [tool_state[index] for index in sorted(tool_state)]

    boundary_target = (
        timestamps["first_tool_call_ns"]
        if args.workload == "tool_calling"
        else timestamps["first_final_answer_ns"]
    )
    phase_mapping_valid = bool(
        timestamps["first_reasoning_ns"] is not None and boundary_target is not None
    )

    output_valid, output_errors = validate_output(
        args.workload, prompt, final_text, tool_calls, finish_reason
    )
    benchmark_errors: list[str] = []
    if not service_active:
        benchmark_errors.append("expected_service_not_active")
    if request_error:
        benchmark_errors.append("http_or_stream_failure")
    benchmark_valid = not benchmark_errors

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    post_first_seconds = None
    output_tps = None
    if timestamps["first_output_ns"] is not None:
        post_first_seconds = (
            timestamps["request_end_ns"] - timestamps["first_output_ns"]
        ) / 1_000_000_000.0
    if completion_tokens is not None and post_first_seconds and post_first_seconds > 0:
        output_tps = max(completion_tokens - 1, 0) / post_first_seconds

    all_errors = benchmark_errors + ([] if phase_mapping_valid else ["phase_boundary_missing"]) + output_errors
    summary = {
        "run_id": run_id,
        "paired_instance_id": paired_instance_id,
        "protocol_version": protocol["protocol"]["version"],
        "protocol_sha256": protocol_checksum,
        "mode": args.mode,
        "workload": args.workload,
        "prompt_id": args.prompt_id,
        "repetition": args.repetition,
        "run_type": args.run_type,
        "timestamps_ns": timestamps,
        "timing_ms": {
            "time_to_first_output_ms": ns_delta_ms(timestamps["first_output_ns"], timestamps["request_start_ns"]),
            "time_to_first_final_output_ms": ns_delta_ms(boundary_target, timestamps["request_start_ns"]),
            "end_to_end_latency_ms": ns_delta_ms(timestamps["request_end_ns"], timestamps["request_start_ns"]),
            "reasoning_associated_duration_ms": ns_delta_ms(boundary_target, timestamps["first_reasoning_ns"]),
            "final_or_tool_associated_duration_ms": ns_delta_ms(timestamps["request_end_ns"], boundary_target),
        },
        "usage": usage,
        "output_tokens_per_second": output_tps,
        "finish_reason": finish_reason,
        "output": {
            "reasoning": reasoning_text,
            "final_answer": final_text,
            "tool_calls": tool_calls,
        },
        "validity": {
            "benchmark_valid": benchmark_valid,
            "phase_mapping_valid": phase_mapping_valid,
            "output_valid": output_valid,
            "invalid_reasons": all_errors,
        },
        "request_error": request_error,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.run_type == "benchmark":
        timing = summary["timing_ms"]
        append_result(root / "results.csv", {
            "run_id": run_id,
            "protocol_version": protocol["protocol"]["version"],
            "mode": args.mode,
            "workload": args.workload,
            "prompt_id": args.prompt_id,
            "repetition": args.repetition,
            "run_type": args.run_type,
            **timing,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "output_tokens_per_second": output_tps,
            "finish_reason": finish_reason,
            "benchmark_valid": benchmark_valid,
            "phase_mapping_valid": phase_mapping_valid,
            "output_valid": output_valid,
            "invalid_reasons": "|".join(all_errors),
        })

    print("\n")
    print(f"Run: {run_id}")
    print(f"Summary: {summary_path}")
    print(f"TTFO: {summary['timing_ms']['time_to_first_output_ms']} ms")
    print(f"E2E: {summary['timing_ms']['end_to_end_latency_ms']} ms")
    print(f"Valid: benchmark={benchmark_valid}, phase={phase_mapping_valid}, output={output_valid}")
    if all_errors:
        print("Issues:", ", ".join(all_errors))

    return 0 if benchmark_valid else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
