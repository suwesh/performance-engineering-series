# System Under Test
Captured: 2026-09-10T16:13:09+05:30

## OS:
Red Hat Enterprise Linux release 9.8 (Plow)
Kernel: Linux lclphcbota02 5.14.0-687.45.1.el9_8.x86_64 #1 SMP PREEMPT_DYNAMIC Tue Sep 1 21:20:37 EDT 2026 x86_64 x86_64 x86_64 GNU/Linux

## GPU:
```text
Thu Sep 10 16:13:09 2026
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 595.71.05              Driver Version: 595.71.05      CUDA Version: 13.2     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA A10G                    Off |   00000000:00:1E.0 Off |                    0 |
|  0%   38C    P0             64W /  300W |   18483MiB /  23028MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
```

## Python
Python 3.12.14<br>
Packages:
```text
Name: vllm
Version: 0.24.0
Summary: A high-throughput and memory-efficient inference and serving engine for LLMs
Home-page: https://github.com/vllm-project/vllm
Author: vLLM Team
Author-email: 
License-Expression: Apache-2.0
Location: /home/cbotadmin/env312-vllm024/lib64/python3.12/site-packages
Requires: aiohttp, anthropic, apache-tvm-ffi, blake3, cachetools, cbor2, cloudpickle, compressed-tensors, depyf, diskcache, einops, fastapi, fastsafetensors, filelock, flashinfer-cubin, flashinfer-python, humming-kernels, ijson, jsonschema, lark, llguidance, lm-format-enforcer, mcp, mistral_common, model-hosting-container-standards, msgspec, ninja, numba, numpy, nvidia-cudnn-frontend, nvidia-cutlass-dsl, openai, openai-harmony, opencv-python-headless, opentelemetry-api, opentelemetry-exporter-otlp, opentelemetry-sdk, opentelemetry-semantic-conventions-ai, outlines_core, partial-json-parser, pillow, prometheus-fastapi-instrumentator, prometheus_client, protobuf, psutil, py-cpuinfo, pybase64, pydantic, python-json-logger, pyyaml, pyzmq, quack-kernels, regex, requests, safetensors, sentencepiece, setproctitle, setuptools, six, starlette, tiktoken, tilelang, tokenizers, tokenspeed-mla, torch, torchaudio, torchvision, tqdm, transformers, typing_extensions, watchfiles, xgrammar
Required-by: 
---
Name: torch
Version: 2.11.0+cu130
Summary: Tensors and Dynamic neural networks in Python with strong GPU acceleration
Home-page: https://pytorch.org
Author: 
Author-email: PyTorch Team <packages@pytorch.org>
License: BSD-3-Clause
Location: /home/cbotadmin/env312-vllm024/lib64/python3.12/site-packages
Requires: cuda-bindings, cuda-toolkit, filelock, fsspec, jinja2, networkx, nvidia-cudnn-cu13, nvidia-cusparselt-cu13, nvidia-nccl-cu13, nvidia-nvshmem-cu13, setuptools, sympy, triton, typing-extensions
Required-by: compressed-tensors, flashinfer-python, humming-kernels, quack-kernels, tilelang, tokenspeed-mla, torch_c_dlpack_ext, torchvision, vllm, xgrammar
---
Name: nvtx
Version: 0.2.16
Summary: Python NVTX - Python code annotation library
Home-page: https://github.com/NVIDIA/NVTX
Author: NVIDIA Corporation
Author-email: 
License-Expression: Apache-2.0 WITH LLVM-exception
Location: /home/cbotadmin/env312-vllm024/lib64/python3.12/site-packages
Requires: 
Required-by: 
```
## Nsight Systems:
NVIDIA Nsight Systems version 2026.4.1.191-264138605071v0

## Nsight Compute:
NVIDIA (R) Nsight Compute Command Line Profiler<br>
Copyright (c) 2018-2026 NVIDIA Corporation<br>
Version 2026.2.1.0 (build 38286902) (public-release)<br>

# Models
## Autoregressive decoder and Speculative decoding verifier
<a href="https://huggingface.co/google/gemma-4-E4B-it-qat-w4a16-ct">google/gemma-4-E4B-it-qat-w4a16-ct</a> 
## Dedicated Speculative drafter
<a href="https://huggingface.co/google/gemma-4-E4B-it-assistant">google/gemma-4-E4B-it-assistant</a>

# Experimental Procedure

## Benchmarking
Autoregressive decoding: `./run_primary_benchmark.sh normal`<br>
Output log: run_primary_benchmark_normal.log<br>
<br>
Speculative decoding: `./run_primary_benchmark.sh mtp`<br>
Output log: run_primary_benchmark_mtp.log
## Profiling
### NVIDIA Nsight Systems
Autoregressive decoding: `./run_nsys_profile_w_cuda.sh normal <workload> <prompt_id> <run_id>`<br>
Outputs: 
<br>
Speculative decoding: `./run_nsys_profile_w_cuda.sh mtp <workload> <prompt_id> <run_id>`<br>
Outputs: 
