"""
Hybrid search combining semantic (ChromaDB) + keyword (BM25) + reranking.
Uses Reciprocal Rank Fusion to merge results, then cross-encoder reranking.
"""
import json
from typing import Optional

from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from backend.models import Quotation, LineItem, Supplier, Project
from backend.search.vector_store import semantic_search, build_document_text
from backend.observability.logger import get_logger
from backend.observability.metrics import measure_latency

logger = get_logger("hybrid_search")

# BM25 index (built lazily)
_bm25_index = None
_bm25_docs = None
_bm25_doc_ids = None


def _build_bm25_index(db: Session):
    """Build BM25 index from all quotation documents."""
    global _bm25_index, _bm25_docs, _bm25_doc_ids

    quotations = db.query(Quotation).all()
    docs = []
    doc_ids = []

    for q in quotations:
        supplier = db.query(Supplier).filter(Supplier.id == q.supplier_id).first()
        project = db.query(Project).filter(Project.id == q.project_id).first()
        line_items = db.query(LineItem).filter(LineItem.quotation_id == q.id).all()

        quotation_data = {
            "doc_id": q.doc_id,
            "doc_no": q.doc_no,
            "supplier_id": q.supplier_id,
            "supplier_name": supplier.name if supplier else "",
            "project_id": q.project_id,
            "project_name": project.name if project else "",
            "project_category": project.category if project else "",
            "doc_date": q.doc_date.strftime("%Y-%m-%d") if q.doc_date else "",
            "currency": q.currency or "",
            "total_excl_tax": q.total_excl_tax or 0,
            "payment_terms": q.payment_terms or "",
            "validity_days": q.validity_days or 0,
            "line_items": [
                {"description": li.description, "quantity": li.quantity,
                 "unit": li.unit, "unit_price": li.unit_price}
                for li in line_items
            ],
        }
        text = build_document_text(quotation_data)
        docs.append(text)
        doc_ids.append(q.doc_id)

    # Tokenize for BM25
    tokenized_docs = [doc.lower().split() for doc in docs]
    _bm25_index = BM25Okapi(tokenized_docs)
    _bm25_docs = docs
    _bm25_doc_ids = doc_ids
    logger.info(f"BM25 index built with {len(docs)} documents")


def bm25_search(query: str, db: Session, n_results: int = 20) -> list[dict]:
    """Perform BM25 keyword search."""
    global _bm25_index, _bm25_docs, _bm25_doc_ids

    if _bm25_index is None:
        _build_bm25_index(db)

    with measure_latency("search", "bm25_search", query=query):
        tokenized_query = query.lower().split()
        scores = _bm25_index.get_scores(tokenized_query)

        # Get top results
        scored_docs = list(zip(_bm25_doc_ids, _bm25_docs, scores))
        scored_docs.sort(key=lambda x: x[2], reverse=True)
        top_docs = scored_docs[:n_results]

    return [
        {
            "doc_id": doc_id,
            "text": text,
            "score": float(score),
        }
        for doc_id, text, score in top_docs
        if score > 0
    ]


def reciprocal_rank_fusion(semantic_results: list[dict],
                             bm25_results: list[dict],
                             k: int = 60) -> list[dict]:
    """
    Merge semantic and BM25 results using Reciprocal Rank Fusion (RRF).
    RRF score = sum(1 / (k + rank)) for each result list.
    """
    rrf_scores = {}
    doc_data = {}

    for rank, result in enumerate(semantic_results, 1):
        doc_id = result["doc_id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
        doc_data[doc_id] = result

    for rank, result in enumerate(bm25_results, 1):
        doc_id = result["doc_id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
        if doc_id not in doc_data:
            doc_data[doc_id] = result

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    return [
        {
            **doc_data[doc_id],
            "rrf_score": rrf_scores[doc_id],
        }
        for doc_id in sorted_ids
    ]


def rerank_results(query: str, results: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank results using a cross-encoder model.
    Falls back to RRF ordering if model loading fails.
    """
    if not results:
        return results

    with measure_latency("search", "reranking"):
        try:
            from sentence_transformers import CrossEncoder
            from backend.config import RERANKER_MODEL

            model = CrossEncoder(RERANKER_MODEL)
            pairs = [(query, r.get("text", "")) for r in results[:20]]
            scores = model.predict(pairs)

            for i, score in enumerate(scores):
                results[i]["rerank_score"] = float(score)

            results_with_scores = results[:len(scores)]
            results_with_scores.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

            return results_with_scores[:top_k]

        except Exception as e:
            logger.warning(f"Reranking failed, using RRF order: {e}")
            return results[:top_k]


def hybrid_search(query: str, db: Session,
                   n_results: int = 20,
                   rerank_top_k: int = 5,
                   filters: Optional[dict] = None) -> list[dict]:
    """
    Full hybrid search pipeline:
    1. Semantic search (ChromaDB)
    2. BM25 keyword search
    3. Reciprocal Rank Fusion
    4. Cross-encoder reranking
    """
    with measure_latency("search", "hybrid_search", query=query):
        # Step 1: Semantic search
        semantic_results = semantic_search(query, n_results=n_results, filters=filters)

        # Step 2: BM25 search
        bm25_results = bm25_search(query, db, n_results=n_results)

        # Step 3: Reciprocal Rank Fusion
        fused_results = reciprocal_rank_fusion(semantic_results, bm25_results)

        # Step 4: Reranking
        final_results = rerank_results(query, fused_results, top_k=rerank_top_k)

        logger.info(f"Hybrid search: semantic={len(semantic_results)}, "
                     f"bm25={len(bm25_results)}, fused={len(fused_results)}, "
                     f"final={len(final_results)}")

    return final_results


def rebuild_search_indices(db: Session):
    """Rebuild both BM25 and vector indices."""
    global _bm25_index, _bm25_docs, _bm25_doc_ids
    _bm25_index = None
    _bm25_docs = None
    _bm25_doc_ids = None
    _build_bm25_index(db)
    from backend.search.vector_store import index_all_quotations
    index_all_quotations(db)
    logger.info("Search indices rebuilt")
