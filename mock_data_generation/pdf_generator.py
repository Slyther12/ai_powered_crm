"""
PDF quotation generator.
Produces two layout styles:
  - formal_letterhead: structured corporate format
  - informal_typed: plain typed quotation (simulates older supplier style)
"""
import random
from datetime import timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from mock_data_generation.data_definitions import (
    SUPPLIERS, PROJECTS, LINE_ITEMS_CATALOGUE, PAYMENT_TERMS,
    VALIDITY_DAYS_OPTIONS, get_doc_date, market_price, random_qty
)

W, H = A4

def _styles():
    s = getSampleStyleSheet()
    custom = {
        "co_name": ParagraphStyle("co_name", fontName="Helvetica-Bold", fontSize=14,
                                   spaceAfter=2, alignment=TA_LEFT),
        "co_addr": ParagraphStyle("co_addr", fontName="Helvetica", fontSize=8,
                                   spaceAfter=1, textColor=colors.HexColor("#555555")),
        "section_hdr": ParagraphStyle("section_hdr", fontName="Helvetica-Bold", fontSize=9,
                                       textColor=colors.HexColor("#1a3a5c"), spaceAfter=4,
                                       spaceBefore=6),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9, spaceAfter=3,
                                leading=13),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8,
                                 textColor=colors.HexColor("#666666")),
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=12,
                                 spaceAfter=8, alignment=TA_CENTER,
                                 textColor=colors.HexColor("#1a3a5c")),
        "right": ParagraphStyle("right", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT),
        "total": ParagraphStyle("total", fontName="Helvetica-Bold", fontSize=10,
                                 alignment=TA_RIGHT),
        "informal": ParagraphStyle("informal", fontName="Courier", fontSize=9,
                                    leading=14, spaceAfter=2),
        "informal_bold": ParagraphStyle("informal_bold", fontName="Courier-Bold", fontSize=10,
                                         leading=14, spaceAfter=4),
        "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8,
                                textColor=colors.HexColor("#AA4400"), spaceBefore=4),
    }
    return custom


# ─── Formal letterhead PDF ────────────────────────────────────────────────────
def generate_formal_pdf(out_path, supplier, project, doc_no, doc_date,
                         line_items, validity_days, payment_terms,
                         anomaly_notes=None, missing_delivery=False,
                         escalation_version=None):
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm, bottomMargin=14*mm
    )
    st = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    header_data = [
        [Paragraph(supplier["name"], st["co_name"]),
         Paragraph("QUOTATION", st["title"])],
        [Paragraph(supplier["address"], st["co_addr"]),
         Paragraph(f"<b>Ref No:</b> {doc_no}", st["right"])],
        [Paragraph(f"GST: {supplier['gst'] or 'N/A'}  |  Tel: {supplier['phone']}", st["co_addr"]),
         Paragraph(f"<b>Date:</b> {doc_date.strftime('%d-%b-%Y')}", st["right"])],
        [Paragraph(f"Email: {supplier['email']}", st["co_addr"]),
         Paragraph(f"<b>Valid till:</b> {(doc_date + timedelta(days=validity_days)).strftime('%d-%b-%Y')}", st["right"])],
    ]
    hdr_table = Table(header_data, colWidths=[105*mm, 65*mm])
    hdr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#1a3a5c")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 6))

    # ── To / Project Info ─────────────────────────────────────────────────────
    to_data = [
        [Paragraph("<b>To:</b>", st["body"]),
         Paragraph("Nexusolve Manufacturing Pvt Ltd,<br/>Plot 22, Phase II, Ranjangaon MIDC, Pune 412220", st["body"])],
        [Paragraph("<b>Project:</b>", st["body"]),
         Paragraph(f"{project['name']} — {project['description']}", st["body"])],
        [Paragraph("<b>Project Ref:</b>", st["body"]),
         Paragraph(project["id"], st["body"])],
    ]
    to_table = Table(to_data, colWidths=[28*mm, 142*mm])
    to_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fa")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(to_table)
    story.append(Spacer(1, 8))

    if escalation_version:
        story.append(Paragraph(
            f"<b>Note:</b> This is Revision {escalation_version} of our earlier quotation "
            f"({doc_no.replace('R2','R1').replace('R3','R2')}). Prices revised due to raw material cost increase.",
            st["note"]
        ))
        story.append(Spacer(1, 4))

    story.append(Paragraph("SCOPE OF SUPPLY / SERVICES", st["section_hdr"]))

    # ── Line Items Table ──────────────────────────────────────────────────────
    currency = supplier["currency"]
    col_hdrs = ["#", "Description", "Unit", "Qty", f"Unit Price\n({currency})", f"Amount\n({currency})"]
    tbl_data = [col_hdrs]
    grand_total = 0

    for i, item in enumerate(line_items, 1):
        qty = item["qty"]
        up = item["unit_price"]
        amt = round(qty * up, 2)
        grand_total += amt
        tbl_data.append([
            str(i),
            item["desc"],
            item["unit"],
            str(qty),
            f"{up:,.2f}",
            f"{amt:,.2f}",
        ])

    # Totals rows
    if supplier["gst"] and currency == "INR":
        gst_rate = 0.18
        gst_amt = round(grand_total * gst_rate, 2)
        grand_with_gst = round(grand_total + gst_amt, 2)
        tbl_data.append(["", "", "", "", "Sub-Total", f"{grand_total:,.2f}"])
        tbl_data.append(["", "", "", "", "GST @ 18%", f"{gst_amt:,.2f}"])
        tbl_data.append(["", "", "", "", "GRAND TOTAL", f"{grand_with_gst:,.2f}"])
    else:
        tbl_data.append(["", "", "", "", "TOTAL", f"{grand_total:,.2f}"])

    col_ws = [10*mm, 76*mm, 13*mm, 13*mm, 24*mm, 24*mm]
    items_table = Table(tbl_data, colWidths=col_ws, repeatRows=1)
    n = len(tbl_data)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, n-4), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID", (0, 0), (-1, n-4), 0.3, colors.HexColor("#cccccc")),
        ("LINEABOVE", (0, n-3), (-1, n-3), 0.8, colors.HexColor("#1a3a5c")),
        ("FONTNAME", (0, n-1), (-1, n-1), "Helvetica-Bold"),
        ("FONTSIZE", (0, n-1), (-1, n-1), 9),
        ("BACKGROUND", (0, n-1), (-1, n-1), colors.HexColor("#dde8f5")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (1, 0), (1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 8))

    # ── Terms ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("TERMS & CONDITIONS", st["section_hdr"]))
    terms_data = [
        ["Payment Terms:", payment_terms],
        ["Validity:", f"{validity_days} days from date of quotation"],
    ]
    if not missing_delivery:
        lead = supplier["typical_lead_days"] + random.randint(-5, 10)
        terms_data.append(["Delivery:", f"{lead} days from receipt of PO & advance"])
    else:
        terms_data.append(["Delivery:", "To be confirmed after receipt of PO"])  # ANOMALY: vague

    terms_data += [
        ["Warranty:", "12 months from date of commissioning"],
        ["Taxes:", f"{'GST @ 18% extra as applicable' if supplier['gst'] else 'Taxes as per applicable law'}"],
        ["Freight:", "Inclusive up to Pune site" if currency == "INR" else "Ex-works Dubai, freight extra"],
    ]

    if anomaly_notes:
        for note in anomaly_notes:
            story.append(Paragraph(f"&#9888; {note}", st["note"]))

    terms_tbl = Table(terms_data, colWidths=[35*mm, 135*mm])
    terms_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.2, colors.HexColor("#dddddd")),
    ]))
    story.append(terms_tbl)
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#aaaaaa")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "We trust the above is in order and look forward to your valued purchase order. "
        "For any clarifications, please contact us.",
        st["small"]
    ))
    story.append(Spacer(1, 16))
    story.append(Paragraph(f"For {supplier['name']}", st["body"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph("________________________", st["body"]))
    story.append(Paragraph(f"{supplier['contact']}<br/>Authorised Signatory", st["small"]))

    doc.build(story)


# ─── Informal / typed style PDF ───────────────────────────────────────────────
def generate_informal_pdf(out_path, supplier, project, doc_no, doc_date,
                           line_items, validity_days, payment_terms,
                           missing_delivery=False):
    """Plain courier-font style — simulates older supplier typed quotation."""
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=22*mm, rightMargin=22*mm,
        topMargin=18*mm, bottomMargin=14*mm
    )
    st = _styles()
    story = []

    story.append(Paragraph(supplier["name"].upper(), st["informal_bold"]))
    story.append(Paragraph(supplier["address"], st["informal"]))
    story.append(Paragraph(f"Ph: {supplier['phone']}   E: {supplier['email']}", st["informal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"Quotation No: {doc_no}          Date: {doc_date.strftime('%d/%m/%Y')}",
        st["informal_bold"]
    ))
    story.append(Paragraph(f"Valid for: {validity_days} days", st["informal"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph(f"To,\nNexusolve Mfg. Pvt. Ltd., Pune", st["informal"]))
    story.append(Paragraph(f"Subject: Quotation for {project['name']} - {project['category']}", st["informal_bold"]))
    story.append(Spacer(1, 6))

    story.append(Paragraph("Dear Sir/Madam,", st["informal"]))
    story.append(Paragraph(
        "We are pleased to submit our quotation for your requirement as under:",
        st["informal"]
    ))
    story.append(Spacer(1, 6))

    currency = supplier["currency"]
    grand_total = 0
    for i, item in enumerate(line_items, 1):
        qty = item["qty"]
        up = item["unit_price"]
        amt = round(qty * up, 2)
        grand_total += amt
        line = (f"{i}. {item['desc']}\n"
                f"   Qty: {qty} {item['unit']}   "
                f"Rate: {currency} {up:,.2f}/{item['unit']}   "
                f"Amt: {currency} {amt:,.2f}")
        story.append(Paragraph(line, st["informal"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph(f"{'='*60}", st["informal"]))
    if supplier["gst"] and currency == "INR":
        gst_amt = round(grand_total * 0.18, 2)
        story.append(Paragraph(f"Sub-Total : INR {grand_total:,.2f}", st["informal"]))
        story.append(Paragraph(f"GST @18%  : INR {gst_amt:,.2f}", st["informal"]))
        story.append(Paragraph(f"TOTAL     : INR {grand_total + gst_amt:,.2f}", st["informal_bold"]))
    else:
        story.append(Paragraph(f"TOTAL : {currency} {grand_total:,.2f}", st["informal_bold"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Payment : {payment_terms}", st["informal"]))
    if not missing_delivery:
        lead = supplier["typical_lead_days"] + random.randint(-3, 7)
        story.append(Paragraph(f"Delivery : {lead} days from PO date", st["informal"]))
    story.append(Paragraph(f"Freight  : To be borne by supplier upto site", st["informal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Thanking you,", st["informal"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"{supplier['contact']}", st["informal_bold"]))
    story.append(Paragraph(supplier["name"], st["informal"]))

    doc.build(story)
