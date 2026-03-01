import json
import logging
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional
from pydantic import BaseModel

from backend.core.matching_engine import MatchResult, DrugCandidate

logger = logging.getLogger(__name__)

# ── OpenFDA Constants ──────────────────────────────────────────
OPENFDA_BASE    = "https://api.fda.gov/drug/label.json"
REQUEST_TIMEOUT = 6
REQUEST_DELAY   = 0.3   # Respect OpenFDA rate limit (240/min)

# ── Safety Flag Values ─────────────────────────────────────────
GREEN  = "GREEN"
YELLOW = "YELLOW"
RED    = "RED"


# ── Pydantic Models ────────────────────────────────────────────

class PatientConstraints(BaseModel):
    """
    Doctor-entered patient context.
    All fields optional — filter applies only what is provided.
    """
    patient_age:          Optional[int]       = None   # Years
    is_pediatric:         bool                = False
    avoid_liver_toxicity: bool                = False
    avoid_immunosuppression: bool             = False
    avoid_cardiac_risk:   bool                = False
    custom_avoid:         list[str]           = []     # Free-text avoid list


class SafetyProfile(BaseModel):
    """Enriched safety profile — DB data + live OpenFDA data merged."""
    black_box_warning:    str
    pediatric_flag:       str   # GREEN | YELLOW | RED
    pediatric_note:       str
    liver_toxicity:       str
    major_side_effects:   list
    contraindications:    list
    missing_data:         str
    # OpenFDA live fields
    fda_warnings:         Optional[str] = None
    fda_boxed_warning:    Optional[str] = None
    fda_pediatric_use:    Optional[str] = None
    fda_source:           str           = "db_only"   # db_only | openfda_enriched


class RankedResult(BaseModel):
    """Final output — one drug entry ready for UI display."""
    rank:                 int
    drug_id:              str
    drug_name:            str
    generic_name:         str
    brand_names:          list
    drug_class:           str
    target_pathway:       str
    pathway_action:       str
    confidence_score:     int
    evidence_links:       list
    evidence_summary:     str
    known_effective_diseases: list
    approval_status:      str
    match_reason:         str
    direction_flag:       str
    validation_plan:      str
    safety:               SafetyProfile
    # Final traffic light — set by safety filter
    traffic_light:        str   # GREEN | YELLOW | RED
    traffic_reason:       str   # Why this flag was assigned
    # Patient-specific flags
    patient_flags:        list  = []   # List of specific warnings for this patient


class FilteredResult(BaseModel):
    """Complete output from safety filter — passed directly to UI."""
    disease_name:         str
    inferred_mechanism:   str
    disrupted_pathway:    str
    pathway_status:       str
    required_action:      str
    mechanism_confidence: int
    abstract_source:      str
    evidence_quote:       str
    pathway_matched:      bool
    biological_cousins:   Optional[dict] = None
    patient_constraints:  Optional[PatientConstraints] = None
    ranked_drugs:         list[RankedResult]
    total_candidates:     int
    safety_summary:       dict   # Counts of RED/YELLOW/GREEN


# ── Core Safety Filter Class ───────────────────────────────────

class SafetyFilter:

    def __init__(self):
        self._openfda_cache: dict = {}   # In-memory cache: query → FDA data
        logger.info("SafetyFilter initialized")

    # ── Public Methods ─────────────────────────────────────────

    def apply(
        self,
        match_result: MatchResult,
        constraints: Optional[PatientConstraints] = None
    ) -> FilteredResult:
        """
        Main entry point.
        Takes MatchResult + patient constraints → FilteredResult.
        """
        if constraints is None:
            constraints = PatientConstraints()

        # Auto-set is_pediatric if age provided
        if constraints.patient_age is not None and constraints.patient_age < 18:
            constraints.is_pediatric = True

        ranked_drugs = []
        for candidate in match_result.candidates:
            result = self._process_candidate(candidate, constraints)
            ranked_drugs.append(result)

        # Re-sort: RED last within same rank group, GREEN first
        ranked_drugs.sort(
            key=lambda d: (
                0 if d.direction_flag == "OK" else 1,
                {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(d.traffic_light, 3),
                -d.confidence_score
            )
        )

        # Re-assign ranks after safety sort
        for i, drug in enumerate(ranked_drugs):
            drug.rank = i + 1

        summary = self._build_summary(ranked_drugs)

        return FilteredResult(
            disease_name          = match_result.disease_name,
            inferred_mechanism    = match_result.inferred_mechanism,
            disrupted_pathway     = match_result.disrupted_pathway,
            pathway_status        = match_result.pathway_status,
            required_action       = match_result.required_action,
            mechanism_confidence  = match_result.confidence_score,
            abstract_source       = match_result.abstract_source,
            evidence_quote        = match_result.evidence_quote,
            pathway_matched       = match_result.pathway_matched,
            biological_cousins    = match_result.biological_cousins,
            patient_constraints   = constraints,
            ranked_drugs          = ranked_drugs,
            total_candidates      = len(ranked_drugs),
            safety_summary        = summary,
        )

    # ── Private Methods ────────────────────────────────────────

    def _process_candidate(
        self,
        candidate: DrugCandidate,
        constraints: PatientConstraints
    ) -> RankedResult:
        """
        Process one drug candidate:
        1. Fetch OpenFDA safety data
        2. Merge with DB safety data
        3. Apply patient constraint rules
        4. Assign final traffic light
        """
        # Step 1: Get live OpenFDA data
        fda_data = self._fetch_openfda(candidate.openfda_query)

        # Step 2: Build enriched safety profile
        safety = self._build_safety_profile(candidate.safety, fda_data)

        # Step 3: Apply constraint rules → get flags
        patient_flags, traffic_light, traffic_reason = self._apply_constraints(
            candidate, safety, constraints
        )

        # Step 4: Direction block always overrides to RED
        if candidate.direction_flag == "BLOCKED":
            traffic_light  = RED
            traffic_reason = f"MECHANISTIC MISMATCH: {candidate.mechanism_action} is contraindicated for {candidate.target_pathway} in this disease mechanism."

        return RankedResult(
            rank                     = candidate.rank,
            drug_id                  = candidate.drug_id,
            drug_name                = candidate.drug_name,
            generic_name             = candidate.generic_name,
            brand_names              = candidate.brand_names,
            drug_class               = candidate.drug_class,
            target_pathway           = candidate.target_pathway,
            pathway_action           = candidate.pathway_action,
            confidence_score         = candidate.confidence_score,
            evidence_links           = candidate.evidence_links,
            evidence_summary         = candidate.evidence_summary,
            known_effective_diseases = candidate.known_effective_diseases,
            approval_status          = candidate.approval_status,
            match_reason             = candidate.match_reason,
            direction_flag           = candidate.direction_flag,
            validation_plan          = candidate.validation_plan,
            safety                   = safety,
            traffic_light            = traffic_light,
            traffic_reason           = traffic_reason,
            patient_flags            = patient_flags,
        )

    def _apply_constraints(
        self,
        candidate: DrugCandidate,
        safety: SafetyProfile,
        constraints: PatientConstraints
    ) -> tuple[list, str, str]:
        """
        Apply patient constraints to determine traffic light.
        Returns: (patient_flags, traffic_light, traffic_reason)

        Rules (in priority order — first RED wins):
          1. Confidence 0 → always RED (safety trap)
          2. Direction BLOCKED → RED (handled in caller)
          3. Pediatric RED flag + pediatric patient → RED
          4. Liver toxicity SEVERE + avoid_liver_toxicity → RED
          5. Cardiac risk + avoid_cardiac_risk → RED
          6. Custom avoid list matches → RED
          7. Pediatric YELLOW + pediatric patient → YELLOW
          8. Any other YELLOW flag → YELLOW
          9. All clear → GREEN
        """
        flags   = []
        reasons = []

        # Rule 1: Confidence 0 = safety trap
        if candidate.confidence_score == 0:
            return (
                ["SAFETY TRAP: This drug is included as a contraindication test case"],
                RED,
                "Confidence score 0 — this drug is a known contraindication for this disease mechanism"
            )

        # Rule 3: Pediatric + RED pediatric flag
        if constraints.is_pediatric and safety.pediatric_flag == RED:
            flags.append(f"PEDIATRIC RED: {safety.pediatric_note}")
            reasons.append("Not approved or contraindicated in pediatric patients")

        # Rule 4: Liver toxicity
        liver = safety.liver_toxicity.upper()
        if constraints.avoid_liver_toxicity and any(
            word in liver for word in ["SEVERE", "HIGH"]
        ):
            flags.append(f"LIVER TOXICITY: {safety.liver_toxicity} — patient constraint active")
            reasons.append("Significant liver toxicity with patient liver avoidance constraint")

        # Rule 5: Cardiac risk
        if constraints.avoid_cardiac_risk:
            cardiac_keywords = ["cardiomyopathy", "cardiac", "QT prolongation", "PAH", "valvulopathy"]
            side_effects_str = " ".join(safety.major_side_effects).lower()
            if any(k.lower() in side_effects_str for k in cardiac_keywords):
                flags.append("CARDIAC RISK: Cardiac side effects detected with avoidance constraint active")
                reasons.append("Cardiac risk with patient cardiac avoidance constraint")

        # Rule 6: Custom avoid list
        for avoid_term in constraints.custom_avoid:
            avoid_lower = avoid_term.lower()
            contraindications_str = " ".join(safety.contraindications).lower()
            side_effects_str      = " ".join(safety.major_side_effects).lower()
            if avoid_lower in contraindications_str or avoid_lower in side_effects_str:
                flags.append(f"CUSTOM AVOID: '{avoid_term}' matched in safety profile")
                reasons.append(f"Patient constraint '{avoid_term}' matched")

        # Determine final traffic light
        if reasons:
            return flags, RED, " | ".join(reasons)

        # Rule 7-8: YELLOW conditions
        yellow_reasons = []

        if constraints.is_pediatric and safety.pediatric_flag == YELLOW:
            yellow_reasons.append(f"Pediatric monitoring required: {safety.pediatric_note}")

        if any(word in liver for word in ["MODERATE", "LOW-MODERATE"]):
            yellow_reasons.append(f"Moderate liver monitoring advised: {safety.liver_toxicity}")

        if safety.black_box_warning and safety.black_box_warning not in ["None.", "None"]:
            yellow_reasons.append("Black box warning present — review before use")

        if yellow_reasons:
            flags.extend(yellow_reasons)
            return flags, YELLOW, yellow_reasons[0]

        return [], GREEN, "No critical flags for this patient profile"

    def _fetch_openfda(self, query: str) -> Optional[dict]:
        """
        Fetch drug label data from OpenFDA API.
        Returns parsed dict with key safety fields or None.
        Uses in-memory cache to avoid repeat calls.
        """
        if query in self._openfda_cache:
            return self._openfda_cache[query]

        try:
            time.sleep(REQUEST_DELAY)
            encoded = urllib.parse.quote(f'"{query}"')
            url     = f"{OPENFDA_BASE}?search=openfda.generic_name:{encoded}&limit=1"
            req     = urllib.request.Request(
                url,
                headers={"User-Agent": "RareMatch/1.0 (rarematch@hackathon.dev)"}
            )
            response = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
            raw      = response.read().decode("utf-8")
            data     = json.loads(raw)

            results = data.get("results", [])
            if not results:
                self._openfda_cache[query] = None
                return None

            label = results[0]
            parsed = {
                "boxed_warning": self._extract_field(label, "boxed_warning"),
                "warnings":      self._extract_field(label, "warnings"),
                "pediatric_use": self._extract_field(label, "pediatric_use"),
                "contraindications": self._extract_field(label, "contraindications"),
                "adverse_reactions": self._extract_field(label, "adverse_reactions"),
            }

            self._openfda_cache[query] = parsed
            logger.info(f"OpenFDA data fetched for '{query}'")
            return parsed

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info(f"OpenFDA: no label found for '{query}'")
            else:
                logger.warning(f"OpenFDA HTTP error for '{query}': {e.code}")
            self._openfda_cache[query] = None
            return None
        except Exception as e:
            logger.warning(f"OpenFDA fetch failed for '{query}': {e}")
            self._openfda_cache[query] = None
            return None

    def _build_safety_profile(
        self,
        db_safety: dict,
        fda_data: Optional[dict]
    ) -> SafetyProfile:
        """
        Merge DB safety data with OpenFDA live data.
        OpenFDA data enriches — it does not fully replace DB data.
        DB data is the authoritative source for pediatric_flag classification.
        """
        profile = SafetyProfile(
            black_box_warning  = db_safety.get("black_box_warning", "Not available"),
            pediatric_flag     = db_safety.get("pediatric_flag", YELLOW),
            pediatric_note     = db_safety.get("pediatric_note", "No pediatric data available"),
            liver_toxicity     = db_safety.get("liver_toxicity", "Unknown"),
            major_side_effects = db_safety.get("major_side_effects", []),
            contraindications  = db_safety.get("contraindications", []),
            missing_data       = db_safety.get("missing_data", ""),
            fda_source         = "db_only",
        )

        if fda_data:
            # Enrich with live FDA label text
            if fda_data.get("boxed_warning"):
                profile.fda_boxed_warning = fda_data["boxed_warning"][:500]
                # If FDA has a boxed warning that DB doesn't explicitly mention,
                # escalate to YELLOW minimum
                if profile.pediatric_flag == GREEN and profile.fda_boxed_warning:
                    profile.pediatric_flag = YELLOW

            if fda_data.get("warnings"):
                profile.fda_warnings = fda_data["warnings"][:500]

            if fda_data.get("pediatric_use"):
                profile.fda_pediatric_use = fda_data["pediatric_use"][:500]

            profile.fda_source = "openfda_enriched"

        return profile

    def _extract_field(self, label: dict, field: str) -> Optional[str]:
        """Extract a field from FDA label dict — handles list or string."""
        value = label.get(field)
        if isinstance(value, list) and value:
            return value[0][:600]  # First entry, truncated
        if isinstance(value, str):
            return value[:600]
        return None

    def _build_summary(self, ranked_drugs: list) -> dict:
        """Build traffic light count summary for UI header."""
        summary = {GREEN: 0, YELLOW: 0, RED: 0, "total": len(ranked_drugs)}
        for drug in ranked_drugs:
            summary[drug.traffic_light] = summary.get(drug.traffic_light, 0) + 1
        return summary