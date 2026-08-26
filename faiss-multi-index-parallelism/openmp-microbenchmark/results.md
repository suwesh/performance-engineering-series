Results:
# 1. Default OpenMP MAX Threads configuration
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ python script.py<br>
torch.Size([1, 1024])<br>
faiss behaviour when faiss.omp_get_max_threads() = 12<br>
Average Latency for Approach 1: 18602.4974<br>
<br>
Statistics for approach 2:<br>
<br>
Mean Latency (ns): 21404.83<br>
Median Latency (ns): 17383.00<br>
Min Latency (ns): 16451.00<br>
Max Latency (ns): 341141.00<br>
Std Dev (ns): 12153.43<br>
P95 Latency (ns): 31409.00<br>
P99 Latency (ns): 67486.00<br>

# 2. Controlled OpenMP MAX Threads configuration
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ export OMP_NUM_THREADS=1<br>
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ python script.py<br>
torch.Size([1, 1024])<br>
faiss behaviour when faiss.omp_get_max_threads() = 1<br>
Average Latency for Approach 1: 21912.7643<br>
<br>
Statistics for approach 2:<br>
<br>
Mean Latency (ns): 19521.74<br>
Median Latency (ns): 17082.00<br>
Min Latency (ns): 16380.00<br>
Max Latency (ns): 366677.00<br>
Std Dev (ns): 11928.04<br>
P95 Latency (ns): 28774.00<br>
P99 Latency (ns): 45155.00<br>
