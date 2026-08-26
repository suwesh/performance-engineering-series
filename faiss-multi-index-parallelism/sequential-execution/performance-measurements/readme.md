# Sequential Benchmark

Date: 2026-08-24

Branch:
profiling-faiss-sequential

Query:
How to create a new loan application?

Hardware:
CPU: AMD Ryzen 5 5500;
RAM: 32 GB DDR4@3200MHz

OS:
WSL - Ubuntu

Environment:
Python 3.12

FAISS Backend::
faiss-cpu==1.11.0.post1

Retrieval Sources with sizes:(109KB, 265KB, 565KB)

Execution Model:
Sequential

## Raw End-to-End Runs
Measured outside chatbot_kb_retriever() using time.perf_counter().
cmd>for i in {1..10}; do python benchmark_retrieval.py; done: combine in below
cProfiling tuna graph: Projects/chatbotkb_retrieval/profiling_evidences/retrieval_sequential.prof

## Stage Breakdown + Raw End-to-End Measurements
Measured inside sahayak_kb_retriever() using time.perf_counter().
Metrics:
- Embedder Stage Latency
- FAISS Retrieval Stage Latency
- Reranker Stage Latency

cmd>for i in {1..10}; do python benchmark_retrieval.py; done
for i in {1..10}; do python benchmark_retrieval.py; done
Embedder Stage: 0.3215s
source A search took: 0.000125s
source B search took: 0.000065s
source C search took: 0.000101s
FAISS searches Stage (with sequential search): 0.000322s
Reranker Stage: 3.5452s
Total Retrieval Time: 3.8673s
Embedder Stage: 0.2679s
source A search took: 0.000119s
source B search took: 0.000055s
source C search took: 0.000095s
FAISS searches Stage (with sequential search): 0.000299s
Reranker Stage: 2.4282s
Total Retrieval Time: 2.6966s
Embedder Stage: 0.5608s
source A search took: 0.000106s
source B search took: 0.000055s
source C search took: 0.000091s
FAISS searches Stage (with sequential search): 0.000281s
Reranker Stage: 2.5668s
Total Retrieval Time: 3.1281s
Embedder Stage: 0.2031s
source A search took: 0.000129s
source B search took: 0.000058s
source C search took: 0.000091s
FAISS searches Stage (with sequential search): 0.000307s
Reranker Stage: 1.4455s
Total Retrieval Time: 1.6491s
Embedder Stage: 0.6377s
source A search took: 0.000103s
source B search took: 0.000054s
source C search took: 0.000090s
FAISS searches Stage (with sequential search): 0.000276s
Reranker Stage: 1.8491s
Total Retrieval Time: 2.4873s
Embedder Stage: 0.5516s
source A search took: 0.000123s
source B search took: 0.000065s
source C search took: 0.000095s
FAISS searches Stage (with sequential search): 0.000312s
Reranker Stage: 1.3462s
Total Retrieval Time: 1.8983s
Embedder Stage: 0.2728s
source A search took: 0.000124s
source B search took: 0.000057s
source C search took: 0.000093s
FAISS searches Stage (with sequential search): 0.000302s
Reranker Stage: 1.2724s
Total Retrieval Time: 1.5456s
Embedder Stage: 0.1995s
source A search took: 0.000202s
source B search took: 0.000071s
source C search took: 0.000088s
FAISS searches Stage (with sequential search): 0.000388s
Reranker Stage: 1.6063s
Total Retrieval Time: 1.8064s
Embedder Stage: 0.3838s
source A search took: 0.000116s
source B search took: 0.000054s
source C search took: 0.000093s
FAISS searches Stage (with sequential search): 0.000304s
Reranker Stage: 1.9418s
Total Retrieval Time: 2.3262s
Embedder Stage: 0.2335s
source A search took: 0.000117s
source B search took: 0.000057s
source C search took: 0.000103s
FAISS searches Stage (with sequential search): 0.000306s
Reranker Stage: 2.2081s
Total Retrieval Time: 2.4421s

cProfiling tuna graph: Projects/sahayak_kb_retrieval/profiling_evidences/faiss_sequential.prof

## Observations

1. Sequential retrieval completed in approximately 0.28-0.39 ms across the measured runs.

2. Individual source retrieval latencies were consistently below 0.25 ms:
   - Source A: ~0.10-0.20 ms
   - Source B: ~0.05-0.07 ms
   - Source C: ~0.08-0.10 ms

3. Similar to the multithreaded implementation, embedding and reranking dominated end-to-end latency.

4. The reranking stage remained the largest contributor to overall retrieval time.

5. End-to-end latency variability was primarily driven by model inference service response times rather than FAISS retrieval performance.

6. FAISS retrieval latency in the sequential implementation remained several orders of magnitude lower than embedding and reranking latency.

# controlled FAISS runtime:
(env3.12) suwesh@HHFD0000524:~/Projects/sahayak_kb_retrieval$ export OMP_NUM_THREADS=1
(env3.12) suwesh@HHFD0000524:~/Projects/sahayak_kb_retrieval$ for i in {1..10}; do python benchmark_retrieval.py; done

Embedder Stage: 0.0496s
controlled faiss internal threading source A search took: 0.000230s
controlled faiss internal threading source B search took: 0.000098s
controlled faiss internal threading source C search took: 0.000148s
controlled internal threading FAISS searches Stage (with sequential search): 0.000837s
Reranker Stage: 0.8643s
Total Retrieval Time: 0.9150s
Embedder Stage: 0.0290s
controlled faiss internal threading source A search took: 0.000174s
controlled faiss internal threading source B search took: 0.000068s
controlled faiss internal threading source C search took: 0.000107s
controlled internal threading FAISS searches Stage (with sequential search): 0.000664s
Reranker Stage: 0.7606s
Total Retrieval Time: 0.7905s
Embedder Stage: 0.0288s
controlled faiss internal threading source A search took: 0.000221s
controlled faiss internal threading source B search took: 0.000067s
controlled faiss internal threading source C search took: 0.000170s
controlled internal threading FAISS searches Stage (with sequential search): 0.000848s
Reranker Stage: 0.7632s
Total Retrieval Time: 0.7931s
Embedder Stage: 0.0287s
controlled faiss internal threading source A search took: 0.000245s
controlled faiss internal threading source B search took: 0.000119s
controlled faiss internal threading source C search took: 0.000144s
controlled internal threading FAISS searches Stage (with sequential search): 0.001032s
Reranker Stage: 0.7384s
Total Retrieval Time: 0.7684s
Embedder Stage: 0.0325s
controlled faiss internal threading source A search took: 0.000321s
controlled faiss internal threading source B search took: 0.000176s
controlled faiss internal threading source C search took: 0.000177s
controlled internal threading FAISS searches Stage (with sequential search): 0.006909s
Reranker Stage: 0.8708s
Total Retrieval Time: 0.9107s
Embedder Stage: 0.0272s
controlled faiss internal threading source A search took: 0.000306s
controlled faiss internal threading source B search took: 0.000112s
controlled faiss internal threading source C search took: 0.000131s
controlled internal threading FAISS searches Stage (with sequential search): 0.000940s
Reranker Stage: 0.8525s
Total Retrieval Time: 0.8808s
Embedder Stage: 0.0264s
controlled faiss internal threading source A search took: 0.000168s
controlled faiss internal threading source B search took: 0.000100s
controlled faiss internal threading source C search took: 0.000137s
controlled internal threading FAISS searches Stage (with sequential search): 0.007929s
Reranker Stage: 0.8283s
Total Retrieval Time: 0.8629s
Embedder Stage: 0.0309s
controlled faiss internal threading source A search took: 0.000189s
controlled faiss internal threading source B search took: 0.000073s
controlled faiss internal threading source C search took: 0.000124s
controlled internal threading FAISS searches Stage (with sequential search): 0.000803s
Reranker Stage: 0.8909s
Total Retrieval Time: 0.9229s
Embedder Stage: 0.0293s
controlled faiss internal threading source A search took: 0.000278s
controlled faiss internal threading source B search took: 0.000070s
controlled faiss internal threading source C search took: 0.000088s
controlled internal threading FAISS searches Stage (with sequential search): 0.000734s
Reranker Stage: 0.7766s
Total Retrieval Time: 0.8069s
Embedder Stage: 0.0267s
controlled faiss internal threading source A search took: 0.000177s
controlled faiss internal threading source B search took: 0.000069s
controlled faiss internal threading source C search took: 0.000110s
controlled internal threading FAISS searches Stage (with sequential search): 0.000717s
Reranker Stage: 0.8043s
Total Retrieval Time: 0.8319s
