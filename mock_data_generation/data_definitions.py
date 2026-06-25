"""
Core data definitions for synthetic quotation dataset.
8 suppliers, 5 project categories, varied line items, deliberate anomalies.
"""
import random
from datetime import date, timedelta

# ── 8 Suppliers ──────────────────────────────────────────────────────────────
SUPPLIERS = [
    {
        "id": "SUP001",
        "name": "Shree Metals & Alloys Pvt Ltd",
        "contact": "Rajesh Kumar",
        "email": "rajesh@shreemetals.in",
        "phone": "+91-22-4455-6677",
        "address": "Plot 14, MIDC Industrial Area, Pune 411018",
        "gst": "27AABCS1234A1Z5",
        "currency": "INR",
        "typical_lead_days": 21,
        "price_tier": "mid",          # mid = close to market
        "anomaly": None,
    },
    {
        "id": "SUP002",
        "name": "Apex Fasteners & Hardware Co.",
        "contact": "Priya Sharma",
        "email": "priya.s@apexfasteners.com",
        "phone": "+91-11-2345-6789",
        "address": "47 Industrial Estate, Faridabad 121001",
        "gst": "06AABCA5678B2Z3",
        "currency": "INR",
        "typical_lead_days": 14,
        "price_tier": "low",          # consistently cheap
        "anomaly": None,
    },
    {
        "id": "SUP003",
        "name": "Global Polymer Solutions Ltd",
        "contact": "Suresh Nair",
        "email": "snair@globalpolymers.com",
        "phone": "+91-44-6677-8899",
        "address": "3rd Floor, Olympia Tech Park, Chennai 600032",
        "gst": "33AABCG9012C3Z1",
        "currency": "INR",
        "typical_lead_days": 30,
        "price_tier": "mid",
        "anomaly": None,
    },
    {
        "id": "SUP004",
        "name": "TechnoFab Engineering Works",
        "contact": "Amit Desai",
        "email": "amit@technofab.co.in",
        "phone": "+91-79-3344-5566",
        "address": "Survey No. 88, Sarkhej-Gandhinagar Hwy, Ahmedabad 380054",
        "gst": "24AABCT3456D4Z9",
        "currency": "INR",
        "typical_lead_days": 45,
        "price_tier": "high_outlier",  # ANOMALY: quotes 40% above market
        "anomaly": "price_outlier_40pct",
    },
    {
        "id": "SUP005",
        "name": "Indo-Gulf Procurement Services",
        "contact": "Farhan Sheikh",
        "email": "farhan@indogulf.ae",
        "phone": "+971-4-567-8901",
        "address": "Office 1204, Al Quoz Ind Area 4, Dubai, UAE",
        "gst": None,
        "currency": "USD",             # ANOMALY: currency mismatch for domestic project
        "typical_lead_days": 60,
        "price_tier": "mid",
        "anomaly": "currency_mismatch",
    },
    {
        "id": "SUP006",
        "name": "Reliable Rubber & Seals Mfg.",
        "contact": "Deepa Pillai",
        "email": "deepa@reliablerubber.in",
        "phone": "+91-484-2233-4455",
        "address": "NH-47, Edappally, Kochi 682024",
        "gst": "32AABCR7890E5Z7",
        "currency": "INR",
        "typical_lead_days": 18,
        "price_tier": "mid",
        "anomaly": None,
    },
    {
        "id": "SUP007",
        "name": "Electrotech Switchgear Industries",
        "contact": "Vikram Joshi",
        "email": "vjoshi@electrotech.in",
        "phone": "+91-20-6655-4433",
        "address": "Block D, Bhosari MIDC, Pune 411026",
        "gst": "27AABCE4567F6Z2",
        "currency": "INR",
        "typical_lead_days": 30,
        "price_tier": "escalating",    # ANOMALY: price escalation between versions
        "anomaly": "price_escalation_between_versions",
    },
    {
        "id": "SUP008",
        "name": "PrimeCast Foundry & Forge",
        "contact": "Ganesh Reddy",
        "email": "ganesh.r@primecast.in",
        "phone": "+91-40-2244-6688",
        "address": "IDA Uppal, Hyderabad 500039",
        "gst": "36AABCP2345G7Z8",
        "currency": "INR",
        "typical_lead_days": 35,
        "price_tier": "low",
        "anomaly": None,
    },
]

# ── 5 Project Categories ──────────────────────────────────────────────────────
PROJECTS = [
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
]

# ── Line Item Catalogue by Category ──────────────────────────────────────────
LINE_ITEMS_CATALOGUE = {
    "Structural Fabrication": [
        {"desc": "MS Plate 6mm IS 2062 E250", "unit": "MT", "market_price": 68000},
        {"desc": "MS Plate 8mm IS 2062 E250", "unit": "MT", "market_price": 70000},
        {"desc": "MS Plate 12mm IS 2062 E350", "unit": "MT", "market_price": 74000},
        {"desc": "MS Angle 65x65x6mm", "unit": "MT", "market_price": 72000},
        {"desc": "MS Channel 150x75mm", "unit": "MT", "market_price": 75000},
        {"desc": "MS I-Beam 200mm (ISMB 200)", "unit": "MT", "market_price": 78000},
        {"desc": "Structural Steel Fabrication Labour", "unit": "MT", "market_price": 18000},
        {"desc": "Primer & Painting (2 coat)", "unit": "SQM", "market_price": 120},
        {"desc": "Anchor Bolts M20x400 Grade 8.8", "unit": "NOS", "market_price": 85},
        {"desc": "Grating Platform 25x3 Serrated", "unit": "SQM", "market_price": 2800},
    ],
    "Electrical Infrastructure": [
        {"desc": "LT Panel 415V 630A ACB Incomer", "unit": "NOS", "market_price": 180000},
        {"desc": "MCB 63A 4-Pole 10kA", "unit": "NOS", "market_price": 3200},
        {"desc": "XLPE Cable 3.5Cx240sqmm Armoured", "unit": "MTR", "market_price": 1850},
        {"desc": "XLPE Cable 4Cx16sqmm Armoured", "unit": "MTR", "market_price": 320},
        {"desc": "PVC Conduit 25mm ISI Marked", "unit": "MTR", "market_price": 45},
        {"desc": "Cable Tray Perforated 300x50mm", "unit": "MTR", "market_price": 480},
        {"desc": "Earth Pit GI Strip 50x6mm", "unit": "NOS", "market_price": 6500},
        {"desc": "Busbar Trunking 800A Aluminium", "unit": "MTR", "market_price": 12000},
        {"desc": "Voltage Stabilizer 50KVA", "unit": "NOS", "market_price": 95000},
        {"desc": "Installation & Testing Labour", "unit": "LS", "market_price": 45000},
    ],
    "Fluid Systems": [
        {"desc": "SS 316L Pipe 2 inch Sch 40", "unit": "MTR", "market_price": 2800},
        {"desc": "MS ERW Pipe 4 inch Sch 40", "unit": "MTR", "market_price": 1200},
        {"desc": "Gate Valve PN16 2 inch SS Body", "unit": "NOS", "market_price": 4500},
        {"desc": "Ball Valve 3-Piece 1 inch SS316", "unit": "NOS", "market_price": 2800},
        {"desc": "Centrifugal Pump 50LPS@30m Head", "unit": "NOS", "market_price": 85000},
        {"desc": "Pressure Gauge 0-16bar Glycerine", "unit": "NOS", "market_price": 850},
        {"desc": "Pipe Fittings SS 2 inch (Lot)", "unit": "LOT", "market_price": 18000},
        {"desc": "Gasket Spiral Wound 2 inch 316SS", "unit": "NOS", "market_price": 620},
        {"desc": "Hydro Testing & Commissioning", "unit": "LS", "market_price": 25000},
        {"desc": "Insulation 50mm Rock Wool Pipe", "unit": "MTR", "market_price": 380},
    ],
    "Mechanical Overhaul": [
        {"desc": "SKF Bearing 6205-2RS Deep Groove", "unit": "NOS", "market_price": 480},
        {"desc": "SKF Bearing 22222 E Spherical", "unit": "NOS", "market_price": 8500},
        {"desc": "Mechanical Seal Type 502 50mm", "unit": "NOS", "market_price": 3800},
        {"desc": "Coupling Fluid 90mm Bore", "unit": "NOS", "market_price": 14000},
        {"desc": "V-Belt A Section Set", "unit": "SET", "market_price": 1200},
        {"desc": "Gearbox Oil SAE 220 GL-4 200L", "unit": "DRUM", "market_price": 18500},
        {"desc": "Shaft Seal Ring 60x80x10", "unit": "NOS", "market_price": 350},
        {"desc": "Overhaul Labour (Rotating Equip)", "unit": "MH", "market_price": 650},
        {"desc": "Alignment Laser Shaft Service", "unit": "NOS", "market_price": 12000},
        {"desc": "Vibration Analysis Service", "unit": "NOS", "market_price": 8000},
    ],
    "Civil & Insulation": [
        {"desc": "Rock Wool Slab 100mm 128kg/m3", "unit": "SQM", "market_price": 680},
        {"desc": "Aluminium Cladding 0.5mm Stucco", "unit": "SQM", "market_price": 420},
        {"desc": "PUF Panel 60mm Cold Room", "unit": "SQM", "market_price": 1850},
        {"desc": "M20 Grade Concrete (RMC)", "unit": "CUM", "market_price": 5800},
        {"desc": "TMT Bar Fe500D 12mm", "unit": "MT", "market_price": 66000},
        {"desc": "OPC 53 Grade Cement", "unit": "BAG", "market_price": 380},
        {"desc": "Sand Fine River Grade", "unit": "CFT", "market_price": 55},
        {"desc": "Waterproofing Coat (2 layer)", "unit": "SQM", "market_price": 180},
        {"desc": "Scaffolding Erection Labour", "unit": "SQM", "market_price": 95},
        {"desc": "Civil Foundation Works (LS)", "unit": "LS", "market_price": 120000},
    ],
}

# ── Payment Terms Variants ────────────────────────────────────────────────────
PAYMENT_TERMS = [
    "30% advance, 70% against delivery",
    "50% advance, 50% on completion",
    "100% against pro-forma invoice",
    "Net 30 days from invoice date",
    "Net 45 days from invoice date",
    "LC at sight",
    "30 days credit after inspection",
    "15% advance, 85% within 7 days of delivery",
    "Payment as per PO terms",          # VAGUE — anomaly trigger
    "TBD upon mutual agreement",        # VERY VAGUE — strong anomaly
]

VALIDITY_DAYS_OPTIONS = [7, 15, 21, 30, 45, 60, 90]

def get_doc_date(offset_days=0):
    base = date(2024, 8, 1)
    return base + timedelta(days=offset_days)

def market_price(item, supplier):
    """Compute price based on supplier tier with randomness."""
    base = item["market_price"]
    tier = supplier["price_tier"]
    if tier == "low":
        factor = random.uniform(0.88, 0.95)
    elif tier == "mid":
        factor = random.uniform(0.97, 1.06)
    elif tier == "high_outlier":
        factor = random.uniform(1.36, 1.44)   # 40% above market
    elif tier == "escalating":
        factor = random.uniform(0.98, 1.05)   # base price, escalation applied separately
    else:
        factor = 1.0
    return round(base * factor, 2)

def random_qty(unit):
    qty_map = {
        "MT": round(random.uniform(2, 25), 2),
        "MTR": random.randint(50, 500),
        "NOS": random.randint(2, 40),
        "SQM": round(random.uniform(20, 200), 1),
        "LOT": 1,
        "LS": 1,
        "SET": random.randint(1, 6),
        "DRUM": random.randint(1, 10),
        "MH": random.randint(20, 200),
        "BAG": random.randint(50, 500),
        "CUM": round(random.uniform(5, 80), 1),
        "CFT": random.randint(100, 1000),
    }
    return qty_map.get(unit, random.randint(5, 50))