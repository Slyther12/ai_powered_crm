"""
Price benchmarking engine — computes price statistics across quotations
and identifies outliers, trends, and supplier pricing behaviour.
"""
import json
from collections import defaultdict
from statistics import mean, median, stdev

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models import Quotation, LineItem, Supplier
from backend.observability.logger import get_logger
from backend.observability.metrics import measure_latency

logger = get_logger("benchmarking")


def compute_price_benchmarks(db: Session) -> dict:
    """
    Compute price benchmarks for each line item description.
    Returns: { description: { median, mean, min, max, stdev, quotes_count, suppliers } }
    """
    with measure_latency("intelligence", "compute_benchmarks"):
        # Get all line items with their quotation/supplier info
        items = (
            db.query(
                LineItem.description,
                LineItem.unit_price,
                LineItem.unit,
                Quotation.supplier_id,
                Quotation.doc_no,
                Quotation.currency,
            )
            .join(Quotation, LineItem.quotation_id == Quotation.id)
            .all()
        )

        # Group by description
        grouped = defaultdict(list)
        for item in items:
            grouped[item.description].append({
                "unit_price": item.unit_price,
                "unit": item.unit,
                "supplier_id": item.supplier_id,
                "doc_no": item.doc_no,
                "currency": item.currency,
            })

        benchmarks = {}
        for desc, entries in grouped.items():
            if len(entries) < 2:
                continue  # Need at least 2 quotes to benchmark

            prices = [e["unit_price"] for e in entries]
            suppliers = list(set(e["supplier_id"] for e in entries))
            med = median(prices)
            avg = mean(prices)
            sd = stdev(prices) if len(prices) > 1 else 0

            # Find outliers (>30% above median)
            outliers = [
                e for e in entries
                if e["unit_price"] > med * 1.3
            ]

            benchmarks[desc] = {
                "description": desc,
                "unit": entries[0]["unit"],
                "median_price": round(med, 2),
                "mean_price": round(avg, 2),
                "min_price": round(min(prices), 2),
                "max_price": round(max(prices), 2),
                "stdev": round(sd, 2),
                "quotes_count": len(entries),
                "suppliers_count": len(suppliers),
                "suppliers": suppliers,
                "outliers": [
                    {
                        "supplier_id": o["supplier_id"],
                        "doc_no": o["doc_no"],
                        "unit_price": o["unit_price"],
                        "pct_above_median": round(
                            ((o["unit_price"] - med) / med) * 100, 1
                        ),
                    }
                    for o in outliers
                ],
            }

        logger.info(f"Computed benchmarks for {len(benchmarks)} line item types")
        return benchmarks


def get_supplier_pricing_profile(db: Session, supplier_id: str) -> dict:
    """
    Analyze a supplier's pricing behaviour relative to benchmarks.
    """
    benchmarks = compute_price_benchmarks(db)

    items = (
        db.query(LineItem, Quotation.doc_no, Quotation.doc_date)
        .join(Quotation, LineItem.quotation_id == Quotation.id)
        .filter(Quotation.supplier_id == supplier_id)
        .order_by(Quotation.doc_date)
        .all()
    )

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    profile = {
        "supplier_id": supplier_id,
        "supplier_name": supplier.name if supplier else "Unknown",
        "total_quotes": len(set(i[1] for i in items)),
        "total_line_items": len(items),
        "pricing_position": [],  # above/below/at market for each item
        "avg_deviation_pct": 0,
    }

    deviations = []
    for li, doc_no, doc_date in items:
        bm = benchmarks.get(li.description)
        if bm and bm["median_price"] > 0:
            deviation_pct = ((li.unit_price - bm["median_price"]) / bm["median_price"]) * 100
            deviations.append(deviation_pct)
            position = "at_market"
            if deviation_pct > 20:
                position = "above_market"
            elif deviation_pct < -10:
                position = "below_market"

            profile["pricing_position"].append({
                "description": li.description,
                "doc_no": doc_no,
                "date": doc_date.strftime("%Y-%m-%d") if doc_date else None,
                "unit_price": li.unit_price,
                "market_median": bm["median_price"],
                "deviation_pct": round(deviation_pct, 1),
                "position": position,
            })

    if deviations:
        profile["avg_deviation_pct"] = round(mean(deviations), 1)

    return profile


def detect_price_escalations(db: Session) -> list[dict]:
    """
    Detect price escalations between versions of the same quotation.
    Looks for R1/R2 patterns or same supplier+project with increasing prices.
    """
    with measure_latency("intelligence", "detect_escalations"):
        quotations = (
            db.query(Quotation)
            .order_by(Quotation.supplier_id, Quotation.project_id, Quotation.doc_date)
            .all()
        )

        # Group by supplier + project
        grouped = defaultdict(list)
        for q in quotations:
            grouped[(q.supplier_id, q.project_id)].append(q)

        escalations = []
        for (sup_id, proj_id), quotes in grouped.items():
            if len(quotes) < 2:
                continue

            for i in range(len(quotes) - 1):
                q1 = quotes[i]
                q2 = quotes[i + 1]

                # Check if R1→R2 pattern
                is_revision = (
                    "R1" in (q1.doc_no or "") and "R2" in (q2.doc_no or "")
                )

                if q1.total_excl_tax and q2.total_excl_tax and q1.total_excl_tax > 0:
                    pct_change = ((q2.total_excl_tax - q1.total_excl_tax) / q1.total_excl_tax) * 100
                    if pct_change > 5:  # >5% increase
                        escalations.append({
                            "supplier_id": sup_id,
                            "project_id": proj_id,
                            "doc_no_v1": q1.doc_no,
                            "doc_no_v2": q2.doc_no,
                            "date_v1": q1.doc_date.strftime("%Y-%m-%d") if q1.doc_date else None,
                            "date_v2": q2.doc_date.strftime("%Y-%m-%d") if q2.doc_date else None,
                            "total_v1": q1.total_excl_tax,
                            "total_v2": q2.total_excl_tax,
                            "pct_increase": round(pct_change, 1),
                            "is_revision_pair": is_revision,
                        })

        logger.info(f"Detected {len(escalations)} price escalations")
        return escalations


def get_delivery_benchmarks(db: Session) -> dict:
    """Compute delivery timeline benchmarks per supplier."""
    from backend.models import DeliveryTerm

    results = (
        db.query(
            Quotation.supplier_id,
            Supplier.name,
            func.avg(DeliveryTerm.delivery_days).label("avg_days"),
            func.min(DeliveryTerm.delivery_days).label("min_days"),
            func.max(DeliveryTerm.delivery_days).label("max_days"),
            func.count(Quotation.id).label("quote_count"),
        )
        .join(DeliveryTerm, Quotation.id == DeliveryTerm.quotation_id)
        .join(Supplier, Quotation.supplier_id == Supplier.id)
        .group_by(Quotation.supplier_id, Supplier.name)
        .all()
    )

    # Overall average
    all_days = (
        db.query(DeliveryTerm.delivery_days)
        .filter(DeliveryTerm.delivery_days.isnot(None))
        .all()
    )
    overall_avg = mean([d[0] for d in all_days]) if all_days else 30

    return {
        "overall_avg_days": round(overall_avg, 1),
        "by_supplier": [
            {
                "supplier_id": r.supplier_id,
                "supplier_name": r.name,
                "avg_days": round(r.avg_days or 0, 1),
                "min_days": r.min_days,
                "max_days": r.max_days,
                "quote_count": r.quote_count,
                "deviation_from_avg": round((r.avg_days or 0) - overall_avg, 1),
            }
            for r in results
        ],
    }
