import faiss
import time
from retrieval.models import to_embedder_uat # implementation specific imports
from services.retrieval_service import sourceA_index_path # implementation specific imports

index = faiss.read_index(sourceA_index_path) # path of .index file

Q = "<A retrieval query>"
Q_embed = to_embedder_uat(Q) # takes a string, returns the computed vector output from the embedding model
print(Q_embed.shape)

k = 10

# warmup
for _ in range(100):
    index.search(Q_embed, k)

print(f"faiss behaviour when faiss.omp_get_max_threads() = {faiss.omp_get_max_threads()}")

N = 10000
start = time.perf_counter_ns()
for _ in range(N):
    index.search( Q_embed, 10)
end = time.perf_counter_ns()
avg_latency_ns = (end-start)/N
print(f"Average Latency for Approach 1: {avg_latency_ns}")

"""Pros:
Minimizes timer overhead.
Standard HPC microbenchmark technique.
Much more stable for tiny operations.
Better when measuring microseconds and nanoseconds."""

times = []
for _ in range(N):
    start = time.perf_counter_ns()
    index.search(Q_embed, k)
    end = time.perf_counter_ns()
    times.append(end - start)
print("\nStatistics for approach 2:\n")
import statistics
print(f"Mean Latency (ns): {statistics.mean(times):.2f}")
print(f"Median Latency (ns): {statistics.median(times):.2f}")
print(f"Min Latency (ns): {min(times):.2f}")
print(f"Max Latency (ns): {max(times):.2f}")
print(f"Std Dev (ns): {statistics.stdev(times):.2f}")
sorted_times = sorted(times)
p95 = sorted_times[int(len(sorted_times) * 0.95)]
p99 = sorted_times[int(len(sorted_times) * 0.99)]
print(f"P95 Latency (ns): {p95:.2f}")
print(f"P99 Latency (ns): {p99:.2f}")
"""Pros:
Gives a latency distribution.
Lets you calculate p95/p99.
Lets you see outliers.
Cons:
Timer overhead becomes part of the measurement.
Can distort extremely small workloads."""
