# Multicore Benchmark

Date: 2026-08-24

Branch:
profiling-faiss-multicore

Query:
How to create a new loan application?

Hardware: CPU: AMD Ryzen 5 5500; RAM: 32 GB DDR4@3200MHz

OS:
WSL - Ubuntu

Environment:
Python 3.12

FAISS Backend::
faiss-cpu==1.11.0.post1

Retrieval Sources with sizes:(109KB, 265KB, 565KB)

Execution Model:
Multicore / Parallel processing -> from concurrent.futures import ProcessPoolExecutor

## Raw End-to-End Runs
Measured outside chatbot_kb_retriever() using time.perf_counter().
cmd>for i in {1..10}; do python benchmark_retrieval.py; done: combine in below
cProfiling tuna graph: Projects/chatbot_kb_retrieval/profiling_evidences/retrieval_multicore_ProcessPoolExecutor.prof

## Stage Breakdown + Raw End-to-End Measurements
Measured inside chatbot_kb_retriever() using time.perf_counter().
Metrics:
- Embedder Stage Latency
- FAISS Retrieval Stage Latency
- Reranker Stage Latency

cmd>for i in {1..10}; do python benchmark_retrieval.py; done
for i in {1..10}; do python benchmark_retrieval.py; done
Embedder Stage: 0.0715s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.074790s
Reranker Stage: 0.8332s
Total Retrieval Time: 0.9799s
Embedder Stage: 0.0351s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.067588s
Reranker Stage: 0.7639s
Total Retrieval Time: 0.8670s
Embedder Stage: 0.0292s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.064069s
Reranker Stage: 0.7977s
Total Retrieval Time: 0.8913s
Embedder Stage: 0.0271s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.067619s
Reranker Stage: 0.7547s
Total Retrieval Time: 0.8498s
Embedder Stage: 0.0329s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.070284s
Reranker Stage: 0.8422s
Total Retrieval Time: 0.9458s
Embedder Stage: 0.0293s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.065926s
Reranker Stage: 0.8628s
Total Retrieval Time: 0.9588s
Embedder Stage: 0.0291s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.066843s
Reranker Stage: 0.8007s
Total Retrieval Time: 0.8970s
Embedder Stage: 0.0304s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.067585s
Reranker Stage: 0.8257s
Total Retrieval Time: 0.9240s
Embedder Stage: 0.0294s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.068062s
Reranker Stage: 0.7291s
Total Retrieval Time: 0.8269s
Embedder Stage: 0.0252s
FAISS searches Stage (with multicore: ProcessPoolExecutor search): 0.081516s
Reranker Stage: 0.7500s
Total Retrieval Time: 0.8572s

cProfiling tuna graph: Projects/chatbot_kb_retrieval/profiling_evidences/faiss_multicore_ProcessPoolExecutor.prof

## Observations
1. ProcessPoolExecutor successfully executed the retrieval workload without serialization failures.

2. Contrary to the original hypothesis, process-based parallelism produced the slowest retrieval latency of all tested approaches.

3. The FAISS retrieval stage increased from approximately 0.3 ms in the sequential implementation to approximately 65-80 ms when executed using ProcessPoolExecutor.

4. Process creation, scheduling, serialization, and inter-process communication overhead dominated the retrieval workload.

5. The retrieval workload was too small to amortize multiprocessing overhead.

6. Sequential execution remained the fastest implementation among the tested approaches.

# controlled FAISS runtime:
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ export OMP_NUM_THREADS=1
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ for i in {1..10}; do python benchmark_retrieval.py; done

Embedder Stage: 0.0843s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.077597s
Reranker Stage: 0.8239s
Total Retrieval Time: 0.9864s
Embedder Stage: 0.0397s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.067683s
Reranker Stage: 0.8546s
Total Retrieval Time: 0.9624s
Embedder Stage: 0.0303s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.064442s
Reranker Stage: 0.8133s
Total Retrieval Time: 0.9084s
Embedder Stage: 0.0273s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.068719s
Reranker Stage: 0.7999s
Total Retrieval Time: 0.8963s
Embedder Stage: 0.0256s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.067834s
Reranker Stage: 0.7891s
Total Retrieval Time: 0.8830s
Embedder Stage: 0.0288s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.063153s
Reranker Stage: 0.8547s
Total Retrieval Time: 0.9471s
Embedder Stage: 0.0303s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.072380s
Reranker Stage: 0.8016s
Total Retrieval Time: 0.9047s
Embedder Stage: 0.0309s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.073719s
Reranker Stage: 0.8589s
Total Retrieval Time: 0.9639s
Embedder Stage: 0.0305s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.160209s
Reranker Stage: 0.8360s
Total Retrieval Time: 1.0273s
Embedder Stage: 0.0270s
controlled faiss internal threading FAISS searches Stage (with external multicore: ProcessPoolExecutor search): 0.070618s
Reranker Stage: 0.8419s
Total Retrieval Time: 0.9399s
