import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.inference_engine import InferenceEngine
from backend.core.matching_engine import MatchingEngine
from backend.core.safety_filter import SafetyFilter, PatientConstraints, FilteredResult

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Singleton engines — instantiated once, reused per request ──
_inference = None
_matching  = None
_safety    = None

def get_engines():
    """Lazy-load engines on first request — avoids startup crash if API key missing."""
    global _inference, _matching, _safety
    if _inference is None:
        _inference = InferenceEngine()
    if _matching is None:
        _matching  = MatchingEngine()
    if _safety is None:
        _safety    = SafetyFilter()
    return _inference, _matching, _safety


# ── Request / Response Schemas ─────────────────────────────────

class SearchRequest(BaseModel):
    """
    Request body for POST /api/search
    Only disease_name is required — all constraints are optional.
    """
    disease_name:             str   = Field(..., min_length=2, max_length=100)
    patient_age:              Optional[int]  = Field(None, ge=0, le=120)
    avoid_liver_toxicity:     bool  = Field(False)
    avoid_immunosuppression:  bool  = Field(False)
    avoid_cardiac_risk:       bool  = Field(False)
    custom_avoid:             list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "disease_name": "ALPS",
                "patient_age": 8,
                "avoid_liver_toxicity": False,
                "avoid_cardiac_risk": False,
                "custom_avoid": []
            }
        }

class SearchResponse(BaseModel):
    """Wrapper around FilteredResult with timing metadata."""
    success:       bool
    duration_ms:   int
    result:        Optional[FilteredResult] = None
    error:         Optional[str]            = None

class HealthResponse(BaseModel):
    status:        str
    engines_ready: bool
    database_drugs: int
    database_pathways: int

class DiseaseListResponse(BaseModel):
    known_diseases:  list[str]
    total:           int
    note:            str


class PathwayListResponse(BaseModel):
    pathways:        list[str]
    total:           int


# ── Routes ─────────────────────────────────────────────────────

@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search for repurposed drugs",
    description="""
    Main RareMatch pipeline.

    1. Fetches PubMed abstracts for the disease (live or cached)
    2. AI extracts broken pathway and mechanism (GoF/LoF/DN)
    3. Python matches pathway to drug database — no AI drug guessing
    4. OpenFDA enriches safety data per drug
    5. Safety filter applies patient constraints
    6. Returns ranked drugs with Red/Yellow/Green traffic lights

    **The AI never recommends drugs — it only reads literature.**
    """,
    tags=["Search"]
)
async def search(request: SearchRequest) -> SearchResponse:
    start = time.time()

    try:
        inference, matching, safety = get_engines()

        # Step 1 — AI reads PubMed, extracts mechanism
        logger.info(f"Search request: disease='{request.disease_name}' age={request.patient_age}")
        mechanism = inference.analyze(request.disease_name)

        # Step 2 — Find biological cousins (cross-disease matching)
        cousins = None
        if mechanism.disrupted_pathway != "Unknown":
            cousins = inference.find_biological_cousins(mechanism)

        # Step 3 — Python matches drugs by pathway (deterministic)
        match_result = matching.match(mechanism, cousins)

        # Step 4 — Build patient constraints from request
        constraints = PatientConstraints(
            patient_age             = request.patient_age,
            avoid_liver_toxicity    = request.avoid_liver_toxicity,
            avoid_immunosuppression = request.avoid_immunosuppression,
            avoid_cardiac_risk      = request.avoid_cardiac_risk,
            custom_avoid            = request.custom_avoid,
        )

        # Step 5 — Safety filter + OpenFDA enrichment
        filtered = safety.apply(match_result, constraints)

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            f"Search complete: '{request.disease_name}' → "
            f"{filtered.total_candidates} drugs in {duration_ms}ms "
            f"(source: {filtered.abstract_source})"
        )

        return SearchResponse(
            success     = True,
            duration_ms = duration_ms,
            result      = filtered,
        )

    except EnvironmentError as e:
        # Missing API key — tell the user clearly
        logger.error(f"Environment error: {e}")
        raise HTTPException(
            status_code = 503,
            detail      = f"Configuration error: {str(e)}. Check your .env file."
        )

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error(f"Search failed for '{request.disease_name}': {e}", exc_info=True)
        return SearchResponse(
            success     = False,
            duration_ms = duration_ms,
            error       = f"Search failed: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"]
)
async def health() -> HealthResponse:
    """
    Verify all engines are operational.
    Called by Streamlit frontend on startup.
    """
    try:
        _, matching, _ = get_engines()
        db             = matching._db

        total_drugs    = len(db.get("drugs", []))
        total_pathways = len([
            k for k in db.get("pathway_drug_index", {}).keys()
            if not k.startswith("_")
        ])

        return HealthResponse(
            status            = "ok",
            engines_ready     = True,
            database_drugs    = total_drugs,
            database_pathways = total_pathways,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status            = "degraded",
            engines_ready     = False,
            database_drugs    = 0,
            database_pathways = 0,
        )


@router.get(
    "/diseases",
    response_model=DiseaseListResponse,
    summary="List known benchmark diseases",
    tags=["Database"]
)
async def list_diseases() -> DiseaseListResponse:
    """
    Returns list of diseases with known benchmark drugs in the database.
    Used to populate autocomplete suggestions in the Streamlit UI.
    """
    try:
        _, matching, _ = get_engines()

        # Build unique disease list from known_effective_diseases across all drugs
        diseases = set()
        for drug in matching._db.get("drugs", []):
            for disease in drug.get("known_effective_diseases", []):
                diseases.add(disease)

        sorted_diseases = sorted(diseases)

        return DiseaseListResponse(
            known_diseases = sorted_diseases,
            total          = len(sorted_diseases),
            note           = (
                "These diseases have known benchmark drugs. "
                "You can also search for any rare disease not in this list — "
                "the AI will fetch literature from PubMed automatically."
            )
        )
    except Exception as e:
        logger.error(f"Disease list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pathways",
    response_model=PathwayListResponse,
    summary="List supported biological pathways",
    tags=["Database"]
)
async def list_pathways() -> PathwayListResponse:
    """
    Returns all pathways the matching engine can handle.
    Includes synonyms so frontend can display them.
    """
    try:
        _, matching, _ = get_engines()

        pathways = [
            k for k in matching._pathway_index.keys()
            if not k.startswith("_") and matching._pathway_index[k]
        ]

        return PathwayListResponse(
            pathways = sorted(pathways),
            total    = len(pathways),
        )
    except Exception as e:
        logger.error(f"Pathway list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/drug/{drug_id}",
    summary="Get single drug deep-dive",
    tags=["Database"]
)
async def get_drug(drug_id: str) -> dict:
    """
    Returns full drug entry from database by drug_id.
    Used by Streamlit deep-dive expandable card.
    Example: GET /api/drug/DR001
    """
    try:
        _, matching, _ = get_engines()
        drug = matching._drugs.get(drug_id.upper())

        if not drug:
            raise HTTPException(
                status_code = 404,
                detail      = f"Drug ID '{drug_id}' not found. "
                              f"Valid IDs are DR001–DR026."
            )

        return {"success": True, "drug": drug}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Drug lookup failed for '{drug_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))