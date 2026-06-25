"""
Master orchestrator for the 50-document synthetic quotation dataset.
Runs all generators, embeds anomalies, and writes a manifest JSON.
"""
import json
import random
import os
import sys
from datetime import timedelta
from copy import deepcopy

from mock_data_generation.data_definitions import (
    SUPPLIERS, PROJECTS, LINE_ITEMS_CATALOGUE,
    PAYMENT_TERMS, VALIDITY_DAYS_OPTIONS,
    get_doc_date, market_price, random_qty
)
from mock_data_generation.pdf_generator import generate_formal_pdf, generate_informal_pdf
from mock_data_generation.other_generators import generate_xlsx, generate_csv, generate_email_txt, generate_scan_simulation_txt

random.seed(42)


# pyrefly: ignore [parse-error]
OUT_BASE = "./mock_data"
for folder in ["pdf", "xlsx", "csv", "email", "scan_sim", "manifest"]:
    os.makedirs(f"{OUT_BASE}/{folder}", exist_ok=True)
MANIFEST = []

# ─── Helper: build line items for a project/supplier ─────────────────────────
def build_line_items(project, supplier, n_items=None, force_missing_items=False):
    catalogue = LINE_ITEMS_CATALOGUE[project["category"]]
    if n_items is None:
        n_items = random.randint(4, 8)
    chosen = random.sample(catalogue, min(n_items, len(catalogue)))
    items = []
    for item in chosen:
        qty = random_qty(item["unit"])
        up = market_price(item, supplier)
        items.append({
            "desc": item["desc"],
            "unit": item["unit"],
            "qty": qty,
            "unit_price": up,
            "market_price": item["market_price"],
        })
    if force_missing_items:
        # Remove description from one item — anomaly: incomplete line item
        idx = random.randint(0, len(items)-1)
        items[idx]["desc"] = "Item as per drawing"  # vague description
    return items

def supplier_by_id(sid):
    return next(s for s in SUPPLIERS if s["id"] == sid)

def project_by_id(pid):
    return next(p for p in PROJECTS if p["id"] == pid)

def doc_no(supplier_id, project_id, seq, suffix=""):
    return f"{supplier_id}-{project_id}-Q{seq:03d}{suffix}"

def add_to_manifest(doc_id, doc_no, format_, supplier, project, file_path,
                     doc_date, validity_days, payment_terms, anomalies,
                     line_items, notes=""):
    currency = supplier["currency"]
    grand = sum(i["qty"] * i["unit_price"] for i in line_items)
    if supplier["gst"] and currency == "INR":
        grand_incl_tax = round(grand * 1.18, 2)
    else:
        grand_incl_tax = round(grand, 2)

    MANIFEST.append({
        "doc_id": doc_id,
        "doc_no": doc_no,
        "format": format_,
        "supplier_id": supplier["id"],
        "supplier_name": supplier["name"],
        "project_id": project["id"],
        "project_name": project["name"],
        "project_category": project["category"],
        "doc_date": doc_date.strftime("%Y-%m-%d"),
        "validity_days": validity_days,
        "payment_terms": payment_terms,
        "currency": currency,
        "total_excl_tax": round(grand, 2),
        "total_incl_tax": grand_incl_tax,
        "line_item_count": len(line_items),
        "file_path": file_path,
        "anomalies": anomalies,
        "notes": notes,
        "line_items": [
            {
                "desc": i["desc"],
                "unit": i["unit"],
                "qty": i["qty"],
                "unit_price": i["unit_price"],
                "amount": round(i["qty"] * i["unit_price"], 2),
            }
            for i in line_items
        ],
    })

# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT PLAN — 50 docs
# SUP001 Shree Metals      → 7 docs (PROJ-ALPHA heavy, some CHARLIE) — formal PDF + XLSX
# SUP002 Apex Fasteners    → 6 docs (PROJ-DELTA, BRAVO) — CSV + email
# SUP003 Global Polymer    → 6 docs (PROJ-CHARLIE, ECHO) — informal PDF + XLSX
# SUP004 TechnoFab         → 6 docs (ANOMALY: 40% price outlier) — formal PDF
# SUP005 Indo-Gulf         → 5 docs (ANOMALY: USD currency mismatch) — formal PDF + email
# SUP006 Reliable Rubber   → 6 docs (PROJ-DELTA, CHARLIE) — XLSX + scan sim
# SUP007 Electrotech       → 7 docs (ANOMALY: price escalation v1→v2) — formal PDF
# SUP008 PrimeCast         → 7 docs (PROJ-ALPHA, DELTA) — CSV + informal PDF
# ─────────────────────────────────────────────────────────────────────────────

seq = 1

# ──────────────────────────────────────────────────────────────────────────────
# SUP001 — Shree Metals (7 docs)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP001")
for k, (proj_id, fmt, offset) in enumerate([
    ("PROJ-ALPHA", "pdf_formal", 0),
    ("PROJ-ALPHA", "xlsx",       8),
    ("PROJ-ALPHA", "pdf_formal", 18),
    ("PROJ-CHARLIE","pdf_formal",25),
    ("PROJ-CHARLIE","xlsx",      35),
    ("PROJ-ALPHA", "pdf_formal", 45),
    ("PROJ-ECHO",  "csv",        60),
], 1):
    proj = project_by_id(proj_id)
    d_date = get_doc_date(offset)
    v_days = random.choice(VALIDITY_DAYS_OPTIONS)
    pay = random.choice(PAYMENT_TERMS[:6])
    items = build_line_items(proj, sup)
    dn = doc_no("SUP001", proj_id, k)
    fname = f"SUP001_{k:02d}_{proj_id}.{fmt.replace('pdf_formal','pdf').replace('pdf_informal','pdf')}"
    fpath = f"{OUT_BASE}/{'pdf' if 'pdf' in fmt else fmt.replace('pdf_formal','pdf').replace('pdf_informal','pdf')}/{fname}"
    anomalies = []

    if fmt == "pdf_formal":
        generate_formal_pdf(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "xlsx":
        generate_xlsx(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "csv":
        generate_csv(fpath, sup, proj, dn, d_date, items, v_days, pay)

    add_to_manifest(f"DOC-{seq:03d}", dn, fmt, sup, proj, fpath, d_date, v_days, pay, anomalies, items)
    seq += 1
    print(f"  [{seq-1:02d}] {dn} ({fmt})")

# ──────────────────────────────────────────────────────────────────────────────
# SUP002 — Apex Fasteners (6 docs, low price tier)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP002")
for k, (proj_id, fmt, offset) in enumerate([
    ("PROJ-DELTA",  "csv",         5),
    ("PROJ-BRAVO",  "email",       12),
    ("PROJ-DELTA",  "csv",         22),
    ("PROJ-BRAVO",  "xlsx",        38),
    ("PROJ-DELTA",  "email",       50),
    ("PROJ-BRAVO",  "scan_sim",    65),
], 1):
    proj = project_by_id(proj_id)
    d_date = get_doc_date(offset)
    v_days = random.choice(VALIDITY_DAYS_OPTIONS)
    pay = random.choice(PAYMENT_TERMS[:5])
    items = build_line_items(proj, sup)
    dn = doc_no("SUP002", proj_id, k)
    ext = "txt" if fmt in ("email","scan_sim") else fmt
    fname = f"SUP002_{k:02d}_{proj_id}.{ext}"
    fpath = f"{OUT_BASE}/{'email' if fmt=='email' else 'scan_sim' if fmt=='scan_sim' else fmt.replace('pdf_formal','pdf').replace('pdf_informal','pdf')}/{fname}"
    anomalies = []

    if fmt == "csv":
        generate_csv(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "email":
        generate_email_txt(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "xlsx":
        generate_xlsx(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "scan_sim":
        generate_scan_simulation_txt(fpath, sup, proj, dn, d_date, items, v_days, pay)

    add_to_manifest(f"DOC-{seq:03d}", dn, fmt, sup, proj, fpath, d_date, v_days, pay, anomalies, items,
                    notes="Low price tier supplier — consistently below market")
    seq += 1
    print(f"  [{seq-1:02d}] {dn} ({fmt})")

# ──────────────────────────────────────────────────────────────────────────────
# SUP003 — Global Polymer (6 docs)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP003")
for k, (proj_id, fmt, offset) in enumerate([
    ("PROJ-CHARLIE", "pdf_informal", 3),
    ("PROJ-ECHO",    "xlsx",         15),
    ("PROJ-CHARLIE", "pdf_informal", 28),
    ("PROJ-ECHO",    "email",        40),
    ("PROJ-CHARLIE", "xlsx",         55),
    ("PROJ-ECHO",    "pdf_informal", 70),
], 1):
    proj = project_by_id(proj_id)
    d_date = get_doc_date(offset)
    v_days = random.choice(VALIDITY_DAYS_OPTIONS)
    pay = random.choice(PAYMENT_TERMS[:7])
    items = build_line_items(proj, sup)
    dn = doc_no("SUP003", proj_id, k)
    ext = "txt" if fmt == "email" else "pdf"
    fname = f"SUP003_{k:02d}_{proj_id}.{'txt' if fmt=='email' else 'pdf' if 'pdf' in fmt else fmt}"
    fpath_dir = "pdf" if "pdf" in fmt else ("email" if fmt == "email" else fmt)
    fpath = f"{OUT_BASE}/{fpath_dir}/{fname}"
    anomalies = []

    if "pdf_informal" in fmt:
        generate_informal_pdf(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "xlsx":
        generate_xlsx(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "email":
        generate_email_txt(fpath, sup, proj, dn, d_date, items, v_days, pay)

    add_to_manifest(f"DOC-{seq:03d}", dn, fmt, sup, proj, fpath, d_date, v_days, pay, anomalies, items)
    seq += 1
    print(f"  [{seq-1:02d}] {dn} ({fmt})")

# ──────────────────────────────────────────────────────────────────────────────
# SUP004 — TechnoFab (6 docs, ANOMALY: 40% above market)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP004")
for k, (proj_id, fmt, offset) in enumerate([
    ("PROJ-ALPHA",   "pdf_formal", 2),
    ("PROJ-ALPHA",   "pdf_formal", 20),
    ("PROJ-BRAVO",   "xlsx",       33),
    ("PROJ-CHARLIE", "pdf_formal", 48),
    ("PROJ-DELTA",   "pdf_formal", 62),
    ("PROJ-ALPHA",   "csv",        75),
], 1):
    proj = project_by_id(proj_id)
    d_date = get_doc_date(offset)
    v_days = random.choice([7, 15, 21])   # SHORT validity — another anomaly flag
    pay = random.choice(PAYMENT_TERMS[:5])
    items = build_line_items(proj, sup)
    dn = doc_no("SUP004", proj_id, k)
    fname = f"SUP004_{k:02d}_{proj_id}.{'pdf' if 'pdf' in fmt else fmt}"
    fpath_dir = "pdf" if "pdf" in fmt else fmt
    fpath = f"{OUT_BASE}/{fpath_dir}/{fname}"
    anomalies = ["price_outlier_40pct_above_market", "short_validity_window"]

    if fmt == "pdf_formal":
        generate_formal_pdf(fpath, sup, proj, dn, d_date, items, v_days, pay,
                            anomaly_notes=["Note: Prices subject to material availability"])
    elif fmt == "xlsx":
        generate_xlsx(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "csv":
        generate_csv(fpath, sup, proj, dn, d_date, items, v_days, pay)

    add_to_manifest(f"DOC-{seq:03d}", dn, fmt, sup, proj, fpath, d_date, v_days, pay, anomalies, items,
                    notes="ANOMALY: Prices ~40% above market benchmark. Short validity window.")
    seq += 1
    print(f"  [{seq-1:02d}] {dn} ({fmt}) [ANOMALY: price_outlier]")

# ──────────────────────────────────────────────────────────────────────────────
# SUP005 — Indo-Gulf (5 docs, ANOMALY: USD currency for domestic project)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP005")
for k, (proj_id, fmt, offset) in enumerate([
    ("PROJ-ALPHA",   "pdf_formal", 7),
    ("PROJ-BRAVO",   "email",      19),
    ("PROJ-CHARLIE", "pdf_formal", 34),
    ("PROJ-DELTA",   "xlsx",       52),
    ("PROJ-ALPHA",   "email",      68),
], 1):
    proj = project_by_id(proj_id)
    d_date = get_doc_date(offset)
    v_days = random.choice(VALIDITY_DAYS_OPTIONS)
    pay = random.choice(["LC at sight", "100% against pro-forma invoice", "Net 30 days from invoice date"])
    items = build_line_items(proj, sup)
    dn = doc_no("SUP005", proj_id, k)
    fname = f"SUP005_{k:02d}_{proj_id}.{'pdf' if 'pdf' in fmt else 'txt' if fmt=='email' else fmt}"
    fpath_dir = "pdf" if "pdf" in fmt else ("email" if fmt=="email" else fmt)
    fpath = f"{OUT_BASE}/{fpath_dir}/{fname}"
    anomalies = ["currency_mismatch_usd_for_domestic_project", "long_delivery_timeline"]

    if fmt == "pdf_formal":
        generate_formal_pdf(fpath, sup, proj, dn, d_date, items, v_days, pay,
                            anomaly_notes=["Prices quoted in USD. Exchange rate risk applies."])
    elif fmt == "email":
        generate_email_txt(fpath, sup, proj, dn, d_date, items, v_days, pay,
                           vague_terms=True)
    elif fmt == "xlsx":
        generate_xlsx(fpath, sup, proj, dn, d_date, items, v_days, pay)

    add_to_manifest(f"DOC-{seq:03d}", dn, fmt, sup, proj, fpath, d_date, v_days, pay, anomalies, items,
                    notes="ANOMALY: USD pricing for domestic INR project. Long lead time (60 days).")
    seq += 1
    print(f"  [{seq-1:02d}] {dn} ({fmt}) [ANOMALY: currency_mismatch]")

# ──────────────────────────────────────────────────────────────────────────────
# SUP006 — Reliable Rubber (6 docs)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP006")
for k, (proj_id, fmt, offset) in enumerate([
    ("PROJ-DELTA",   "xlsx",      6),
    ("PROJ-CHARLIE", "scan_sim",  17),
    ("PROJ-DELTA",   "xlsx",      29),
    ("PROJ-CHARLIE", "email",     44),
    ("PROJ-DELTA",   "scan_sim",  58),
    ("PROJ-ECHO",    "xlsx",      72),
], 1):
    proj = project_by_id(proj_id)
    d_date = get_doc_date(offset)
    v_days = random.choice(VALIDITY_DAYS_OPTIONS)
    # ANOMALY on one doc: vague payment terms
    pay = "TBD upon mutual agreement" if k == 3 else random.choice(PAYMENT_TERMS[:6])
    missing_del = (k == 5)  # ANOMALY: missing delivery on doc 5
    items = build_line_items(proj, sup, force_missing_items=(k == 4))
    dn = doc_no("SUP006", proj_id, k)
    fname = f"SUP006_{k:02d}_{proj_id}.{'txt' if fmt=='scan_sim' else fmt.replace('email','txt')}"
    fpath_dir = "scan_sim" if fmt == "scan_sim" else ("email" if fmt == "email" else fmt)
    # fix dir for email
    if fmt == "email":
        fpath_dir = "email"
        fname = f"SUP006_{k:02d}_{proj_id}.txt"
    fpath = f"{OUT_BASE}/{fpath_dir}/{fname}"

    anomalies = []
    if k == 3:
        anomalies.append("vague_payment_terms")
    if k == 4:
        anomalies.append("missing_line_item_description")
    if k == 5:
        anomalies.append("missing_delivery_commitment")

    if fmt == "xlsx":
        generate_xlsx(fpath, sup, proj, dn, d_date, items, v_days, pay,
                      missing_delivery=missing_del)
    elif fmt == "scan_sim":
        generate_scan_simulation_txt(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "email":
        generate_email_txt(fpath, sup, proj, dn, d_date, items, v_days, pay,
                           missing_delivery=missing_del)

    add_to_manifest(f"DOC-{seq:03d}", dn, fmt, sup, proj, fpath, d_date, v_days, pay, anomalies, items,
                    notes=", ".join(anomalies) if anomalies else "")
    seq += 1
    print(f"  [{seq-1:02d}] {dn} ({fmt}){' [ANOMALY]' if anomalies else ''}")

# ──────────────────────────────────────────────────────────────────────────────
# SUP007 — Electrotech (7 docs, ANOMALY: price escalation R1→R2)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP007")
# First 3 pairs = R1 then R2 (escalated) for same project
escalation_pairs = [
    ("PROJ-BRAVO", 10, 25),   # (proj, offset_R1, offset_R2)
    ("PROJ-DELTA", 30, 48),
    ("PROJ-BRAVO", 55, 70),
]
k = 1
for proj_id, off1, off2 in escalation_pairs:
    proj = project_by_id(proj_id)
    items_r1 = build_line_items(proj, sup)
    v_days = random.choice([30, 45, 60])
    pay = random.choice(PAYMENT_TERMS[:5])
    d_r1 = get_doc_date(off1)
    dn_r1 = doc_no("SUP007", proj_id, k, "R1")
    fpath_r1 = f"{OUT_BASE}/pdf/SUP007_{k:02d}_{proj_id}_R1.pdf"
    generate_formal_pdf(fpath_r1, sup, proj, dn_r1, d_r1, items_r1, v_days, pay)
    add_to_manifest(f"DOC-{seq:03d}", dn_r1, "pdf_formal", sup, proj, fpath_r1,
                    d_r1, v_days, pay, [], items_r1,
                    notes="Version R1 — initial quotation")
    seq += 1
    print(f"  [{seq-1:02d}] {dn_r1} (pdf_formal) R1")

    # R2: same items, prices escalated by 8-15%
    items_r2 = deepcopy(items_r1)
    for it in items_r2:
        it["unit_price"] = round(it["unit_price"] * random.uniform(1.08, 1.15), 2)
    d_r2 = get_doc_date(off2)
    dn_r2 = doc_no("SUP007", proj_id, k, "R2")
    fpath_r2 = f"{OUT_BASE}/pdf/SUP007_{k:02d}_{proj_id}_R2.pdf"
    generate_formal_pdf(fpath_r2, sup, proj, dn_r2, d_r2, items_r2, v_days, pay,
                        escalation_version="2",
                        anomaly_notes=["Revised prices reflect steel/copper index movement"])
    add_to_manifest(f"DOC-{seq:03d}", dn_r2, "pdf_formal", sup, proj, fpath_r2,
                    d_r2, v_days, pay, ["price_escalation_between_versions"], items_r2,
                    notes="ANOMALY: R2 prices 8-15% higher than R1 for same line items")
    seq += 1
    print(f"  [{seq-1:02d}] {dn_r2} (pdf_formal) R2 [ANOMALY: escalation]")
    k += 1

# 1 standalone Electrotech doc
proj = project_by_id("PROJ-ECHO")
d_date = get_doc_date(80)
items = build_line_items(proj, sup)
v_days = 30
pay = PAYMENT_TERMS[0]
dn = doc_no("SUP007", "PROJ-ECHO", k)
fpath = f"{OUT_BASE}/pdf/SUP007_{k:02d}_PROJ-ECHO.pdf"
generate_formal_pdf(fpath, sup, proj, dn, d_date, items, v_days, pay)
add_to_manifest(f"DOC-{seq:03d}", dn, "pdf_formal", sup, proj, fpath,
                d_date, v_days, pay, [], items)
seq += 1
print(f"  [{seq-1:02d}] {dn} (pdf_formal)")

# ──────────────────────────────────────────────────────────────────────────────
# SUP008 — PrimeCast (7 docs, low price)
# ──────────────────────────────────────────────────────────────────────────────
sup = supplier_by_id("SUP008")
for k, (proj_id, fmt, offset) in enumerate([
    ("PROJ-ALPHA",   "pdf_informal", 4),
    ("PROJ-DELTA",   "csv",          16),
    ("PROJ-ALPHA",   "pdf_informal", 26),
    ("PROJ-DELTA",   "xlsx",         39),
    ("PROJ-ALPHA",   "email",        53),
    ("PROJ-DELTA",   "pdf_informal", 66),
    ("PROJ-ECHO",    "csv",          78),
], 1):
    proj = project_by_id(proj_id)
    d_date = get_doc_date(offset)
    v_days = random.choice(VALIDITY_DAYS_OPTIONS)
    pay = random.choice(PAYMENT_TERMS[:5])
    items = build_line_items(proj, sup)
    dn = doc_no("SUP008", proj_id, k)
    fname = f"SUP008_{k:02d}_{proj_id}.{'pdf' if 'pdf' in fmt else 'txt' if fmt=='email' else fmt}"
    fpath_dir = "pdf" if "pdf" in fmt else ("email" if fmt=="email" else fmt)
    fpath = f"{OUT_BASE}/{fpath_dir}/{fname}"
    anomalies = []

    if "pdf_informal" in fmt:
        generate_informal_pdf(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "csv":
        generate_csv(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "xlsx":
        generate_xlsx(fpath, sup, proj, dn, d_date, items, v_days, pay)
    elif fmt == "email":
        generate_email_txt(fpath, sup, proj, dn, d_date, items, v_days, pay)

    add_to_manifest(f"DOC-{seq:03d}", dn, fmt, sup, proj, fpath, d_date, v_days, pay, anomalies, items,
                    notes="Low price tier — competitive rates")
    seq += 1
    print(f"  [{seq-1:02d}] {dn} ({fmt})")


# ─── Write Manifest ───────────────────────────────────────────────────────────
manifest_path = f"{OUT_BASE}/manifest/quotation_manifest.json"
with open(manifest_path, "w") as f:
    json.dump(MANIFEST, f, indent=2, default=str)

print(f"\nSuccessfully generated {len(MANIFEST)} documents")
print(f"Manifest: {manifest_path}")

# Summary by format and anomaly
fmt_counts = {}
anomaly_counts = {}
for doc in MANIFEST:
    fmt_counts[doc["format"]] = fmt_counts.get(doc["format"], 0) + 1
    for a in doc["anomalies"]:
        anomaly_counts[a] = anomaly_counts.get(a, 0) + 1

print("\nFormat breakdown:")
for k, v in sorted(fmt_counts.items()):
    print(f"  {k:20s}: {v}")

print("\nAnomaly breakdown:")
for k, v in sorted(anomaly_counts.items()):
    print(f"  {k:45s}: {v} docs")