"""
Risk detection engine — combines rule-based flags with LLM-generated summaries.
Every flag cites the specific field and value that triggered it.
"""
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import (
    Quotation, LineItem, DeliveryTerm, RiskFlag, RiskSeverity, Supplier
)
from backend.intelligence.benchmarking import compute_price_benchmarks
from backend.intelligence.llm_client import generate_risk_summary
from backend.observability.logger import get_logger
from backend.observability.metrics import measure_latency, record_metric

logger = get_logger("risk_engine")


# ── Rule-Based Risk Detection ────────────────────────────────────────────────

def _check_short_validity(quotation: Quotation) -> list[dict]:
    """Flag quotations with validity < 15 days."""
    flags = []
    if quotation.validity_days and quotation.validity_days < 15:
        flags.append({
            "flag_type": "short_validity_window",
            "severity": RiskSeverity.MEDIUM,
            "field": "validity_days",
            "value": str(quotation.validity_days),
            "explanation": (
                f"Quotation validity is only {quotation.validity_days} days, "
                f"which is unusually short. Standard industry practice is 30-45 days. "
                f"This limits time for evaluation and negotiation."
            ),
        })
    return flags


def _check_currency_mismatch(quotation: Quotation, supplier: Supplier) -> list[dict]:
    """Flag when supplier quotes in foreign currency for domestic project."""
    flags = []
    if supplier and supplier.currency != "INR" and quotation.currency != "INR":
        flags.append({
            "flag_type": "currency_mismatch",
            "severity": RiskSeverity.HIGH,
            "field": "currency",
            "value": quotation.currency,
            "explanation": (
                f"Quotation is in {quotation.currency} from supplier {supplier.name}, "
                f"but the project appears domestic (India-based). "
                f"This introduces exchange rate risk and may complicate payment processing."
            ),
        })
    return flags


def _check_vague_payment_terms(quotation: Quotation) -> list[dict]:
    """Flag vague or uncommitted payment terms."""
    flags = []
    vague_keywords = ["tbd", "mutual agreement", "to be decided", "as per po terms"]
    if quotation.payment_terms:
        terms_lower = quotation.payment_terms.lower()
        if any(kw in terms_lower for kw in vague_keywords):
            flags.append({
                "flag_type": "vague_payment_terms",
                "severity": RiskSeverity.MEDIUM,
                "field": "payment_terms",
                "value": quotation.payment_terms,
                "explanation": (
                    f"Payment terms '{quotation.payment_terms}' are vague and non-committal. "
                    f"This could lead to disputes during invoice processing. "
                    f"Request specific terms (e.g., Net 30, 50% advance)."
                ),
            })
    return flags


def _check_missing_delivery(quotation: Quotation, delivery: DeliveryTerm) -> list[dict]:
    """Flag missing or vague delivery commitments."""
    flags = []
    if not delivery or not delivery.delivery_days:
        flags.append({
            "flag_type": "missing_delivery_commitment",
            "severity": RiskSeverity.HIGH,
            "field": "delivery_days",
            "value": "Not specified",
            "explanation": (
                "No specific delivery timeline provided. "
                "This is a significant risk for project planning. "
                "Request a firm delivery commitment in days from PO date."
            ),
        })
    elif delivery.delivery_text and "confirm" in delivery.delivery_text.lower():
        flags.append({
            "flag_type": "vague_delivery_commitment",
            "severity": RiskSeverity.MEDIUM,
            "field": "delivery_text",
            "value": delivery.delivery_text,
            "explanation": (
                f"Delivery commitment is vague: '{delivery.delivery_text}'. "
                f"Supplier has not committed to a specific timeline."
            ),
        })
    return flags


def _check_long_delivery(quotation: Quotation, delivery: DeliveryTerm,
                          avg_delivery_days: float) -> list[dict]:
    """Flag delivery timelines significantly above average."""
    flags = []
    if delivery and delivery.delivery_days:
        if delivery.delivery_days > avg_delivery_days * 1.5:
            flags.append({
                "flag_type": "long_delivery_timeline",
                "severity": RiskSeverity.MEDIUM,
                "field": "delivery_days",
                "value": str(delivery.delivery_days),
                "explanation": (
                    f"Delivery timeline of {delivery.delivery_days} days is "
                    f"{round(((delivery.delivery_days - avg_delivery_days) / avg_delivery_days) * 100)}% "
                    f"above the average of {round(avg_delivery_days)} days across all suppliers. "
                    f"This may impact project schedule."
                ),
            })
    return flags


def _check_price_outliers(quotation: Quotation, line_items: list[LineItem],
                            benchmarks: dict) -> list[dict]:
    """Flag line items priced significantly above market benchmark."""
    flags = []
    for li in line_items:
        bm = benchmarks.get(li.description)
        if bm and bm["median_price"] > 0:
            deviation_pct = ((li.unit_price - bm["median_price"]) / bm["median_price"]) * 100
            if deviation_pct > 30:
                flags.append({
                    "flag_type": "price_outlier",
                    "severity": RiskSeverity.HIGH if deviation_pct > 40 else RiskSeverity.MEDIUM,
                    "field": f"line_item[{li.seq_no}].unit_price",
                    "value": f"{li.unit_price:,.2f} (median: {bm['median_price']:,.2f})",
                    "explanation": (
                        f"'{li.description}' is priced at {li.unit_price:,.2f}, which is "
                        f"{round(deviation_pct)}% above the market median of {bm['median_price']:,.2f}. "
                        f"Market range: {bm['min_price']:,.2f} – {bm['max_price']:,.2f} "
                        f"across {bm['quotes_count']} quotations from {bm['suppliers_count']} suppliers."
                    ),
                })
    return flags


def _check_missing_line_item_detail(line_items: list[LineItem]) -> list[dict]:
    """Flag line items with vague or incomplete descriptions."""
    flags = []
    vague_descriptions = ["as per drawing", "as discussed", "as per requirement",
                          "item", "material", "misc"]
    for li in line_items:
        if li.description:
            desc_lower = li.description.lower().strip()
            if any(vague in desc_lower for vague in vague_descriptions):
                flags.append({
                    "flag_type": "vague_line_item_description",
                    "severity": RiskSeverity.LOW,
                    "field": f"line_item[{li.seq_no}].description",
                    "value": li.description,
                    "explanation": (
                        f"Line item {li.seq_no} has a vague description: '{li.description}'. "
                        f"Insufficient detail for proper evaluation and comparison. "
                        f"Request a specific material/service description."
                    ),
                })
    return flags


# ── Main Risk Assessment ─────────────────────────────────────────────────────

def assess_quotation_risk(db: Session, quotation_id: int) -> dict:
    """
    Run full risk assessment on a quotation.
    Returns risk flags and an LLM-generated summary.
    """
    with measure_latency("intelligence", "risk_assessment",
                          quotation_id=quotation_id):
        quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
        if not quotation:
            return {"error": "Quotation not found"}

        supplier = db.query(Supplier).filter(Supplier.id == quotation.supplier_id).first()
        line_items = db.query(LineItem).filter(
            LineItem.quotation_id == quotation_id
        ).all()
        delivery = db.query(DeliveryTerm).filter(
            DeliveryTerm.quotation_id == quotation_id
        ).first()

        # Get benchmarks
        benchmarks = compute_price_benchmarks(db)

        # Calculate average delivery days
        all_deliveries = db.query(DeliveryTerm.delivery_days).filter(
            DeliveryTerm.delivery_days.isnot(None)
        ).all()
        avg_delivery = sum(d[0] for d in all_deliveries) / len(all_deliveries) if all_deliveries else 30

        # Collect all rule-based flags
        all_flags = []
        all_flags.extend(_check_short_validity(quotation))
        all_flags.extend(_check_currency_mismatch(quotation, supplier))
        all_flags.extend(_check_vague_payment_terms(quotation))
        all_flags.extend(_check_missing_delivery(quotation, delivery))
        all_flags.extend(_check_long_delivery(quotation, delivery, avg_delivery))
        all_flags.extend(_check_price_outliers(quotation, line_items, benchmarks))
        all_flags.extend(_check_missing_line_item_detail(line_items))

        # Clear old flags and write new ones
        db.query(RiskFlag).filter(RiskFlag.quotation_id == quotation_id).delete()
        for flag_data in all_flags:
            flag = RiskFlag(
                quotation_id=quotation_id,
                **flag_data,
            )
            db.add(flag)

        # Compute risk score (0-100)
        severity_weights = {
            RiskSeverity.LOW: 10,
            RiskSeverity.MEDIUM: 25,
            RiskSeverity.HIGH: 40,
            RiskSeverity.CRITICAL: 60,
        }
        risk_score = min(100, sum(
            severity_weights.get(f["severity"], 10) for f in all_flags
        ))

        # Generate LLM risk summary
        quotation_data = {
            "supplier_name": supplier.name if supplier else "Unknown",
            "doc_no": quotation.doc_no,
            "doc_date": quotation.doc_date.strftime("%Y-%m-%d") if quotation.doc_date else "N/A",
            "currency": quotation.currency,
            "total_excl_tax": quotation.total_excl_tax or 0,
            "payment_terms": quotation.payment_terms,
            "validity_days": quotation.validity_days,
            "anomalies": json.loads(quotation.anomalies_json or "[]"),
            "line_items": [
                {"description": li.description, "unit_price": li.unit_price,
                 "quantity": li.quantity, "unit": li.unit}
                for li in line_items
            ],
            "risk_flags": [
                {"type": f["flag_type"], "severity": f["severity"].value,
                 "field": f["field"], "explanation": f["explanation"]}
                for f in all_flags
            ],
        }
        risk_summary = generate_risk_summary(quotation_data)

        # Update quotation
        quotation.risk_score = risk_score
        quotation.risk_summary = risk_summary
        db.commit()

        logger.info(f"Risk assessment complete for {quotation.doc_no}: "
                     f"score={risk_score}, flags={len(all_flags)}")

        record_metric("intelligence", "risk_assessment_complete",
                       metadata={"doc_no": quotation.doc_no,
                                 "risk_score": risk_score,
                                 "flags_count": len(all_flags)})

        return {
            "quotation_id": quotation_id,
            "doc_no": quotation.doc_no,
            "risk_score": risk_score,
            "risk_summary": risk_summary,
            "flags": [
                {
                    "flag_type": f["flag_type"],
                    "severity": f["severity"].value,
                    "field": f["field"],
                    "value": f["value"],
                    "explanation": f["explanation"],
                }
                for f in all_flags
            ],
        }


def assess_all_quotations(db: Session) -> list[dict]:
    """Run risk assessment on all quotations."""
    quotations = db.query(Quotation).all()
    results = []
    for q in quotations:
        result = assess_quotation_risk(db, q.id)
        results.append(result)
    logger.info(f"Assessed {len(results)} quotations")
    return results
