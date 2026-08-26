Results:
# 1. Default OpenMP MAX Threads configuration
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ python script.py  
torch.Size([1, 1024])
faiss behaviour when faiss.omp_get_max_threads() = 12
Average Latency for Approach 1: 18602.4974
Statistics for approach 2:

Mean Latency (ns): 21404.83
Median Latency (ns): 17383.00
Min Latency (ns): 16451.00
Max Latency (ns): 341141.00
Std Dev (ns): 12153.43
P95 Latency (ns): 31409.00
P99 Latency (ns): 67486.00

# 2. Controlled OpenMP MAX Threads configuration
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ export OMP_NUM_THREADS=1
(env3.12) suwesh@HHFD0000524:~/Projects/chatbot_kb_retrieval$ python script.py
torch.Size([1, 1024])
faiss behaviour when faiss.omp_get_max_threads() = 1
Average Latency for Approach 1: 21912.7643

Statistics for approach 2:

Mean Latency (ns): 19521.74
Median Latency (ns): 17082.00
Min Latency (ns): 16380.00
Max Latency (ns): 366677.00
Std Dev (ns): 11928.04
P95 Latency (ns): 28774.00
P99 Latency (ns): 45155.00
