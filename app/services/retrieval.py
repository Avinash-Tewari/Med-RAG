"""Hybrid retrieval engine — semantic + BM25 with Reciprocal Rank Fusion."""

from __future__ import annotations

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.config import BM25_TOP_K, EMBEDDING_MODEL, FINAL_TOP_K, SEMANTIC_TOP_K
from app.services.ingestion import get_collection

# ── Singleton ───────────────────────────────────────────────────────────
_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


# ── Reciprocal Rank Fusion ──────────────────────────────────────────────

def _reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """
    Merge multiple ranked lists using RRF.
    Each item must have an 'id' key.
    Returns a single merged list sorted by RRF score (desc).
    """
    scores: dict[str, float] = {}
    item_map: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
            item_map[item_id] = item

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [
        {**item_map[item_id], "rrf_score": round(scores[item_id], 6)}
        for item_id in sorted_ids
    ]


# ── Retrieval ───────────────────────────────────────────────────────────

def retrieve(query: str) -> list[dict]:
    """
    Hybrid retrieval: semantic search + BM25 keyword search, merged via RRF.

    Returns top-K chunks, each with:
        id, text, filename, chunk_index, source, rrf_score
    """
    collection = get_collection()

    # Check if collection is empty
    count = collection.count()
    if count == 0:
        return []

    # ── 1. Semantic search ──────────────────────────────────────────────
    model = _get_embedding_model()
    query_embedding = model.encode([query], show_progress_bar=False).tolist()[0]

    semantic_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(SEMANTIC_TOP_K, count),
        include=["documents", "metadatas", "distances"],
    )

    semantic_ranked: list[dict] = []
    if semantic_results["ids"] and semantic_results["ids"][0]:
        for i, chunk_id in enumerate(semantic_results["ids"][0]):
            semantic_ranked.append({
                "id": chunk_id,
                "text": semantic_results["documents"][0][i],
                "metadata": semantic_results["metadatas"][0][i],
                "semantic_distance": semantic_results["distances"][0][i],
            })

    # ── 2. BM25 keyword search ──────────────────────────────────────────
    # Get ALL documents for BM25 corpus
    all_docs = collection.get(include=["documents", "metadatas"])
    bm25_ranked: list[dict] = []

    if all_docs["ids"] and all_docs["documents"]:
        corpus = all_docs["documents"]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)

        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)

        # Get top-K by BM25 score
        scored_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:BM25_TOP_K]

        for idx in scored_indices:
            if bm25_scores[idx] > 0:
                bm25_ranked.append({
                    "id": all_docs["ids"][idx],
                    "text": all_docs["documents"][idx],
                    "metadata": all_docs["metadatas"][idx],
                    "bm25_score": float(bm25_scores[idx]),
                })

    # ── 3. Reciprocal Rank Fusion ───────────────────────────────────────
    fused = _reciprocal_rank_fusion([semantic_ranked, bm25_ranked])

    # Format final results
    results = []
    for item in fused[:FINAL_TOP_K]:
        meta = item.get("metadata", {})
        results.append({
            "id": item["id"],
            "text": item["text"],
            "filename": meta.get("filename", "unknown"),
            "chunk_index": meta.get("chunk_index", -1),
            "source": meta.get("source", "unknown"),
            "rrf_score": item.get("rrf_score", 0.0),
        })

    return results
