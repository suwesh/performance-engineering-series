# Capture 1: AR gemv2T_kernel_val
## Terminal 0: stop the controlled services
`sudo systemctl stop prof-gemma4vllm.service` <br>
`sudo systemctl stop prof-gemma4vllm-mtp.service` <br>

`ss -lntp | grep ':8000' || true` <br>
`nvidia-smi` <br>


Port 8000 should be free before proceeding.

## Terminal 1: launch normal vLLM through NCU
`NCU="/usr/local/NVIDIA-Nsight-Compute-2026.2/ncu"` <br>

`cd /home/suwesh` <br>
```text
sudo env \
  HOME=/home/suwesh \
  XDG_CACHE_HOME=/home/suwesh/.cache \
  PYTHONUNBUFFERED=1 \
  PATH=/home/suwesh/env312-vllm024/bin:/home/suwesh/.local/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin \
  "$NCU" \
  --mode launch \
  --target-processes all \
  /home/suwesh/env312-vllm024/bin/python \
  -m vllm.entrypoints.openai.api_server \
  --model /home/suwesh/models/gemma4-w4a16ct \
  --served-model-name google/gemma-4-e4b \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --gpu-memory-utilization 0.80 \
  --max-model-len 8192 \
  --enable-chunked-prefill \
  --max-num-batched-tokens 2048 \
  --max-num-seqs 1 \
  --kv-cache-dtype bfloat16 \
  --enable-prefix-caching \
  --enable-auto-tool-choice \
  --tool-call-parser gemma4 \
  --reasoning-parser gemma4 \
  --generation-config vllm \
  --chat-template /home/suwesh/models/gemma4-w4a16ct/tool_chat_template_gemma4.jinja \
  --chat-template-content-format openai
```

Terminal 1 should print something similar to:

==PROF== Waiting for profiler to attach on ports ...

## Terminal 2: attach and configure AR kernel collection
`NCU="/usr/local/NVIDIA-Nsight-Compute-2026.2/ncu"` <br>
```text
sudo "$NCU" \
  --mode attach \
  --set detailed \
  --kernel-name 'regex:gemv2T_kernel_val' \
  --launch-skip 100 \
  --launch-count 1 \
  --force-overwrite \
  --export /home/suwesh/gemv_reasoning_ncu_001
```

Do not add --target-processes all to the attach command. In the previously successful workflow, that option belonged to the launch command, while the attach frontend discovered the waiting application.

## Terminal 3: wait for health, then send one request

After Terminal 2 attaches, vLLM initialization should continue.
```text
until curl -fsS http://127.0.0.1:8000/health >/dev/null; do
  echo "Waiting for NCU-launched normal vLLM..."
  sleep 2
done
```

Then:

`cd /home/suwesh/gpu-profiling` <br>
```text
/home/suwesh/env312-vllm024/bin/python gpu_prof_client.py \
  --mode normal \
  --workload reasoning_intensive \
  --prompt-id reasoning_001 \
  --repetition 120 \
  --run-type profile \
  --protocol protocol_v1.2.yaml \
  --output-root profile_client_runs/ncu
```

Expected NCU output:

==PROF== Profiling "gemv2T_kernel_val...": ...


Expected report:

/home/suwesh/gemv_reasoning_ncu_001.ncu-rep

Finish the AR capture

Wait until Terminal 2 returns to the shell and the report exists:

`ls -lh /home/suwesh/gemv_reasoning_ncu_001.ncu-rep` <br>

Fix ownership:

`sudo chown suwesh:suwesh /home/suwesh/gemv_reasoning_ncu_001.ncu-rep` <br>

Then stop Terminal 1 with Ctrl+C and confirm cleanup:

`pgrep -af 'vllm.entrypoints.openai.api_server|VLLM::EngineCore' || true` <br>
`ss -lntp | grep ':8000' || true` <br>
`nvidia-smi`

# Capture 2: MTP BF16 GEMM

Repeat the same workflow after confirming port 8000 and GPU memory are free.

## Terminal 1: launch MTP vLLM through NCU
`NCU="/usr/local/NVIDIA-Nsight-Compute-2026.2/ncu"` <br>

`cd /home/suwesh` <br>
```text
sudo env \
  HOME=/home/suwesh \
  XDG_CACHE_HOME=/home/suwesh/.cache \
  PYTHONUNBUFFERED=1 \
  PATH=/home/suwesh/env312-vllm024/bin:/home/suwesh/.local/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin \
  "$NCU" \
  --mode launch \
  --target-processes all \
  /home/suwesh/env312-vllm024/bin/python \
  -m vllm.entrypoints.openai.api_server \
  --model /home/suwesh/models/gemma4-w4a16ct \
  --served-model-name google/gemma-4-e4b \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --gpu-memory-utilization 0.80 \
  --max-model-len 8192 \
  --enable-chunked-prefill \
  --max-num-batched-tokens 2048 \
  --max-num-seqs 1 \
  --kv-cache-dtype bfloat16 \
  --enable-prefix-caching \
  --enable-auto-tool-choice \
  --tool-call-parser gemma4 \
  --reasoning-parser gemma4 \
  --generation-config vllm \
  --chat-template /home/suwesh/models/gemma4-w4a16ct/tool_chat_template_gemma4.jinja \
  --chat-template-content-format openai \
  --speculative-config '{"method":"mtp","model":"/home/suwesh/models/gemma4-drafter","num_speculative_tokens":2}'
```
## Terminal 2: attach and configure GEMM collection
`NCU="/usr/local/NVIDIA-Nsight-Compute-2026.2/ncu"` <br>
```text
sudo "$NCU" \
  --mode attach \
  --set detailed \
  --kernel-name 'regex:^ampere_bf16_s16816gemm_bf16_64x64_ldg8_f2f_stages_64x6_tn$' \
  --launch-skip 100 \
  --launch-count 1 \
  --force-overwrite \
  --export /home/suwesh/gemm_reasoning_ncu_001
```
## Terminal 3: wait for health and send the MTP request
```text
until curl -fsS http://127.0.0.1:8000/health >/dev/null; do
  echo "Waiting for NCU-launched MTP vLLM..."
  sleep 2
done
```

Then:<br>

`cd /home/suwesh/gpu-profiling` <br>
```text
/home/suwesh/env312-vllm024/bin/python gpu_prof_client.py \
  --mode mtp \
  --workload reasoning_intensive \
  --prompt-id reasoning_001 \
  --repetition 120 \
  --run-type profile \
  --protocol protocol_v1.2.yaml \
  --output-root profile_client_runs/ncu
```

Expected report:

/home/suwesh/gemm_reasoning_ncu_001.ncu-rep

Finish the MTP capture <br>
`ls -lh /home/suwesh/gemm_reasoning_ncu_001.ncu-rep` <br>

`sudo chown suwesh:suwesh /home/suwesh/gemm_reasoning_ncu_001.ncu-rep` <br>


Stop Terminal 1 with Ctrl+C, then verify cleanup.

Why --launch-skip 100?

The previous FMHA learning capture used a one-kernel filter and --launch-count 1. Here, GEMV and GEMM may also execute during vLLM initialization. Skipping the first 100 matching launches makes it more likely that the captured invocation belongs to repeated request execution rather than startup activity.

The reasoning request has hundreds of steady-state dominant-kernel invocations, so skipping 100 still leaves many eligible matches.

If no report is generated because fewer than 101 matching invocations occurred, rerun with:

--launch-skip 10


Do not change the filter and skip value simultaneously.

Do we need external warm-ups?

No separate warm-up request before capture.

Because NCU is already attached and filtering kernel launches, a warm-up request would itself consume matching launches and could trigger the report. Instead:

- launch under NCU;
- attach with --launch-skip 100;
- allow vLLM initialization to complete;
- send the single reasoning request;
- capture one later matching invocation.
- Final expected artifacts
- /home/suwesh/gemv_reasoning_ncu_001.ncu-rep
- /home/suwesh/gemm_reasoning_ncu_001.ncu-rep
