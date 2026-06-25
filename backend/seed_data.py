"""
Seed the database from the quotation manifest JSON.
Seeds: Suppliers, Projects, and all mock quotations from the manifest.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from backend.config import MANIFEST_PATH, BASE_DIR
from backend.database import init_db, get_session
from backend.models import (
    Supplier, Project, Quotation, LineItem, DeliveryTerm,
    StatusHistory, QuotationStatus, RiskFlag
)
from backend.observability.logger import get_logger
from backend.observability.metrics import record_metric, measure_latency

logger = get_logger("seed")

# Supplier master data
SUPPLIERS_MASTER = [
    {"id": "SUP001", "name": "Shree Metals & Alloys Pvt Ltd", "contact": "Rajesh Kumar",
     "email": "rajesh@shreemetals.in", "phone": "+91-22-4455-6677",
     "address": "Plot 14, MIDC Industrial Area, Pune 411018",
     "gst": "27AABCS1234A1Z5", "currency": "INR", "typical_lead_days": 21},
    {"id": "SUP002", "name": "Apex Fasteners & Hardware Co.", "contact": "Priya Sharma",
     "email": "priya.s@apexfasteners.com", "phone": "+91-11-2345-6789",
     "address": "47 Industrial Estate, Faridabad 121001",
     "gst": "06AABCA5678B2Z3", "currency": "INR", "typical_lead_days": 14},
    {"id": "SUP003", "name": "Global Polymer Solutions Ltd", "contact": "Suresh Nair",
     "email": "snair@globalpolymers.com", "phone": "+91-44-6677-8899",
     "address": "3rd Floor, Olympia Tech Park, Chennai 600032",
     "gst": "33AABCG9012C3Z1", "currency": "INR", "typical_lead_days": 30},
    {"id": "SUP004", "name": "TechnoFab Engineering Works", "contact": "Amit Desai",
     "email": "amit@technofab.co.in", "phone": "+91-79-3344-5566",
     "address": "Survey No. 88, Sarkhej-Gandhinagar Hwy, Ahmedabad 380054",
     "gst": "24AABCT3456D4Z9", "currency": "INR", "typical_lead_days": 45},
    {"id": "SUP005", "name": "Indo-Gulf Procurement Services", "contact": "Farhan Sheikh",
     "email": "farhan@indogulf.ae", "phone": "+971-4-567-8901",
     "address": "Office 1204, Al Quoz Ind Area 4, Dubai, UAE",
     "gst": None, "currency": "USD", "typical_lead_days": 60},
    {"id": "SUP006", "name": "Reliable Rubber & Seals Mfg.", "contact": "Deepa Pillai",
     "email": "deepa@reliablerubber.in", "phone": "+91-484-2233-4455",
     "address": "NH-47, Edappally, Kochi 682024",
     "gst": "32AABCR7890E5Z7", "currency": "INR", "typical_lead_days": 18},
    {"id": "SUP007", "name": "Electrotech Switchgear Industries", "contact": "Vikram Joshi",
     "email": "vjoshi@electrotech.in", "phone": "+91-20-6655-4433",
     "address": "Block D, Bhosari MIDC, Pune 411026",
     "gst": "27AABCE4567F6Z2", "currency": "INR", "typical_lead_days": 30},
    {"id": "SUP008", "name": "PrimeCast Foundry & Forge", "contact": "Ganesh Reddy",
     "email": "ganesh.r@primecast.in", "phone": "+91-40-2244-6688",
     "address": "IDA Uppal, Hyderabad 500039",
     "gst": "36AABCP2345G7Z8", "currency": "INR", "typical_lead_days": 35},
    # Fallback for uploads with unknown supplier/project
    {"id": "UNKNOWN", "name": "Unknown Supplier", "contact": "",
     "email": "", "phone": "", "address": "", "gst": None,
     "currency": "INR", "typical_lead_days": 30},
]

PROJECTS_MASTER = [
    {"id": "PROJ-ALPHA", "name": "Project Alpha", "category": "Structural Fabrication",
     "description": "Heavy structural steel works for new production hall"},
    {"id": "PROJ-BRAVO", "name": "Project Bravo", "category": "Electrical Infrastructure",
     "description": "LT panel installation and cable laying"},
    {"id": "PROJ-CHARLIE", "name": "Project Charlie", "category": "Fluid Systems",
     "description": "Process piping and valve replacement"},
    {"id": "PROJ-DELTA", "name": "Project Delta", "category": "Mechanical Overhaul",
     "description": "Gearbox and rotating equipment maintenance"},
    {"id": "PROJ-ECHO", "name": "Project Echo", "category": "Civil & Insulation",
     "description": "Thermal insulation and civil foundation works"},
    # Fallback for uploads with unknown project
    {"id": "UNKNOWN", "name": "Unknown Project", "category": "Uncategorized",
     "description": "Uploaded document with unknown project"},
]

# Delivery/warranty data from manifest format details (approximate per supplier category)
DELIVERY_DATA = {
    "pdf_formal": {"delivery_days": 21, "freight_terms": "Ex-Works Pune", "warranty": "12 months from delivery"},
    "xlsx": {"delivery_days": 14, "freight_terms": "Door Delivery", "warranty": "6 months"},
    "csv": {"delivery_days": 18, "freight_terms": "Ex-Factory", "warranty": ""},
    "email": {"delivery_days": 30, "freight_terms": "Freight extra at actuals", "warranty": "Standard manufacturer warranty"},
    "scan_sim": {"delivery_days": 25, "freight_terms": "FOR Destination", "warranty": "12 months"},
}


def _parse_date(date_str):
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def seed_all():
    """Seed the database: suppliers, projects, and all manifest quotations."""
    init_db()
    session = get_session()

    with measure_latency("seed", "full_seed"):
        try:
            # ── Seed suppliers ───────────────────────────────────────────────
            for sup_data in SUPPLIERS_MASTER:
                session.merge(Supplier(**sup_data))
            session.commit()
            logger.info(f"Seeded {len(SUPPLIERS_MASTER)} suppliers")

            # ── Seed projects ────────────────────────────────────────────────
            for proj_data in PROJECTS_MASTER:
                session.merge(Project(**proj_data))
            session.commit()
            logger.info(f"Seeded {len(PROJECTS_MASTER)} projects")

            # ── Check if quotations already seeded ───────────────────────────
            existing = session.query(Quotation).count()
            if existing > 0:
                logger.info(f"Database already has {existing} quotations — skipping manifest seed")
                return

            # ── Load manifest ─────────────────────────────────────────────────
            if not MANIFEST_PATH.exists():
                logger.warning(f"Manifest not found at {MANIFEST_PATH} — skipping quotation seed")
                return

            manifest = json.loads(MANIFEST_PATH.read_text())
            logger.info(f"Seeding {len(manifest)} quotations from manifest...")

            seeded = 0
            for entry in manifest:
                try:
                    doc_date = _parse_date(entry.get("doc_date"))
                    validity_days = entry.get("validity_days")
                    valid_until = None
                    if doc_date and validity_days:
                        valid_until = doc_date + timedelta(days=validity_days)

                    fmt = entry.get("format", "pdf_formal")
                    # Normalise format name: "pdf_formal" → "pdf"
                    db_fmt = fmt.replace("pdf_formal", "pdf").replace("pdf_revised", "pdf")

                    quotation = Quotation(
                        doc_id=entry["doc_id"],
                        doc_no=entry["doc_no"],
                        supplier_id=entry["supplier_id"],
                        project_id=entry["project_id"],
                        doc_date=doc_date,
                        validity_days=validity_days,
                        valid_until=valid_until,
                        payment_terms=entry.get("payment_terms", ""),
                        currency=entry.get("currency", "INR"),
                        total_excl_tax=entry.get("total_excl_tax", 0),
                        total_incl_tax=entry.get("total_incl_tax", 0),
                        status=QuotationStatus.RECEIVED,
                        format=db_fmt,
                        file_path=str(BASE_DIR / entry.get("file_path", "").lstrip("./")),
                        anomalies_json=json.dumps(entry.get("anomalies", [])),
                        notes=entry.get("notes", ""),
                        risk_score=0,
                    )
                    session.add(quotation)
                    session.flush()  # get quotation.id

                    # ── Line items ────────────────────────────────────────────
                    for idx, li in enumerate(entry.get("line_items", []), 1):
                        line_item = LineItem(
                            quotation_id=quotation.id,
                            seq_no=idx,
                            description=li.get("desc") or li.get("description", "Unknown"),
                            unit=li.get("unit", "NOS"),
                            quantity=li.get("qty") or li.get("quantity", 0),
                            unit_price=li.get("unit_price", 0),
                            amount=li.get("amount", 0),
                        )
                        session.add(line_item)

                    # ── Delivery terms ────────────────────────────────────────
                    dd = DELIVERY_DATA.get(fmt, DELIVERY_DATA["pdf_formal"])
                    delivery = DeliveryTerm(
                        quotation_id=quotation.id,
                        delivery_days=dd["delivery_days"],
                        delivery_text=f"{dd['delivery_days']} days from PO date",
                        freight_terms=dd["freight_terms"],
                        warranty=dd["warranty"],
                    )
                    session.add(delivery)

                    # ── Status history ────────────────────────────────────────
                    history = StatusHistory(
                        quotation_id=quotation.id,
                        old_status=None,
                        new_status=QuotationStatus.RECEIVED.value,
                        changed_by="seed",
                        notes=f"Initial seed from manifest: {entry['doc_no']}",
                    )
                    session.add(history)
                    seeded += 1

                except Exception as e:
                    logger.warning(f"Failed to seed quotation {entry.get('doc_id', '?')}: {e}")
                    session.rollback()
                    # Re-seed suppliers/projects after rollback
                    for sup_data in SUPPLIERS_MASTER:
                        session.merge(Supplier(**sup_data))
                    for proj_data in PROJECTS_MASTER:
                        session.merge(Project(**proj_data))
                    session.commit()
                    continue

            session.commit()
            logger.info(f"✅ Seeded {seeded}/{len(manifest)} quotations from manifest")
            record_metric("seed", "seed_complete", metadata={"quotations": seeded})

        except Exception as e:
            session.rollback()
            logger.error(f"Seed failed: {e}")
            raise
        finally:
            session.close()


if __name__ == "__main__":
    seed_all()
    print("✅ Database seeded successfully")