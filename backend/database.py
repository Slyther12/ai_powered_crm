"""
Database connection, session management, and initialisation.
Uses SQLite via SQLAlchemy for zero-config local development.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from backend.config import DATABASE_URL
from backend.models import Base
from backend.observability.logger import get_logger

logger = get_logger("database")

# Create engine — enable WAL mode for concurrent reads
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
    echo=False,
)


# Enable WAL mode and foreign keys for SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialised")


def get_db():
    """FastAPI dependency — yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """Get a standalone session (for scripts, not FastAPI routes)."""
    return SessionLocal()
