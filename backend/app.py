"""
NexuSolve CRM — FastAPI application.
AI-Powered Quotation Ingestion & Manufacturing CRM Intelligence System.
"""
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.config import CORS_ORIGINS, HOST, PORT, UPLOAD_DIR, BASE_DIR
from backend.database import get_db, init_db, get_session
from backend.models import (
    Quotation, LineItem, DeliveryTerm, Supplier, Project,
    StatusHistory, QuotationStatus, RiskFlag, ObservabilityLog
)
from backend.seed_data import seed_all
from backend.observability.logger import get_logger, set_request_context, log_with_extras
from backend.observability.metrics import (
    record_metric, get_metrics_buffer, flush_metrics_to_db, get_aggregate_metrics
)

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting NexuSolve CRM...")
    # Init DB and seed
    seed_all()
    # Index quotations for search
    try:
        session = get_session()
        from backend.search.vector_store import index_all_quotations
        index_all_quotations(session)
        session.close()
        logger.info("Search indices built")
    except Exception as e:
        logger.warning(f"Search index build failed (non-fatal): {e}")

    # Run risk assessment on all quotations
    try:
        session = get_session()
        from backend.intelligence.risk_engine import assess_all_quotations
        assess_all_quotations(session)
        session.close()
        logger.info("Risk assessment complete for all quotations")
    except Exception as e:
        logger.warning(f"Risk assessment failed (non-fatal): {e}")

    yield
    logger.info("Shutting down NexuSolve CRM...")


app = FastAPI(
    title="NexuSolve CRM",
    description="AI-Powered Quotation Ingestion & Manufacturing CRM Intelligence System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request middleware ───────────────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_id = str(uuid.uuid4())[:8]
    set_request_context(request_id=request_id)
    start = time.perf_counter()

    response = await call_next(request)

    duration = round((time.perf_counter() - start) * 1000, 2)
    log_with_extras(logger, "INFO",
                    f"{request.method} {request.url.path} → {response.status_code}",
                    duration_ms=duration, request_id=request_id)
    record_metric("api", f"{request.method} {request.url.path}",
                   duration_ms=duration)
    return response


# ═════════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═════════════════════════════════════════════════════════════════════════════


# ── Dashboard ────────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Dashboard aggregate statistics."""
    total_quotations = db.query(func.count(Quotation.id)).scalar()
    total_suppliers = db.query(func.count(Supplier.id)).scalar()
    total_projects = db.query(func.count(Project.id)).scalar()
    avg_quote_value = db.query(func.avg(Quotation.total_excl_tax)).scalar() or 0
    total_value = db.query(func.sum(Quotation.total_excl_tax)).scalar() or 0

    # Status breakdown
    status_counts = dict(
        db.query(Quotation.status, func.count(Quotation.id))
        .group_by(Quotation.status).all()
    )

    # Format breakdown
    format_counts = dict(
        db.query(Quotation.format, func.count(Quotation.id))
        .group_by(Quotation.format).all()
    )

    # Risk flags count
    total_risk_flags = db.query(func.count(RiskFlag.id)).scalar() or 0
    high_risk_count = db.query(func.count(Quotation.id)).filter(
        Quotation.risk_score >= 50
    ).scalar() or 0

    # Recent quotations
    recent = (
        db.query(Quotation)
        .order_by(desc(Quotation.ingestion_timestamp))
        .limit(5)
        .all()
    )

    return {
        "total_quotations": total_quotations,
        "total_suppliers": total_suppliers,
        "total_projects": total_projects,
        "avg_quote_value": round(avg_quote_value, 2),
        "total_value": round(total_value, 2),
        "status_breakdown": {k.value if hasattr(k, 'value') else k: v for k, v in status_counts.items()},
        "format_breakdown": format_counts,
        "total_risk_flags": total_risk_flags,
        "high_risk_quotations": high_risk_count,
        "recent_quotations": [
            {
                "id": q.id,
                "doc_id": q.doc_id,
                "doc_no": q.doc_no,
                "supplier_id": q.supplier_id,
                "project_id": q.project_id,
                "total_excl_tax": q.total_excl_tax,
                "status": q.status.value if q.status else "received",
                "risk_score": q.risk_score or 0,
                "format": q.format,
                "doc_date": q.doc_date.strftime("%Y-%m-%d") if q.doc_date else None,
            }
            for q in recent
        ],
    }


# ── Quotations ───────────────────────────────────────────────────────────────
@app.get("/api/quotations")
def list_quotations(
    supplier_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    min_risk: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List quotations with filters and pagination."""
    query = db.query(Quotation)

    if supplier_id:
        query = query.filter(Quotation.supplier_id == supplier_id)
    if project_id:
        query = query.filter(Quotation.project_id == project_id)
    if status:
        query = query.filter(Quotation.status == status)
    if min_risk is not None:
        query = query.filter(Quotation.risk_score >= min_risk)

    total = query.count()
    quotations = (
        query.order_by(desc(Quotation.doc_date))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_quotation_summary(q) for q in quotations],
    }


@app.get("/api/quotations/{quotation_id}")
def get_quotation(quotation_id: int, db: Session = Depends(get_db)):
    """Get full quotation detail with line items, terms, and risk flags."""
    q = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")

    supplier = db.query(Supplier).filter(Supplier.id == q.supplier_id).first()
    project = db.query(Project).filter(Project.id == q.project_id).first()
    line_items = db.query(LineItem).filter(LineItem.quotation_id == q.id).order_by(LineItem.seq_no).all()
    delivery = db.query(DeliveryTerm).filter(DeliveryTerm.quotation_id == q.id).first()
    risk_flags = db.query(RiskFlag).filter(RiskFlag.quotation_id == q.id).all()
    history = db.query(StatusHistory).filter(
        StatusHistory.quotation_id == q.id
    ).order_by(StatusHistory.changed_at).all()

    return {
        "id": q.id,
        "doc_id": q.doc_id,
        "doc_no": q.doc_no,
        "supplier": {
            "id": supplier.id,
            "name": supplier.name,
            "contact": supplier.contact,
            "email": supplier.email,
            "phone": supplier.phone,
        } if supplier else None,
        "project": {
            "id": project.id,
            "name": project.name,
            "category": project.category,
        } if project else None,
        "doc_date": q.doc_date.strftime("%Y-%m-%d") if q.doc_date else None,
        "validity_days": q.validity_days,
        "valid_until": q.valid_until.strftime("%Y-%m-%d") if q.valid_until else None,
        "payment_terms": q.payment_terms,
        "currency": q.currency,
        "total_excl_tax": q.total_excl_tax,
        "total_incl_tax": q.total_incl_tax,
        "status": q.status.value if q.status else "received",
        "format": q.format,
        "risk_score": q.risk_score or 0,
        "risk_summary": q.risk_summary,
        "anomalies": json.loads(q.anomalies_json or "[]"),
        "notes": q.notes,
        "line_items": [
            {
                "id": li.id,
                "seq_no": li.seq_no,
                "description": li.description,
                "unit": li.unit,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "amount": li.amount,
                "market_price_benchmark": li.market_price_benchmark,
            }
            for li in line_items
        ],
        "delivery_term": {
            "delivery_days": delivery.delivery_days,
            "delivery_text": delivery.delivery_text,
            "freight_terms": delivery.freight_terms,
            "warranty": delivery.warranty,
        } if delivery else None,
        "risk_flags": [
            {
                "id": rf.id,
                "flag_type": rf.flag_type,
                "severity": rf.severity.value if rf.severity else "medium",
                "field": rf.field,
                "value": rf.value,
                "explanation": rf.explanation,
            }
            for rf in risk_flags
        ],
        "status_history": [
            {
                "old_status": sh.old_status,
                "new_status": sh.new_status,
                "changed_at": sh.changed_at.isoformat() if sh.changed_at else None,
                "changed_by": sh.changed_by,
                "notes": sh.notes,
            }
            for sh in history
        ],
    }


@app.patch("/api/quotations/{quotation_id}/status")
def update_quotation_status(
    quotation_id: int,
    new_status: str,
    notes: str = "",
    db: Session = Depends(get_db),
):
    """Update quotation status (CRM workflow)."""
    q = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")

    valid_statuses = ["received", "reviewed", "approved", "rejected"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400,
                            detail=f"Invalid status. Must be one of: {valid_statuses}")

    old_status = q.status.value if q.status else None
    q.status = QuotationStatus(new_status)

    history = StatusHistory(
        quotation_id=q.id,
        old_status=old_status,
        new_status=new_status,
        changed_by="user",
        notes=notes,
    )
    db.add(history)
    db.commit()

    return {"message": f"Status updated to {new_status}", "quotation_id": quotation_id}


@app.delete("/api/quotations/{quotation_id}")
def delete_quotation(quotation_id: int, db: Session = Depends(get_db)):
    """Delete a quotation, its associated file, and its vector store entry."""
    q = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")

    doc_id = q.doc_id  # capture before deletion for vector store cleanup

    # Delete the uploaded file if it exists
    import os
    if q.file_path and os.path.exists(q.file_path):
        try:
            os.remove(q.file_path)
            logger.info(f"Deleted file: {q.file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {q.file_path}: {e}")

    # Delete from DB (cascade removes line_items, delivery_term, status_history, risk_flags)
    db.delete(q)
    db.commit()

    # Remove from vector store (non-fatal)
    try:
        from backend.search.vector_store import _get_collection
        collection = _get_collection()
        # ChromaDB stores quotations with doc_id as the document ID
        collection.delete(ids=[doc_id])
        logger.info(f"Removed {doc_id} from vector store")
    except Exception as e:
        logger.warning(f"Vector store cleanup for {doc_id} failed (non-fatal): {e}")

    return {"message": "Quotation deleted successfully", "quotation_id": quotation_id}


# ── Suppliers ────────────────────────────────────────────────────────────────
@app.get("/api/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    """Supplier master list with stats."""
    suppliers = db.query(Supplier).all()
    result = []
    for s in suppliers:
        quote_count = db.query(func.count(Quotation.id)).filter(
            Quotation.supplier_id == s.id
        ).scalar()
        total_value = db.query(func.sum(Quotation.total_excl_tax)).filter(
            Quotation.supplier_id == s.id
        ).scalar() or 0
        avg_risk = db.query(func.avg(Quotation.risk_score)).filter(
            Quotation.supplier_id == s.id
        ).scalar() or 0

        result.append({
            "id": s.id,
            "name": s.name,
            "contact": s.contact,
            "email": s.email,
            "phone": s.phone,
            "currency": s.currency,
            "typical_lead_days": s.typical_lead_days,
            "quotation_count": quote_count,
            "total_value": round(total_value, 2),
            "avg_risk_score": round(avg_risk, 1),
        })

    return result


@app.get("/api/suppliers/{supplier_id}")
def get_supplier_detail(supplier_id: str, db: Session = Depends(get_db)):
    """Supplier detail with quotation history."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    quotations = (
        db.query(Quotation)
        .filter(Quotation.supplier_id == supplier_id)
        .order_by(desc(Quotation.doc_date))
        .all()
    )

    from backend.intelligence.benchmarking import get_supplier_pricing_profile
    pricing = get_supplier_pricing_profile(db, supplier_id)

    return {
        "id": supplier.id,
        "name": supplier.name,
        "contact": supplier.contact,
        "email": supplier.email,
        "phone": supplier.phone,
        "address": supplier.address,
        "gst": supplier.gst,
        "currency": supplier.currency,
        "typical_lead_days": supplier.typical_lead_days,
        "quotations": [_quotation_summary(q) for q in quotations],
        "pricing_profile": pricing,
    }


# ── Compare ──────────────────────────────────────────────────────────────────
@app.get("/api/compare")
def compare_line_items(
    item_description: str = Query(..., description="Line item description to compare"),
    db: Session = Depends(get_db),
):
    """Compare prices across suppliers for the same line item."""
    items = (
        db.query(
            LineItem.description,
            LineItem.unit_price,
            LineItem.quantity,
            LineItem.unit,
            LineItem.amount,
            Quotation.doc_no,
            Quotation.doc_date,
            Quotation.currency,
            Quotation.supplier_id,
            Supplier.name.label("supplier_name"),
            Project.name.label("project_name"),
        )
        .join(Quotation, LineItem.quotation_id == Quotation.id)
        .join(Supplier, Quotation.supplier_id == Supplier.id)
        .join(Project, Quotation.project_id == Project.id)
        .filter(LineItem.description.ilike(f"%{item_description}%"))
        .order_by(LineItem.unit_price.asc())
        .all()
    )

    if not items:
        return {"item": item_description, "comparisons": [], "stats": None}

    prices = [i.unit_price for i in items]
    from statistics import mean, median

    return {
        "item": item_description,
        "comparisons": [
            {
                "supplier_id": i.supplier_id,
                "supplier_name": i.supplier_name,
                "doc_no": i.doc_no,
                "date": i.doc_date.strftime("%Y-%m-%d") if i.doc_date else None,
                "project": i.project_name,
                "unit_price": i.unit_price,
                "quantity": i.quantity,
                "unit": i.unit,
                "currency": i.currency,
            }
            for i in items
        ],
        "stats": {
            "min": min(prices),
            "max": max(prices),
            "mean": round(mean(prices), 2),
            "median": round(median(prices), 2),
            "count": len(prices),
            "spread_pct": round(((max(prices) - min(prices)) / min(prices)) * 100, 1) if min(prices) > 0 else 0,
        },
    }


# ── Upload / Ingest ──────────────────────────────────────────────────────────
@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    supplier_id: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Upload and ingest a new document."""
    # Save uploaded file
    upload_path = UPLOAD_DIR / file.filename
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Run ingestion pipeline
    from backend.ingestion.pipeline import ingest_document
    result = ingest_document(str(upload_path), db, supplier_id, project_id)

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    return result


# ── Intelligence ─────────────────────────────────────────────────────────────
@app.get("/api/intelligence/risk/{quotation_id}")
def get_risk_analysis(quotation_id: int, db: Session = Depends(get_db)):
    """Get or generate risk analysis for a quotation."""
    from backend.intelligence.risk_engine import assess_quotation_risk
    return assess_quotation_risk(db, quotation_id)


@app.get("/api/intelligence/benchmarks")
def get_benchmarks(db: Session = Depends(get_db)):
    """Get price benchmarking data."""
    from backend.intelligence.benchmarking import (
        compute_price_benchmarks, detect_price_escalations, get_delivery_benchmarks
    )
    return {
        "price_benchmarks": compute_price_benchmarks(db),
        "escalations": detect_price_escalations(db),
        "delivery_benchmarks": get_delivery_benchmarks(db),
    }


@app.get("/api/intelligence/risk-summary")
def get_all_risks(db: Session = Depends(get_db)):
    """Get all quotations with risk flags summary."""
    quotations = (
        db.query(Quotation)
        .filter(Quotation.risk_score > 0)
        .order_by(desc(Quotation.risk_score))
        .all()
    )

    results = []
    for q in quotations:
        supplier = db.query(Supplier).filter(Supplier.id == q.supplier_id).first()
        flags = db.query(RiskFlag).filter(RiskFlag.quotation_id == q.id).all()
        results.append({
            "id": q.id,
            "doc_no": q.doc_no,
            "supplier_name": supplier.name if supplier else "Unknown",
            "risk_score": q.risk_score or 0,
            "risk_summary": q.risk_summary,
            "flags_count": len(flags),
            "flags": [
                {
                    "flag_type": f.flag_type,
                    "severity": f.severity.value if f.severity else "medium",
                    "field": f.field,
                    "explanation": f.explanation,
                }
                for f in flags
            ],
        })

    return results


# ── Search ───────────────────────────────────────────────────────────────────
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    supplier_id: Optional[str] = None
    project_id: Optional[str] = None

@app.post("/api/search")
def search_quotations(
    body: SearchRequest,
    db: Session = Depends(get_db),
):
    """Natural language search across quotation data."""
    filters = {}
    if body.supplier_id:
        filters["supplier_id"] = body.supplier_id
    if body.project_id:
        filters["project_id"] = body.project_id

    from backend.search.query_engine import process_query
    return process_query(body.query, db, filters=filters if filters else None)


# ── Observability ────────────────────────────────────────────────────────────
@app.get("/api/observability/logs")
def get_logs(
    stage: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get pipeline and system logs."""
    # Flush buffer first
    flush_metrics_to_db(db)

    query = db.query(ObservabilityLog).order_by(desc(ObservabilityLog.timestamp))
    if stage:
        query = query.filter(ObservabilityLog.stage == stage)

    logs = query.limit(limit).all()

    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "stage": log.stage,
            "operation": log.operation,
            "duration_ms": log.duration_ms,
            "tokens_used": log.tokens_used,
            "error": log.error,
            "metadata": json.loads(log.metadata_json or "{}"),
        }
        for log in logs
    ]


@app.get("/api/observability/metrics")
def get_observability_metrics(db: Session = Depends(get_db)):
    """Get aggregate observability metrics."""
    flush_metrics_to_db(db)
    return get_aggregate_metrics(db)


# ── Projects ─────────────────────────────────────────────────────────────────
@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    projects = db.query(Project).all()
    result = []
    for p in projects:
        quote_count = db.query(func.count(Quotation.id)).filter(
            Quotation.project_id == p.id
        ).scalar()
        result.append({
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "quotation_count": quote_count,
        })
    return result


# ── Line Items (for compare dropdown) ────────────────────────────────────────
@app.get("/api/line-items/distinct")
def get_distinct_line_items(db: Session = Depends(get_db)):
    """Get distinct line item descriptions for the compare feature."""
    items = (
        db.query(LineItem.description, func.count(LineItem.id).label("count"))
        .group_by(LineItem.description)
        .order_by(desc(func.count(LineItem.id)))
        .all()
    )
    return [{"description": i.description, "count": i.count} for i in items]


# ── Helper ───────────────────────────────────────────────────────────────────
def _quotation_summary(q: Quotation) -> dict:
    return {
        "id": q.id,
        "doc_id": q.doc_id,
        "doc_no": q.doc_no,
        "supplier_id": q.supplier_id,
        "project_id": q.project_id,
        "doc_date": q.doc_date.strftime("%Y-%m-%d") if q.doc_date else None,
        "total_excl_tax": q.total_excl_tax,
        "total_incl_tax": q.total_incl_tax,
        "currency": q.currency,
        "status": q.status.value if q.status else "received",
        "format": q.format,
        "risk_score": q.risk_score or 0,
        "validity_days": q.validity_days,
        "payment_terms": q.payment_terms,
    }


# ── Static files (serves React build in production) ──────────────────────────
frontend_build = BASE_DIR / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_build / "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve React SPA for all non-API routes."""
        file_path = frontend_build / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_build / "index.html"))