"""
Application configuration — loads from environment variables with sensible defaults.
"""
import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent          # nexusolve_crm/
DATA_DIR = BASE_DIR / "mock_data"
MANIFEST_PATH = DATA_DIR / "manifest" / "quotation_manifest.json"
DB_PATH = BASE_DIR / "data" / "nexusolve.db"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"
UPLOAD_DIR = BASE_DIR / "uploads"
LOG_DIR = BASE_DIR / "logs"

# Ensure dirs exist
for d in [DB_PATH.parent, CHROMA_DIR, UPLOAD_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# ── LLM (Groq) ──────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    import warnings
    warnings.warn("GROQ_API_KEY is not set. LLM features may fail.")
    
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Embedding / Search ──────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
SEARCH_TOP_K = int(os.getenv("SEARCH_TOP_K", "20"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))

# ── Server ───────────────────────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# ── Observability ────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # json or console