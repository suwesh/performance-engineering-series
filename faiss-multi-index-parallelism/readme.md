<div align="center"> <a href="https://suwesh.github.io/engineering-war-stories/006">⚔️Blog Post</a> | <a href="https://doi.org/10.5281/zenodo.22115696">📝Technical Report</a> </div>

### Analyzing Internal and External Parallelism in Multi-Index FAISS Retrieval: Threads, Processes, OpenMP and the Cost of Concurrency
__A CPU Performance Engineering Study.__<br>

This collection contains benchmark scripts, raw measurements, profiling statistics, and analysis artifacts for the performance-engineering study of a multi-index FAISS retrieval pipeline. Three independent retrieval sources were evaluated using sequential execution, thread-level parallelism through ThreadPoolExecutor, and process-level parallelism through ProcessPoolExecutor. Additional experiments were conducted using OMP_NUM_THREADS=1 to isolate the contribution of FAISS internal parallelism from externally managed concurrency. Execution time measurements and profiling data were collected to understand the performance implications of different execution models. The results demonstrate the relationship between retrieval workload granularity, internal OpenMP parallelism, external concurrency mechanisms, and parallel execution overhead.
<br>

Folder Structure:
```text

```
