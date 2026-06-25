"""
SQLAlchemy ORM models for the NexuSolve CRM data layer.

Schema:
  - Supplier         Master table for supplier entities
  - Project          Project categories
  - Quotation        Quotation header (one per document)
  - LineItem         Individual line items within a quotation
  - DeliveryTerm     Delivery/freight/warranty terms per quotation
  - StatusHistory    Audit trail for quotation status changes
  - ObservabilityLog Pipeline and system metrics
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, Enum, ForeignKey,
    JSON, Boolean, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class QuotationStatus(str, enum.Enum):
    RECEIVED = "received"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Supplier Master ──────────────────────────────────────────────────────────
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String(20), primary_key=True)                # SUP001, SUP002...
    name = Column(String(200), nullable=False)
    contact = Column(String(100))
    email = Column(String(200))
    phone = Column(String(50))
    address = Column(Text)
    gst = Column(String(50))
    currency = Column(String(10), default="INR")
    typical_lead_days = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    quotations = relationship("Quotation", back_populates="supplier")


# ── Project ──────────────────────────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id = Column(String(30), primary_key=True)                # PROJ-ALPHA, etc.
    name = Column(String(100), nullable=False)
    category = Column(String(100))
    description = Column(Text)

    quotations = relationship("Quotation", back_populates="project")


# ── Quotation Header ────────────────────────────────────────────────────────
class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(20), unique=True, nullable=False)  # DOC-001, etc.
    doc_no = Column(String(100), nullable=False)               # Supplier ref no
    supplier_id = Column(String(20), ForeignKey("suppliers.id"), nullable=False)
    project_id = Column(String(30), ForeignKey("projects.id"), nullable=False)
    doc_date = Column(DateTime)
    validity_days = Column(Integer)
    valid_until = Column(DateTime)
    payment_terms = Column(Text)
    currency = Column(String(10))
    total_excl_tax = Column(Float, default=0)
    total_incl_tax = Column(Float, default=0)
    status = Column(
        Enum(QuotationStatus),
        default=QuotationStatus.RECEIVED,
        nullable=False,
    )
    format = Column(String(30))                                # pdf_formal, xlsx, etc.
    file_path = Column(String(500))
    ingestion_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    anomalies_json = Column(Text, default="[]")                # JSON list of anomaly tags
    risk_summary = Column(Text)                                # LLM-generated risk summary
    risk_score = Column(Float, default=0)                      # 0-100 composite risk score
    notes = Column(Text)

    # Relationships
    supplier = relationship("Supplier", back_populates="quotations")
    project = relationship("Project", back_populates="quotations")
    line_items = relationship("LineItem", back_populates="quotation",
                              cascade="all, delete-orphan")
    delivery_term = relationship("DeliveryTerm", back_populates="quotation",
                                 uselist=False, cascade="all, delete-orphan")
    status_history = relationship("StatusHistory", back_populates="quotation",
                                  cascade="all, delete-orphan")
    risk_flags = relationship("RiskFlag", back_populates="quotation",
                              cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_quotation_supplier", "supplier_id"),
        Index("ix_quotation_project", "project_id"),
        Index("ix_quotation_status", "status"),
        Index("ix_quotation_date", "doc_date"),
    )


# ── Line Item ────────────────────────────────────────────────────────────────
class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    seq_no = Column(Integer)
    description = Column(Text, nullable=False)
    unit = Column(String(20))
    quantity = Column(Float)
    unit_price = Column(Float)
    amount = Column(Float)
    market_price_benchmark = Column(Float)                     # For comparison

    quotation = relationship("Quotation", back_populates="line_items")

    __table_args__ = (
        Index("ix_lineitem_description", "description"),
        Index("ix_lineitem_quotation", "quotation_id"),
    )


# ── Delivery Terms ───────────────────────────────────────────────────────────
class DeliveryTerm(Base):
    __tablename__ = "delivery_terms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    delivery_days = Column(Integer)
    delivery_text = Column(Text)
    freight_terms = Column(Text)
    warranty = Column(Text)

    quotation = relationship("Quotation", back_populates="delivery_term")


# ── Risk Flag ────────────────────────────────────────────────────────────────
class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    flag_type = Column(String(100), nullable=False)
    severity = Column(Enum(RiskSeverity), default=RiskSeverity.MEDIUM)
    field = Column(String(100))                                # Which field triggered it
    value = Column(Text)                                       # The actual value
    explanation = Column(Text, nullable=False)                 # Why this is flagged
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    quotation = relationship("Quotation", back_populates="risk_flags")


# ── Status History (Audit Trail) ─────────────────────────────────────────────
class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    old_status = Column(String(20))
    new_status = Column(String(20), nullable=False)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    changed_by = Column(String(100), default="system")
    notes = Column(Text)

    quotation = relationship("Quotation", back_populates="status_history")


# ── Observability Log ────────────────────────────────────────────────────────
class ObservabilityLog(Base):
    __tablename__ = "observability_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    stage = Column(String(50), nullable=False)                 # ingestion, search, llm, etc.
    operation = Column(String(100), nullable=False)
    duration_ms = Column(Float, default=0)
    tokens_used = Column(Integer, default=0)
    tokens_prompt = Column(Integer, default=0)
    tokens_completion = Column(Integer, default=0)
    error = Column(Text)
    metadata_json = Column(Text, default="{}")

    __table_args__ = (
        Index("ix_obs_stage", "stage"),
        Index("ix_obs_timestamp", "timestamp"),
    )
