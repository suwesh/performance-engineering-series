# NVIDIA Nsight Systems Captures

### <a href="https://www.kaggle.com/datasets/suwesh/beneath-the-tokens-gpu-profiling">gpu-profiling/profiles/nsys/</a>
Matched NVIDIA Nsight Systems captures for autoregressive and MTP decoding across the three workloads.

Artifacts may include:

- Nsight Systems report files
- SQLite exports
- profiler logs
- NVTX-aligned request evidence
- derived kernel and CUDA Graph summaries

The SQLite exports enable reproducible inspection of kernel launches, CUDA Graph executions, timing intervals, and kernel composition without relying only on screenshots.

### <a href="https://www.kaggle.com/datasets/suwesh/beneath-the-tokens-gpu-profiling">gpu-profiling/profile_client_runs/nsys/</a>
Client-side records generated during profiler-instrumented requests.

### <a href="https://www.kaggle.com/code/suwesh/nsys-rq3-analysis-ipynb">nsys_rq3_analysis.ipynb</a> and <a href="https://www.kaggle.com/datasets/suwesh/beneath-the-tokens-gpu-profiling">gpu-profiling/result-analysis/</a>
Analysis scripts, derived tables, notebooks, and supporting outputs used to produce the results reported in the technical report.
