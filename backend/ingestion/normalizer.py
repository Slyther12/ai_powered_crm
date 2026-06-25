"""
Post-extraction data normalisation — standardises extracted data before DB insertion.
"""
import re
from datetime import datetime, timedelta
from typing import Optional

from backend.observability.logger import get_logger

logger = get_logger("normalizer")

# Unit normalisation map
UNIT_MAP = {
    "mt": "MT", "ton": "MT", "tons": "MT", "tonne": "MT",
    "mtr": "MTR", "meter": "MTR", "meters": "MTR", "metre": "MTR", "m": "MTR",
    "nos": "NOS", "no": "NOS", "pcs": "NOS", "pieces": "NOS", "ea": "NOS",
    "sqm": "SQM", "sq.m": "SQM", "sq m": "SQM",
    "lot": "LOT", "ls": "LS", "lump sum": "LS",
    "set": "SET", "sets": "SET",
    "drum": "DRUM", "drums": "DRUM",
    "mh": "MH", "man-hours": "MH",
    "bag": "BAG", "bags": "BAG",
    "cum": "CUM", "cubic meter": "CUM",
    "cft": "CFT", "cubic feet": "CFT",
}


def normalise_unit(unit: str) -> str:
    """Normalise unit strings to standard abbreviations."""
    if not unit:
        return "NOS"
    clean = unit.strip().lower()
    return UNIT_MAP.get(clean, unit.strip().upper())


def normalise_currency(currency: str) -> str:
    """Normalise currency codes."""
    if not currency:
        return "INR"
    clean = currency.strip().upper()
    mapping = {"₹": "INR", "RS": "INR", "RS.": "INR", "RUPEE": "INR",
               "$": "USD", "US$": "USD"}
    return mapping.get(clean, clean)


def normalise_extracted_data(data: dict) -> dict:
    """
    Normalise all fields in the extracted data dict.
    """
    normalised = dict(data)

    # Normalise currency
    normalised["currency"] = normalise_currency(data.get("currency", "INR"))

    # Normalise line items
    for item in normalised.get("line_items", []):
        if "unit" in item:
            item["unit"] = normalise_unit(item["unit"])
        if "quantity" in item and item["quantity"]:
            item["quantity"] = round(float(item["quantity"]), 2)
        if "unit_price" in item and item["unit_price"]:
            item["unit_price"] = round(float(item["unit_price"]), 2)
        if "amount" not in item or not item.get("amount"):
            if item.get("quantity") and item.get("unit_price"):
                item["amount"] = round(item["quantity"] * item["unit_price"], 2)

    # Calculate total if not present
    if normalised.get("line_items"):
        total = sum(item.get("amount", 0) for item in normalised["line_items"])
        if not normalised.get("total_excl_tax"):
            normalised["total_excl_tax"] = round(total, 2)

    # Compute valid_until from doc_date + validity_days
    if normalised.get("doc_date") and normalised.get("validity_days"):
        doc_date = normalised["doc_date"]
        if isinstance(doc_date, str):
            try:
                doc_date = datetime.strptime(doc_date, "%Y-%m-%d")
                normalised["doc_date"] = doc_date
            except ValueError:
                pass
        
        if isinstance(doc_date, datetime):
            normalised["valid_until"] = (
                doc_date + timedelta(days=normalised["validity_days"])
            )

    return normalised
