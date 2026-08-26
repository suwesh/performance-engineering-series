# Multithreading Benchmark

Date: 2026-08-24

Branch:
profiling-faiss-multithreading

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
ThreadPoolExecutor (3 worker threads)

## Raw End-to-End Runs
Measured outside chatbot_kb_retriever() using time.perf_counter().
cmd>for i in {1..10}; do python benchmark_retrieval.py; done
Total Retrieval Time: 1.4032s
Total Retrieval Time: 1.3841s
Total Retrieval Time: 1.2903s
Total Retrieval Time: 1.2779s
Total Retrieval Time: 2.6766s
Total Retrieval Time: 1.3720s
Total Retrieval Time: 1.8829s
Total Retrieval Time: 1.7627s
Total Retrieval Time: 1.7438s
Total Retrieval Time: 2.3106s

cProfiling tuna graph: Projects/chatbot_kb_retrieval/profiling_evidences/retrieval_threadpool.prof

## Stage Breakdown Measurements
Measured inside chatbot_kb_retriever() using time.perf_counter().
Metrics:
- Embedder Stage Latency
- FAISS Retrieval Stage Latency
- Reranker Stage Latency

cmd>for i in {1..10}; do python benchmark_retrieval.py; done
Embedder Stage: 0.4318s
FAISS searches Stage (with multithreading): 0.001309s
Reranker Stage: 1.4992s
Total Retrieval Time: 1.9327s
Embedder Stage: 0.1644s
FAISS searches Stage (with multithreading): 0.001407s
Reranker Stage: 1.5058s
Total Retrieval Time: 1.6719s
Embedder Stage: 0.2391s
FAISS searches Stage (with multithreading): 0.001534s
Reranker Stage: 1.5260s
Total Retrieval Time: 1.7669s
Embedder Stage: 0.2177s
FAISS searches Stage (with multithreading): 0.001296s
Reranker Stage: 1.3937s
Total Retrieval Time: 1.6130s
Embedder Stage: 0.1851s
FAISS searches Stage (with multithreading): 0.001542s
Reranker Stage: 1.2609s
Total Retrieval Time: 1.4479s
Embedder Stage: 0.3598s
FAISS searches Stage (with multithreading): 0.001301s
Reranker Stage: 2.6117s
Total Retrieval Time: 2.9731s
Embedder Stage: 0.2026s
FAISS searches Stage (with multithreading): 0.001555s
Reranker Stage: 1.3913s
Total Retrieval Time: 1.5958s
Embedder Stage: 0.1789s
FAISS searches Stage (with multithreading): 0.001161s
Reranker Stage: 1.5858s
Total Retrieval Time: 1.7662s
Embedder Stage: 0.2110s
FAISS searches Stage (with multithreading): 0.001352s
Reranker Stage: 1.3513s
Total Retrieval Time: 1.5639s
Embedder Stage: 0.1749s
FAISS searches Stage (with multithreading): 0.001115s
Reranker Stage: 1.3203s
Total Retrieval Time: 1.4968s

cProfiling tuna graph: Projects/chatbot_kb_retrieval/profiling_evidences/faiss_threadpool.prof

## Observations

1. FAISS retrieval latency appears extremely small compared to embedding and reranking latency.

2. The multithreaded retrieval stage consistently completed in approximately 1-2 ms across all runs.

3. Reranking latency ranged from approximately 1.26 s to 2.61 s during the measured runs.

4. End-to-end retrieval latency variability appears primarily driven by embedding and reranking service response times rather than FAISS retrieval time.

5. Initial cProfile analysis correctly identified network-bound HTTP requests as the dominant contributors to total retrieval latency.

6. The measured FAISS retrieval stage completed in approximately 1.1-1.6 ms across runs.

7. The retrieval stage was too short-lived for meaningful standalone cProfile visualization, with Tuna reporting near-zero cumulative execution time.

# controlled FAISS runtime:
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ export OMP_NUM_THREADS=1
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ for i in {1..10}; do python benchmark_retrieval.py; done

Embedder Stage: 0.0737s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001622s
Reranker Stage: 0.7540s
Total Retrieval Time: 0.8296s
Embedder Stage: 0.0295s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001251s
Reranker Stage: 0.7677s
Total Retrieval Time: 0.7987s
Embedder Stage: 0.0290s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001449s
Reranker Stage: 0.8000s
Total Retrieval Time: 0.8308s
Embedder Stage: 0.0269s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001362s
Reranker Stage: 0.8391s
Total Retrieval Time: 0.8678s
Embedder Stage: 0.0312s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001526s
Reranker Stage: 0.7602s
Total Retrieval Time: 0.7933s
Embedder Stage: 0.0294s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001809s
Reranker Stage: 0.7835s
Total Retrieval Time: 0.8151s
Embedder Stage: 0.0284s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001372s
Reranker Stage: 0.7999s
Total Retrieval Time: 0.8300s
Embedder Stage: 0.0246s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001417s
Reranker Stage: 0.6993s
Total Retrieval Time: 0.7256s
Embedder Stage: 0.0265s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001587s
Reranker Stage: 0.8286s
Total Retrieval Time: 0.8570s
Embedder Stage: 0.0212s
controlled faiss internal threading, FAISS searches Stage (with external multithreading): 0.001324s
Reranker Stage: 0.8056s
Total Retrieval Time: 0.8284s
