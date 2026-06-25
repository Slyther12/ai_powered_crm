"""
Ingestion pipeline orchestrator — detects format, routes to extractor,
normalises data, and writes to database.
"""
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import UPLOAD_DIR
from backend.models import (
    Quotation, LineItem, DeliveryTerm, StatusHistory, QuotationStatus
)
from backend.ingestion.extractors import (
    extract_pdf, extract_xlsx, extract_csv, extract_email, extract_scan
)
from backend.ingestion.normalizer import normalise_extracted_data
from backend.observability.logger import get_logger
from backend.observability.metrics import measure_latency, record_metric

logger = get_logger("pipeline")

FORMAT_EXTENSIONS = {
    ".pdf": "pdf",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".csv": "csv",
    ".txt": "email",  # default for txt; scan_sim detected by content
}


def detect_format(file_path: str) -> str:
    """Detect document format from extension and content."""
    ext = Path(file_path).suffix.lower()
    fmt = FORMAT_EXTENSIONS.get(ext, "unknown")

    # For .txt files, try to distinguish email vs scan
    if fmt == "email":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                head = f.read(500)
            if "From:" in head and "Subject:" in head:
                return "email"
            elif "QUOTATION" in head.upper() and "|" in head:
                return "scan_sim"
            else:
                return "email"
        except Exception:
            pass

    return fmt


def extract_document(file_path: str, fmt: str) -> dict:
    """Route to the appropriate extractor based on format."""
    extractors = {
        "pdf": extract_pdf,
        "xlsx": extract_xlsx,
        "csv": extract_csv,
        "email": extract_email,
        "scan_sim": extract_scan,
    }

    extractor = extractors.get(fmt)
    if not extractor:
        return {"error": f"Unsupported format: {fmt}", "raw_text": ""}

    return extractor(file_path)


def ingest_document(file_path: str, db: Session,
                     supplier_id: str = None,
                     project_id: str = None) -> dict:
    """
    Full ingestion pipeline for a single document:
    1. Detect format
    2. Extract structured data
    3. Normalise
    4. Write to database
    5. Log metrics
    """
    with measure_latency("ingestion", "full_pipeline", file=file_path):
        # Step 1: Detect format
        fmt = detect_format(file_path)
        logger.info(f"Ingesting {file_path} (detected format: {fmt})")

        # Step 2: Extract
        extracted = extract_document(file_path, fmt)
        if extracted.get("error"):
            logger.error(f"Extraction failed: {extracted['error']}")
            record_metric("ingestion", "extraction_failed",
                          error=extracted["error"],
                          metadata={"file": file_path, "format": fmt})
            return {"error": extracted["error"], "doc_id": None}

        # Step 3: Normalise
        normalised = normalise_extracted_data(extracted)

        # Step 4b: Try to resolve supplier_id from extracted supplier_name if not provided
        if not supplier_id and normalised.get("supplier_name"):
            from backend.models import Supplier
            matched_supplier = db.query(Supplier).filter(
                Supplier.name.ilike(f"%{normalised['supplier_name'].split()[0]}%")
            ).first()
            if matched_supplier:
                supplier_id = matched_supplier.id
                logger.info(f"Resolved supplier_id={supplier_id} from name '{normalised['supplier_name']}'")

        # Step 4c: Try to resolve project_id from extracted project_id/project_name if not provided
        if not project_id:
            if normalised.get("project_id"):
                project_id = normalised["project_id"]
            elif normalised.get("project_name"):
                from backend.models import Project
                matched_project = db.query(Project).filter(
                    Project.name.ilike(f"%{normalised['project_name']}%")
                ).first()
                if matched_project:
                    project_id = matched_project.id
                    logger.info(f"Resolved project_id={project_id} from name '{normalised['project_name']}'")

        # Step 4: Copy to uploads dir
        dest_filename = f"{uuid.uuid4().hex[:8]}_{Path(file_path).name}"
        dest_path = UPLOAD_DIR / dest_filename
        try:
            shutil.copy2(file_path, dest_path)
        except Exception as e:
            logger.warning(f"Could not copy file to uploads: {e}")
            dest_path = file_path

        # Step 5: Write to database
        doc_id = f"DOC-UP-{uuid.uuid4().hex[:6].upper()}"
        doc_no = normalised.get("doc_no", doc_id)

        quotation = Quotation(
            doc_id=doc_id,
            doc_no=doc_no,
            supplier_id=supplier_id or "UNKNOWN",
            project_id=project_id or "UNKNOWN",
            doc_date=normalised.get("doc_date"),
            validity_days=normalised.get("validity_days"),
            valid_until=normalised.get("valid_until"),
            payment_terms=normalised.get("payment_terms", ""),
            currency=normalised.get("currency", "INR"),
            total_excl_tax=normalised.get("total_excl_tax", 0),
            total_incl_tax=normalised.get("total_incl_tax", 0),
            status=QuotationStatus.RECEIVED,
            format=fmt,
            file_path=str(dest_path),
            ingestion_timestamp=datetime.now(timezone.utc),
        )
        db.add(quotation)
        db.flush()

        # Add line items
        for idx, li in enumerate(normalised.get("line_items", []), 1):
            line_item = LineItem(
                quotation_id=quotation.id,
                seq_no=idx,
                description=li.get("description", "Unknown"),
                unit=li.get("unit", "NOS"),
                quantity=li.get("quantity", 0),
                unit_price=li.get("unit_price", 0),
                amount=li.get("amount", 0),
            )
            db.add(line_item)

        # Add delivery term
        if normalised.get("delivery_days") or normalised.get("warranty") or normalised.get("freight_terms"):
            delivery = DeliveryTerm(
                quotation_id=quotation.id,
                delivery_days=normalised.get("delivery_days"),
                delivery_text=f"{normalised['delivery_days']} days from PO date" if normalised.get("delivery_days") else None,
                freight_terms=normalised.get("freight_terms", ""),
                warranty=normalised.get("warranty", ""),
            )
            db.add(delivery)

        # Add status history
        status_entry = StatusHistory(
            quotation_id=quotation.id,
            old_status=None,
            new_status=QuotationStatus.RECEIVED.value,
            changed_by="system",
            notes=f"Uploaded document: {Path(file_path).name}",
        )
        db.add(status_entry)

        db.commit()

        logger.info(f"Ingested document {doc_id} ({doc_no}) with "
                     f"{len(normalised.get('line_items', []))} line items")

        record_metric("ingestion", "document_ingested",
                       metadata={"doc_id": doc_id, "format": fmt,
                                 "line_items": len(normalised.get("line_items", []))})

        return {
            "doc_id": doc_id,
            "doc_no": doc_no,
            "format": fmt,
            "supplier_name": normalised.get("supplier_name", ""),
            "project_name": normalised.get("project_name", ""),
            "line_items_count": len(normalised.get("line_items", [])),
            "total": normalised.get("total_excl_tax", 0),
            "quotation_id": quotation.id,
        }