from retrieval.models import to_embedder_uat, to_reranker # implementation specific imports for embedding and reranking functions
import time
import cProfile

#similarity search seperate functions
def similar_docs(k, I, D, sentences, texts):##function only for printing in terminal
    print(f"Top {k} similar results for query- {sentences}:")
    for i in range(k):
        print(f"Document {I[0][i]} with distance {D[0][i]}")
        print(f"Text: {texts[I[0][i]]}")
def similarity_search_faqs(vector_embeddings, sentences, num_searchresults, index, texts): # source A
    k = num_searchresults
    D, I =  index.search(vector_embeddings, k)
    #collecting top results
    results = []
    for i in range(min(num_searchresults, len(I[0]))):
        results.append({
            "text": texts[I[0][i]],
            "distance": D[0][i]
        })
    #similar_docs(k, I, D, sentences, texts)
    return results
def similarity_search_video(vector_embeddings, sentences, num_searchresults, index, texts): #source B
    k = num_searchresults
    D, I =  index.search(vector_embeddings, k)
    #collecting top results
    results = []
    for i in range(min(num_searchresults, len(I[0]))):
        results.append({
            "text": texts[I[0][i]],
            "distance": D[0][i]
        })
    #similar_docs(k, I, D, sentences, texts)
    return results
## graph rag for manuals
def faiss_search_manuals_chunk(q_embeddings, top_k, index, metadata): # source C
    scores, ids = index.search(q_embeddings, top_k)
    chunks = []
    for vid, score in zip(ids[0], scores[0]):
        if vid < 0:# faiss did not find any similar chunks, distance to the found chunks are infinity hence it assigns id = -1, so to filter them we add this condition
            continue
        chunks.append({
            "vector_id": int(vid),# faiss id
            "unit_id": metadata[vid]["unit_id"],
            "text": metadata[vid]["text"], # get chunk text from metadata
            "score": float(score)
        })
    return chunks
def expand_chunks_to_unit(chunks):
    seen = set()
    ordered_unit_ids = []
    for c in chunks:
        unit_id = c["unit_id"]
        if unit_id not in seen:
            seen.add(unit_id)
            ordered_unit_ids.append(unit_id)
    return ordered_unit_ids
def expand_units_with_neighbors(unit_ids, units_by_id):# procedural adjacency expansion
    expanded = []
    seen = set()
    for uid in unit_ids:
        if uid not in units_by_id:
            continue
        u = units_by_id[uid]
        # previous
        pid = u.get("prev_unit_id")
        if pid and pid in units_by_id and pid not in seen:
            expanded.append(units_by_id[pid])
            seen.add(pid)
        # self
        if uid not in seen:
            expanded.append(u)
            seen.add(uid)
        # next
        nid = u.get("next_unit_id")
        if nid and nid in units_by_id and nid not in seen:
            expanded.append(units_by_id[nid])
            seen.add(nid)
    return expanded
def serialize_manual_units(units):
    parts = []
    for u in units:
        parts.append(f"### {u['title']}")
        if u.get("paragraphs"):
            parts.extend(u["paragraphs"])
        if u.get("steps"):
            parts.extend(u["steps"])
        if u.get("rules"):
            parts.extend(u["rules"])
    return "\n".join(parts)

# change inside here to toggle embedding and reranking to UAT/PROD 
# CHECK N CHANGE EMBEDDER FUNCTION IN app.py>clip_generator also as it uses seperately
def chatbot_kb_retriever(sentences, rag_resources):
    index_faqs = rag_resources["index_faqs"]
    texts_faqs = rag_resources["texts_faqs"]
    index_video = rag_resources["index_video"]
    texts_video = rag_resources["texts_video"]
    index_manuals = rag_resources["index_manuals"]
    metadata_manuals = rag_resources["metadata_manuals"]
    units_by_id_manuals = rag_resources["units_by_id_manuals"]
    embed_start = time.perf_counter()
    vector_embeddings = to_embedder_uat(sentences).numpy()#query embeddings - already l2 normalized embeddings returned by embedder
    embed_end = time.perf_counter()
    print(f"Embedder Stage: {embed_end - embed_start:.4f}s")
    # create a list containing functions and each function's tuple of arguments (fun, (*args))
    search_tasks = [
        (similarity_search_faqs, (vector_embeddings, sentences, 10, index_faqs, texts_faqs)),
        (similarity_search_video, (vector_embeddings, sentences, 5, index_video, texts_video)),
        (faiss_search_manuals_chunk, (vector_embeddings, 10, index_manuals, metadata_manuals)),
    ]
    search_start = time.perf_counter()
    search_profiler = cProfile.Profile()
    search_profiler.enable()
    faqs_results = similarity_search_faqs(vector_embeddings, sentences, 10, index_faqs, texts_faqs)
    #enda = time.perf_counter()
    #print(f"controlled faiss internal threading source A search took: {enda - search_start:.6f}s")
    video_results = similarity_search_video(vector_embeddings, sentences, 5, index_video, texts_video)
    #endb = time.perf_counter()
    #print(f"controlled faiss internal threading source B search took: {endb - enda:.6f}s")
    manuals_chunk_results = faiss_search_manuals_chunk(vector_embeddings, 10, index_manuals, metadata_manuals)
    #endc = time.perf_counter()
    #print(f"controlled faiss internal threading source C search took: {endc - endb:.6f}s")
    search_profiler.disable()
    search_profiler.dump_stats("/home/suwesh/Projects/chatbot_kb_retrieval/profiling_evidences/faiss_sequential.prof")
    search_end = time.perf_counter()
    print(f"controlled internal threading FAISS searches Stage (with sequential search): {search_end - search_start:.6f}s")
    faqs_list = [result["text"] for result in faqs_results]
    video_list = [result["text"] for result in video_results]
    manual_list = [result["text"] for result in manuals_chunk_results]
    rerank_start = time.perf_counter()
    reranked_list = to_reranker_uat(faqs_list, video_list, manual_list, user_query=sentences, topn=12)
    rerank_end = time.perf_counter()
    print(f"Reranker Stage: {rerank_end - rerank_start:.4f}s")
    re_faqs_list = [x["text"] for x in reranked_list if x["source"] == "FAQs"]
    re_video_list = [x["text"] for x in reranked_list if x["source"] == "Video Transcripts"]
    re_manual_list = [x["text"] for x in reranked_list if x["source"] == "User Manuals"]
    faqs_context = "\n".join(re_faqs_list) if re_faqs_list else "None"
    video_context = "\n".join(re_video_list) if re_video_list else "None"
    # graph rag expansion for manuals chunks
    manuals_context = None
    if re_manual_list:
        # map reranked manuals chuunks to original chunk vector ids
        reranked_set = set(re_manual_list)
        surviving_chunks = [
            m for m in manuals_chunk_results if m["text"] in reranked_set
        ]# append post reranker if any chunk has a surviving text after reranker 
        # expand surviving chunks
        unit_ids = expand_chunks_to_unit(surviving_chunks)
        expanded_units = expand_units_with_neighbors(unit_ids, units_by_id_manuals)
        manuals_context = serialize_manual_units(expanded_units)
    #prompt = f"{system_message}\n\nContext: {context}\n\nQuery: {sentences}\n\nAnswer:"
    return faqs_context, video_context, manuals_context
