"""
ChromaDB vector store for semantic search over quotation data.
Embeds quotation documents (concatenated supplier + project + line items + terms)
using sentence-transformers.
"""
import json
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import CHROMA_DIR, EMBEDDING_MODEL
from backend.observability.logger import get_logger
from backend.observability.metrics import measure_latency

logger = get_logger("vector_store")

_chroma_client = None
_collection = None
COLLECTION_NAME = "quotations"


def _get_client():
    """Lazy-init ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
        )
        logger.info(f"ChromaDB client initialised at {CHROMA_DIR}")
    return _chroma_client


def _get_collection():
    """Get or create the quotations collection."""
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' ready "
                     f"({_collection.count()} documents)")
    return _collection


def build_document_text(quotation_data: dict) -> str:
    """
    Build a rich text representation of a quotation for embedding.
    Includes all searchable fields for maximum retrieval quality.
    """
    parts = [
        f"Supplier: {quotation_data.get('supplier_name', '')}",
        f"Supplier ID: {quotation_data.get('supplier_id', '')}",
        f"Project: {quotation_data.get('project_name', '')} ({quotation_data.get('project_category', '')})",
        f"Document: {quotation_data.get('doc_no', '')}",
        f"Date: {quotation_data.get('doc_date', '')}",
        f"Currency: {quotation_data.get('currency', '')}",
        f"Total: {quotation_data.get('total_excl_tax', 0):,.2f}",
        f"Payment Terms: {quotation_data.get('payment_terms', '')}",
        f"Validity: {quotation_data.get('validity_days', '')} days",
    ]

    # Add line items
    line_items = quotation_data.get("line_items", [])
    if line_items:
        parts.append("Line Items:")
        for li in line_items:
            parts.append(
                f"  - {li.get('description', '')}: "
                f"{li.get('quantity', 0)} {li.get('unit', '')} "
                f"@ {li.get('unit_price', 0):,.2f} per {li.get('unit', '')}"
            )

    # Add anomalies/notes
    anomalies = quotation_data.get("anomalies", [])
    if anomalies:
        parts.append(f"Anomalies: {', '.join(anomalies)}")

    notes = quotation_data.get("notes", "")
    if notes:
        parts.append(f"Notes: {notes}")

    return "\n".join(parts)


def index_quotation(quotation_data: dict):
    """Index a single quotation document in ChromaDB."""
    collection = _get_collection()
    doc_id = quotation_data.get("doc_id", "")
    text = build_document_text(quotation_data)

    metadata = {
        "doc_id": doc_id,
        "doc_no": quotation_data.get("doc_no", ""),
        "supplier_id": quotation_data.get("supplier_id", ""),
        "supplier_name": quotation_data.get("supplier_name", ""),
        "project_id": quotation_data.get("project_id", ""),
        "project_name": quotation_data.get("project_name", ""),
        "project_category": quotation_data.get("project_category", ""),
        "doc_date": quotation_data.get("doc_date", ""),
        "currency": quotation_data.get("currency", ""),
        "total_excl_tax": float(quotation_data.get("total_excl_tax", 0)),
        "format": quotation_data.get("format", ""),
    }

    collection.upsert(
        ids=[doc_id],
        documents=[text],
        metadatas=[metadata],
    )


def index_all_quotations(db_session):
    """Index all quotations from the database into ChromaDB."""
    from backend.models import Quotation, LineItem, Supplier, Project

    with measure_latency("search", "index_all"):
        quotations = db_session.query(Quotation).all()

        for q in quotations:
            supplier = db_session.query(Supplier).filter(
                Supplier.id == q.supplier_id
            ).first()
            project = db_session.query(Project).filter(
                Project.id == q.project_id
            ).first()
            line_items = db_session.query(LineItem).filter(
                LineItem.quotation_id == q.id
            ).all()

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
                "format": q.format or "",
                "anomalies": json.loads(q.anomalies_json or "[]"),
                "notes": q.notes or "",
                "line_items": [
                    {
                        "description": li.description,
                        "quantity": li.quantity,
                        "unit": li.unit,
                        "unit_price": li.unit_price,
                    }
                    for li in line_items
                ],
            }
            index_quotation(quotation_data)

        count = _get_collection().count()
        logger.info(f"Indexed {count} quotations in ChromaDB")
        return count


def semantic_search(query: str, n_results: int = 20,
                     filters: Optional[dict] = None) -> list[dict]:
    """
    Perform semantic search against the quotation vector store.
    Returns ranked results with metadata.
    """
    collection = _get_collection()

    where_filter = None
    if filters:
        conditions = []
        if filters.get("supplier_id"):
            conditions.append({"supplier_id": {"$eq": filters["supplier_id"]}})
        if filters.get("project_id"):
            conditions.append({"project_id": {"$eq": filters["project_id"]}})
        if conditions:
            where_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

    with measure_latency("search", "semantic_search", query=query):
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count() or 1),
            where=where_filter,
        )

    docs = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            docs.append({
                "doc_id": doc_id,
                "text": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
                "score": 1 - (results["distances"][0][i] if results["distances"] else 0),
            })

    return docs
