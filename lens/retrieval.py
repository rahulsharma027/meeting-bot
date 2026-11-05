"""BM25, exact cosine search and reciprocal rank fusion, kept visible for learning."""
import math
import re
from collections import Counter

STOP_WORDS = set("a an the and or of to in is it are was were be been on for with as at by that this i we you our what which how can does do did my me their they have has had will would should not if from".split())


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP_WORDS]


def normalize(vector, expected=None):
    if not isinstance(vector, list) or not vector or (expected and len(vector) != expected):
        raise ValueError("Unexpected embedding dimension. Rebuild using a compatible model.")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in vector):
        raise ValueError("The embedding contains invalid numeric values.")
    norm = math.sqrt(sum(v*v for v in vector))
    if norm == 0:
        raise ValueError("The embedding has zero length.")
    return [v / norm for v in vector]


def bm25(query, items):
    documents = [Counter(tokens(i["title"] + " " + i["content"])) for i in items]
    query_terms = set(tokens(query))
    if not documents or not query_terms:
        return []
    average = sum(sum(d.values()) for d in documents) / len(documents) or 1
    frequencies = {term: sum(term in d for d in documents) for term in query_terms}
    ranked = []
    for item, counts in zip(items, documents):
        length, score = sum(counts.values()), 0.0
        for term in query_terms:
            frequency = counts[term]
            if frequency:
                inverse = math.log(1 + (len(documents) - frequencies[term] + 0.5) / (frequencies[term] + 0.5))
                score += inverse * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * length / average))
        if score > 0:
            ranked.append((item["id"], score))
    return sorted(ranked, key=lambda r: (-r[1], r[0]))


def dense(query_vector, items):
    query_vector = normalize(query_vector)
    scores = []
    for item in items:
        vector = normalize(item["embedding"], len(query_vector))
        scores.append((item["id"], sum(a*b for a, b in zip(query_vector, vector))))
    return sorted(scores, key=lambda r: (-r[1], r[0]))


def fuse(*rankings, depth=12, constant=60):
    scores = Counter()
    for ranking in rankings:
        for rank, (item_id, _) in enumerate(ranking[:depth], 1):
            scores[item_id] += 1 / (constant + rank)
    return sorted(scores.items(), key=lambda r: (-r[1], r[0]))


def retrieve(query, items, mode="keyword", query_vector=None, top_k=4):
    if mode not in {"keyword", "semantic", "hybrid"}:
        raise ValueError("Choose keyword, semantic, or hybrid retrieval.")
    if top_k not in {2, 4, 6}:
        raise ValueError("Choose 2, 4, or 6 source passages.")
    keyword = bm25(query, items) if mode != "semantic" else []
    semantic = dense(query_vector, items) if mode != "keyword" else []
    ranked = keyword if mode == "keyword" else semantic if mode == "semantic" else fuse(keyword, semantic)
    indexed = {i["id"]: i for i in items}
    keyword_ranks = {i: n for n, (i, _) in enumerate(keyword, 1)}
    semantic_ranks = {i: n for n, (i, _) in enumerate(semantic, 1)}
    return [{**indexed[item_id], "score": round(score, 5), "rank": rank,
             "keyword_rank": keyword_ranks.get(item_id), "semantic_rank": semantic_ranks.get(item_id)}
            for rank, (item_id, score) in enumerate(ranked[:top_k], 1)]
