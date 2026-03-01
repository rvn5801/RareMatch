import os
import json
import logging
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

from backend.services.pubmed_client import PubMedClient
from backend.prompts.mechanism_prompt import (
    MECHANISM_EXTRACTION_SYSTEM,
    MECHANISM_EXTRACTION_USER,
    MISSING_DATA_SYSTEM,
    MISSING_DATA_USER,
    COUSIN_FINDER_SYSTEM,
    COUSIN_FINDER_USER,
    VALID_MECHANISMS,
    VALID_PATHWAYS,
    VALID_PATHWAY_STATUS,
)

# ── Setup ──────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).parent.parent / "data" / "repurposing_database.json"

GEMINI_MODEL = "gemini-2.5-flash"       # Fast, cost-effective for hackathon
MAX_RETRIES  = 2                         # Retry once on malformed JSON


# ── Pydantic Models ────────────────────────────────────────────
class MechanismResult(BaseModel):
    """
    Structured output from the AI inference engine.
    Every field is validated — no raw LLM strings passed downstream.
    """
    disease_name:               str
    causative_gene:             str
    inferred_mechanism:         str
    disrupted_pathway:          str
    pathway_status:             str
    required_therapeutic_action: str
    confidence_score:           int  = Field(ge=0, le=100)
    evidence_quote:             str
    # These two are added by the engine, not the LLM
    abstracts_used:             int  = 0
    abstract_source:            str  = 'unknown'  # pubmed_live | cache | fallback
    low_confidence_flag:        bool = False
    missing_data:               Optional[dict] = None

    @validator("inferred_mechanism")
    def validate_mechanism(cls, v):
        if v not in VALID_MECHANISMS + ["Unknown"]:
            raise ValueError(f"Invalid mechanism: {v}. Must be one of {VALID_MECHANISMS}")
        return v

    @validator("disrupted_pathway")
    def validate_pathway(cls, v):
        # Normalize common synonyms before strict check
        synonym_map = {
            "PI3K": "PI3K/AKT", "AKT": "PI3K/AKT", "PIK3CA": "PI3K/AKT",
            "RAS": "RAS/MAPK", "MAPK": "RAS/MAPK", "MEK/ERK": "RAS/MAPK",
            "mTORC1": "mTOR", "mTOR signaling": "mTOR",
            "GABAergic": "GABA", "NMDA": "NMDA/Glutamate",
        }
        v = synonym_map.get(v, v)
        if v not in VALID_PATHWAYS:
            logger.warning(f"Pathway '{v}' not in controlled list — defaulting to 'Unknown'")
            return "Unknown"
        return v

    @validator("pathway_status")
    def validate_status(cls, v):
        # Normalize natural language to controlled vocab
        v_lower = v.lower()
        if any(word in v_lower for word in ["overactive", "hyperactive", "gain", "constitutive", "stuck on"]):
            return "Overactive"
        if any(word in v_lower for word in ["deficient", "loss", "absent", "reduced", "stuck off"]):
            return "Deficient"
        return "Unknown"

    @validator("confidence_score")
    def flag_low_confidence(cls, v, values):
        return v  # flagging happens in engine, not validator


# ── Core Engine Class ──────────────────────────────────────────
class InferenceEngine:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not found. "
                "Copy .env.example to .env and add your key."
            )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self._db = self._load_database()
        self._pubmed = PubMedClient()
        logger.info(f"InferenceEngine ready — model: {GEMINI_MODEL}")

    # ── Public Methods ─────────────────────────────────────────

    def analyze(self, disease_name: str) -> MechanismResult:
        """
        Main entry point.
        1. Load abstracts for disease
        2. Run mechanism extraction
        3. Run missing-data check if confidence < 50
        Returns validated MechanismResult.
        """
        abstracts, source = self._load_abstracts(disease_name)
        result    = self._extract_mechanism(disease_name, abstracts)
        result.abstract_source = source

        # Flag and enrich low-confidence results
        if result.confidence_score < 50:
            result.low_confidence_flag = True
            result.missing_data = self._get_missing_data(
                disease_name, result.confidence_score, abstracts
            )
            logger.warning(
                f"Low confidence ({result.confidence_score}%) for {disease_name}. "
                f"Missing data: {result.missing_data}"
            )

        return result

    def find_biological_cousins(self, result: MechanismResult) -> Optional[dict]:
        """
        Cross-disease matching:
        Given a MechanismResult, find known diseases with same pathway.
        Returns cousin match dict.
        """
        known_library = self._build_known_library()
        prompt = COUSIN_FINDER_USER.format(
            disease_name      = result.disease_name,
            disrupted_pathway = result.disrupted_pathway,
            pathway_status    = result.pathway_status,
            inferred_mechanism= result.inferred_mechanism,
            known_disease_library = known_library,
        )
        raw = self._call_gemini(COUSIN_FINDER_SYSTEM, prompt)
        return self._parse_json_response(raw, fallback={
            "rare_disease": result.disease_name,
            "matched_known_diseases": [],
            "top_match": "None found"
        })

    # ── Private Methods ────────────────────────────────────────

    def _load_abstracts(self, disease_name: str) -> tuple:
        """
        Fetch abstracts via PubMed live API first.
        Falls back to cached .txt file if network unavailable.
        Returns: (abstract_text, source)
          source is 'pubmed_live' | 'cache' | 'fallback'
        """
        return self._pubmed.fetch_abstracts(disease_name)

    def _extract_mechanism(
        self,
        disease_name: str,
        abstracts: str,
        attempt: int = 1
    ) -> MechanismResult:
        """
        Core LLM call. Retries once on JSON parse failure.
        """
        prompt = MECHANISM_EXTRACTION_USER.format(
            disease_name = disease_name,
            abstracts    = abstracts,
        )

        raw      = self._call_gemini(MECHANISM_EXTRACTION_SYSTEM, prompt)
        parsed   = self._parse_json_response(raw, fallback=None)

        if parsed is None:
            if attempt < MAX_RETRIES:
                logger.warning(f"JSON parse failed — retry {attempt}/{MAX_RETRIES}")
                return self._extract_mechanism(disease_name, abstracts, attempt + 1)
            # After retries, return safe fallback result
            logger.error(f"All retries failed for {disease_name}. Returning fallback.")
            return self._fallback_result(disease_name)

        # Validate with pydantic
        try:
            result = MechanismResult(**parsed)
            result.abstracts_used = len(abstracts.split("\n\n"))
            return result
        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            return self._fallback_result(disease_name)

    def _get_missing_data(
        self,
        disease_name: str,
        confidence_score: int,
        abstracts: str
    ) -> Optional[dict]:
        """
        Secondary LLM call for low-confidence results.
        Identifies what evidence is missing.
        """
        prompt = MISSING_DATA_USER.format(
            disease_name     = disease_name,
            confidence_score = confidence_score,
            abstracts        = abstracts,
        )
        raw = self._call_gemini(MISSING_DATA_SYSTEM, prompt)
        return self._parse_json_response(raw, fallback={
            "missing_evidence_type": "Unknown",
            "suggested_search_terms": [],
            "minimum_confidence_blocker": "Insufficient abstract data."
        })

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """
        Single point of contact with the Gemini API.
        All API calls go through here — easier to swap model or mock in tests.
        """
        try:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response    = self.model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return ""

    def _parse_json_response(self, raw: str, fallback) -> Optional[dict]:
        """
        Safely parse LLM JSON output.
        Strips markdown fences if present before parsing.
        """
        if not raw:
            return fallback

        # Strip markdown code fences the LLM sometimes adds despite instructions
        cleaned = raw
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e} | Raw: {raw[:200]}")
            return fallback

    def _fallback_result(self, disease_name: str) -> MechanismResult:
        """
        Safe fallback when AI extraction fails completely.
        Returns Unknown mechanism rather than crashing.
        """
        return MechanismResult(
            disease_name               = disease_name,
            causative_gene             = "Unknown",
            inferred_mechanism         = "Unknown",
            disrupted_pathway          = "Unknown",
            pathway_status             = "Unknown",
            required_therapeutic_action= "Manual review required",
            confidence_score           = 0,
            evidence_quote             = "Extraction failed — no evidence available",
            abstracts_used             = 0,
            low_confidence_flag        = True,
        )

    def _load_database(self) -> dict:
        with open(DATABASE_PATH, "r") as f:
            return json.load(f)

    def _build_known_library(self) -> str:
        """
        Format known diseases from database as a readable string for the cousin prompt.
        """
        lines = []
        for d in self._db.get("diseases", []):
            benchmark = d.get("benchmark_drug", "None established")
            lines.append(
                f"- {d['disease_name']}: {d['disrupted_pathway']} "
                f"({d['pathway_status']}) → {benchmark}"
            )
        return "\n".join(lines)