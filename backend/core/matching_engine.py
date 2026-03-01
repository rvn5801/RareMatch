import json
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from backend.core.inference_engine import MechanismResult

logger      = logging.getLogger(__name__)
DB_PATH     = Path(__file__).parent.parent / "data" / "repurposing_database.json"


# ── Pydantic Models ────────────────────────────────────────────

class DrugCandidate(BaseModel):
    """A single ranked drug candidate — output of matching engine."""
    drug_id:                str
    drug_name:              str
    generic_name:           str
    brand_names:            list
    drug_class:             str
    mechanism_action:       str
    target_pathway:         str
    pathway_action:         str
    confidence_score:       int
    evidence_links:         list
    evidence_summary:       str
    known_effective_diseases: list
    approval_status:        str
    openfda_query:          str
    safety:                 dict
    validation_plan:        str
    # Added by matching engine
    match_reason:           str  = ""
    direction_flag:         str  = "OK"    # OK | MISMATCH | BLOCKED
    rank:                   int  = 0


class MatchResult(BaseModel):
    """Full output from matching engine — passed directly to safety filter."""
    disease_name:           str
    inferred_mechanism:     str
    disrupted_pathway:      str
    pathway_status:         str
    required_action:        str
    confidence_score:       int
    abstract_source:        str
    evidence_quote:         str
    candidates:             list[DrugCandidate]
    total_found:            int
    pathway_matched:        bool
    biological_cousins:     Optional[dict] = None


# ── Core Engine Class ──────────────────────────────────────────

class MatchingEngine:

    def __init__(self):
        self._db             = self._load_db()
        self._drugs          = {d["drug_id"]: d for d in self._db["drugs"]}
        self._pathway_index  = {
            k: v for k, v in self._db["pathway_drug_index"].items()
            if not k.startswith("_")
        }
        self._synonym_map    = {
            k: v for k, v in self._db["pathway_synonym_map"].items()
            if not k.startswith("_")
        }
        self._direction_rules = {
            k: v for k, v in self._db["mechanism_action_rules"].items()
            if not k.startswith("_")
        }
        logger.info(
            f"MatchingEngine ready — "
            f"{len(self._drugs)} drugs, {len(self._pathway_index)} pathways"
        )

    # ── Public Methods ─────────────────────────────────────────

    def match(
        self,
        mechanism_result: MechanismResult,
        cousins: Optional[dict] = None
    ) -> MatchResult:
        """
        Main entry point.
        Takes MechanismResult → returns ranked MatchResult.
        """
        pathway   = self._resolve_pathway(mechanism_result.disrupted_pathway)
        mechanism = mechanism_result.inferred_mechanism
        candidates = []

        if pathway and pathway in self._pathway_index:
            drug_ids   = self._pathway_index[pathway]
            candidates = self._build_candidates(drug_ids, pathway, mechanism)
            logger.info(
                f"Pathway '{pathway}' matched {len(drug_ids)} drugs "
                f"for mechanism '{mechanism}'"
            )
            pathway_matched = True
        else:
            logger.warning(
                f"Pathway '{mechanism_result.disrupted_pathway}' "
                f"not found in index — returning empty candidates"
            )
            pathway_matched = False

        # Sort: OK direction first, then by confidence score descending
        candidates.sort(
            key=lambda d: (0 if d.direction_flag == "OK" else 1, -d.confidence_score)
        )

        # Assign final ranks
        for i, c in enumerate(candidates):
            c.rank = i + 1

        return MatchResult(
            disease_name        = mechanism_result.disease_name,
            inferred_mechanism  = mechanism,
            disrupted_pathway   = pathway or mechanism_result.disrupted_pathway,
            pathway_status      = mechanism_result.pathway_status,
            required_action     = mechanism_result.required_therapeutic_action,
            confidence_score    = mechanism_result.confidence_score,
            abstract_source     = mechanism_result.abstract_source,
            evidence_quote      = mechanism_result.evidence_quote,
            candidates          = candidates,
            total_found         = len(candidates),
            pathway_matched     = pathway_matched,
            biological_cousins  = cousins,
        )

    # ── Private Methods ────────────────────────────────────────

    def _resolve_pathway(self, pathway_raw: str) -> Optional[str]:
        """
        Map LLM pathway output to canonical pathway key.
        Checks exact match first, then synonym map.
        """
        if not pathway_raw or pathway_raw == "Unknown":
            return None

        # Exact match
        if pathway_raw in self._pathway_index:
            return pathway_raw

        # Synonym lookup — check if pathway_raw appears in any synonym list
        pathway_lower = pathway_raw.lower()
        for canonical, synonyms in self._synonym_map.items():
            if pathway_lower == canonical.lower():
                return canonical
            for syn in synonyms:
                if pathway_lower == syn.lower() or pathway_lower in syn.lower():
                    logger.info(
                        f"Synonym resolved: '{pathway_raw}' → '{canonical}'"
                    )
                    return canonical

        logger.warning(f"Could not resolve pathway '{pathway_raw}' to canonical key")
        return None

    def _build_candidates(
        self,
        drug_ids: list,
        pathway: str,
        mechanism: str
    ) -> list[DrugCandidate]:
        """
        Build DrugCandidate list from drug IDs.
        Applies direction filter for each drug.
        """
        candidates = []
        rules      = self._direction_rules.get(mechanism, {})
        allowed    = rules.get("allowed", [])
        blocked    = rules.get("blocked", [])

        for drug_id in drug_ids:
            drug = self._drugs.get(drug_id)
            if not drug:
                logger.warning(f"Drug ID '{drug_id}' in index but not in drugs array")
                continue

            action          = drug.get("mechanism_action", "")
            direction_flag  = self._check_direction(action, allowed, blocked, mechanism)
            match_reason    = self._build_match_reason(drug, pathway, mechanism, direction_flag)

            candidates.append(DrugCandidate(
                drug_id                  = drug["drug_id"],
                drug_name                = drug["drug_name"],
                generic_name             = drug["generic_name"],
                brand_names              = drug.get("brand_names", []),
                drug_class               = drug["drug_class"],
                mechanism_action         = action,
                target_pathway           = drug["target_pathway"],
                pathway_action           = drug["pathway_action"],
                confidence_score         = drug["confidence_score"],
                evidence_links           = drug.get("evidence_links", []),
                evidence_summary         = drug["evidence_summary"],
                known_effective_diseases = drug.get("known_effective_diseases", []),
                approval_status          = drug["approval_status"],
                openfda_query            = drug.get("openfda_query", drug["generic_name"]),
                safety                   = drug["safety"],
                validation_plan          = drug["validation_plan"],
                match_reason             = match_reason,
                direction_flag           = direction_flag,
            ))

        return candidates

    def _check_direction(
        self,
        action: str,
        allowed: list,
        blocked: list,
        mechanism: str
    ) -> str:
        """
        Check if drug mechanism_action aligns with disease mechanism direction.
        Returns: OK | MISMATCH | BLOCKED | UNKNOWN
        """
        if not mechanism or mechanism == "Unknown":
            return "UNKNOWN"

        # Confidence 0 = always blocked (safety trap entries)
        if action in blocked:
            return "BLOCKED"

        if allowed and action not in allowed:
            return "MISMATCH"

        return "OK"

    def _build_match_reason(
        self,
        drug: dict,
        pathway: str,
        mechanism: str,
        direction_flag: str
    ) -> str:
        """
        Build human-readable match rationale for the UI evidence ledger.
        """
        drug_name = drug["drug_name"]
        action    = drug["mechanism_action"]
        drug_class = drug["drug_class"]

        if direction_flag == "BLOCKED":
            return (
                f" DIRECTION MISMATCH: {drug_name} is a {action} — "
                f"inappropriate for {mechanism} disease mechanism. "
                f"Pathway would be pushed in wrong direction."
            )

        if direction_flag == "MISMATCH":
            return (
                f"UNCERTAIN MATCH: {drug_name} ({action}) may not align "
                f"optimally with {mechanism} mechanism. Review carefully."
            )

        return (
            f" {drug_name} ({drug_class}) targets the {pathway} pathway as a {action}. "
            f"Disease mechanism is {mechanism} — this drug's action is directionally correct."
        )

    def _load_db(self) -> dict:
        with open(DB_PATH) as f:
            return json.load(f)