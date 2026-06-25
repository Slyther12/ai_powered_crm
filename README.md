# NexuSolve CRM

**AI-Powered Quotation Ingestion & Manufacturing CRM Intelligence System**

NexuSolve CRM automates the ingestion of supplier quotations from multiple formats (PDF, XLSX, CSV, email, scanned documents), normalises the data into a unified schema, and provides AI-powered intelligence features including risk assessment, price benchmarking, and natural language search.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.13+, FastAPI, SQLAlchemy, SQLite |
| **Frontend** | React 19, Vite, React Router, Recharts, Lucide Icons |
| **AI / ML** | Groq (LLM), Sentence Transformers (embeddings), ChromaDB (vector store) |
| **Search** | Hybrid search (BM25 + vector similarity + cross-encoder re-ranking) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                          │
│  Dashboard │ Quotations │ Suppliers │ Compare │ Intelligence   │
│  Upload    │ AI Search  │ Observability                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ REST API (JSON)
┌─────────────────────▼───────────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │Ingestion │  │  Search  │  │  Intel.  │  │Observability │   │
│  │Pipeline  │  │  Engine  │  │  Engine  │  │  Logger      │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────┘   │
│       │              │             │                            │
│  ┌────▼──────────────▼─────────────▼────────────────────────┐  │
│  │              SQLite + ChromaDB (vector store)            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** (Recommended)
- **Python 3.13+** with [uv](https://docs.astral.sh/uv/) package manager (for local dev)
- **Node.js 18+** with npm (for local dev)

### Docker Setup (Recommended)

The easiest way to run NexuSolve CRM is using Docker.

1. **Configure Environment:** Create a `.env` file in the root directory. Be sure to add your API key:
   ```ini
   GROQ_API_KEY=your_api_key_here
   PORT=8000
   HOST=0.0.0.0
   DEBUG=true
   ```

2. **Start the Stack:**
   ```bash
   docker compose up --build
   ```

3. **Access the Application:**
   - Frontend Dashboard: [http://localhost:5173](http://localhost:5173)
   - Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Local Development Setup

#### Backend Setup

```bash
# Install Python dependencies
uv sync

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Start the backend (auto-seeds mock data on first run)
python main.py
```

The backend starts on `http://localhost:8000` with auto-reload enabled.

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend starts on `http://localhost:5173` and proxies API requests to the backend.

### Environment Variables

NexuSolve CRM reads configuration from a `.env` file in the root directory.

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(empty)* | Groq API key for LLM features (Required for AI capabilities) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `DATABASE_URL` | `sqlite:///data/nexusolve.db` | Database connection string |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Enable reload and debug mode |

## Features

- **Multi-Format Ingestion** — PDF, XLSX, CSV, email, and scanned document parsing
- **Unified Data Model** — Normalised quotation schema with supplier/project linkage
- **Risk Assessment** — Automated risk scoring with configurable flag rules
- **Price Benchmarking** — Cross-supplier price comparison with escalation detection
- **Hybrid AI Search** — BM25 + semantic vector search with cross-encoder re-ranking
- **CRM Workflow** — Status tracking (received → reviewed → approved/rejected) with audit trail
- **Observability** — Structured logging, latency tracking, and token usage metrics

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

```
nexusolve_crm/
├── backend/
│   ├── app.py              # FastAPI application & routes
│   ├── config.py           # Configuration & environment
│   ├── database.py         # SQLAlchemy engine & sessions
│   ├── models.py           # ORM models
│   ├── seed_data.py        # Mock data seeding
│   ├── ingestion/          # Document extraction pipeline
│   ├── intelligence/       # Risk engine, benchmarking, LLM
│   ├── search/             # Hybrid search & vector store
│   └── observability/      # Logging & metrics
├── frontend/
│   └── src/
│       ├── App.jsx          # Routes & sidebar layout
│       ├── api/client.js    # API client
│       ├── pages/           # Page components
│       └── index.css        # Design system
├── mock_data_generation/   # Mock data generation scripts
├── mock_data/              # Sample quotation documents
├── data/                   # SQLite DB & ChromaDB
├── logs/                   # Log outputs
├── uploads/                # Uploaded files
├── main.py                 # Application entry point
└── pyproject.toml          # Python dependencies
```
