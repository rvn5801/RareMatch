import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan — startup/shutdown events ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    logger.info("=" * 50)
    logger.info("RareMatch API starting up")
    logger.info("Docs available at http://localhost:8000/docs")
    logger.info("=" * 50)
    yield
    logger.info("RareMatch API shutting down")


# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title       = "RareMatch API",
    description = """
## RareMatch — AI-Powered Rare Disease Drug Repurposing Engine

**Core principle: The AI reads. Python decides. Safety gates everything.**

### How it works
1. Doctor inputs a rare disease name
2. PubMed API fetches real research abstracts (live)
3. AI extracts broken pathway + mechanism (GoF/LoF/DN) — never recommends drugs
4. Python matches pathway to drug database (deterministic, no hallucination)
5. OpenFDA API enriches safety data with live FDA label text
6. Safety filter applies patient constraints → Red/Yellow/Green traffic lights

### Key endpoints
- `POST /api/search` — Run the full pipeline
- `GET /api/health`  — Verify system status
- `GET /api/diseases` — Known benchmark diseases
- `GET /api/drug/{id}` — Drug deep-dive
    """,
    version     = "1.0.0",
    lifespan    = lifespan,
)

# ── CORS — allow Streamlit frontend to call the API ────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Register routes under /api prefix ─────────────────────────
app.include_router(router, prefix="/api")


# ── Root redirect to docs ──────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "RareMatch API is running",
        "docs":    "http://localhost:8000/docs",
        "health":  "http://localhost:8000/api/health",
    }