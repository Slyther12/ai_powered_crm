"""
Natural language query engine — processes user queries, determines
the best retrieval strategy, and generates answers with source citations.
"""
import json
import re
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models import Quotation, LineItem, Supplier, Project
from backend.search.hybrid_search import hybrid_search
from backend.intelligence.llm_client import generate_search_answer
from backend.observability.logger import get_logger
from backend.observability.metrics import measure_latency

logger = get_logger("query_engine")


def _enrich_results_from_db(results: list[dict], db: Session) -> list[dict]:
    """Enrich search results with full quotation data from DB."""
    enriched = []
    for result in results:
        doc_id = result.get("doc_id", "")
        quotation = db.query(Quotation).filter(Quotation.doc_id == doc_id).first()
        if not quotation:
            enriched.append(result)
            continue

        supplier = db.query(Supplier).filter(Supplier.id == quotation.supplier_id).first()
        project = db.query(Project).filter(Project.id == quotation.project_id).first()
        line_items = db.query(LineItem).filter(
            LineItem.quotation_id == quotation.id
        ).all()

        enriched.append({
            **result,
            "doc_no": quotation.doc_no,
            "supplier_name": supplier.name if supplier else "",
            "supplier_id": quotation.supplier_id,
            "project_name": project.name if project else "",
            "project_id": quotation.project_id,
            "project_category": project.category if project else "",
            "doc_date": quotation.doc_date.strftime("%Y-%m-%d") if quotation.doc_date else "",
            "currency": quotation.currency or "",
            "total_excl_tax": quotation.total_excl_tax or 0,
            "total_incl_tax": quotation.total_incl_tax or 0,
            "payment_terms": quotation.payment_terms or "",
            "validity_days": quotation.validity_days or 0,
            "status": quotation.status.value if quotation.status else "",
            "risk_score": quotation.risk_score or 0,
            "line_items": [
                {
                    "description": li.description,
                    "quantity": li.quantity,
                    "unit": li.unit,
                    "unit_price": li.unit_price,
                    "amount": li.amount,
                }
                for li in line_items
            ],
        })

    return enriched


def _try_structured_query(query: str, db: Session) -> Optional[dict]:
    """
    Try to answer simple structured queries directly from SQL.
    Returns None if the query needs hybrid search.
    """
    query_lower = query.lower()

    # Pattern: lowest price for X
    match = re.search(r"lowest.*price.*for\s+(.+?)(?:\s+in\s+the\s+last|\s*\?|\s*$)", query_lower)
    if match:
        item_desc = match.group(1).strip()
        results = (
            db.query(
                LineItem.description,
                LineItem.unit_price,
                LineItem.unit,
                Quotation.doc_no,
                Quotation.supplier_id,
                Supplier.name.label("supplier_name"),
                Quotation.doc_date,
            )
            .join(Quotation, LineItem.quotation_id == Quotation.id)
            .join(Supplier, Quotation.supplier_id == Supplier.id)
            .filter(LineItem.description.ilike(f"%{item_desc}%"))
            .order_by(LineItem.unit_price.asc())
            .limit(5)
            .all()
        )

        if results:
            return {
                "type": "structured",
                "answer": (
                    f"The lowest price for items matching '{item_desc}' is "
                    f"₹{results[0].unit_price:,.2f}/{results[0].unit} "
                    f"from {results[0].supplier_name} "
                    f"(Ref: {results[0].doc_no}, "
                    f"Date: {results[0].doc_date.strftime('%d-%b-%Y') if results[0].doc_date else 'N/A'})."
                ),
                "sources": [
                    {
                        "doc_no": r.doc_no,
                        "supplier": r.supplier_name,
                        "unit_price": r.unit_price,
                        "unit": r.unit,
                        "date": r.doc_date.strftime("%Y-%m-%d") if r.doc_date else None,
                    }
                    for r in results
                ],
            }

    return None


def process_query(query: str, db: Session,
                   filters: Optional[dict] = None) -> dict:
    """
    Process a natural language query.
    1. Try structured SQL query for simple patterns
    2. Fall back to hybrid search + LLM for complex queries
    """
    with measure_latency("search", "process_query", query=query):
        # Try structured query first
        structured_result = _try_structured_query(query, db)
        if structured_result:
            logger.info(f"Query answered via structured SQL: {query[:50]}...")
            return structured_result

        # Hybrid search
        search_results = hybrid_search(
            query=query,
            db=db,
            n_results=20,
            rerank_top_k=5,
            filters=filters,
        )

        # Enrich results with DB data
        enriched = _enrich_results_from_db(search_results, db)

        # Generate LLM answer
        answer = generate_search_answer(query, enriched)

        return {
            "type": "hybrid",
            "answer": answer,
            "sources": [
                {
                    "doc_id": r.get("doc_id", ""),
                    "doc_no": r.get("doc_no", ""),
                    "supplier_name": r.get("supplier_name", ""),
                    "project_name": r.get("project_name", ""),
                    "relevance_score": round(r.get("rerank_score", r.get("rrf_score", 0)), 4),
                }
                for r in enriched
            ],
        }
