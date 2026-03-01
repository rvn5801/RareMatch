import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


# ── Helpers ────────────────────────────────────────────────────

def make_mechanism(pathway="mTOR", mechanism="Loss of Function"):
    from backend.core.inference_engine import MechanismResult
    from backend.core.matching_engine import MatchingEngine
    eng = MatchingEngine()
    mech = MechanismResult(
        disease_name                = "Test Disease",
        causative_gene              = "TEST",
        inferred_mechanism          = mechanism,
        disrupted_pathway           = pathway,
        pathway_status              = "Overactive",
        required_therapeutic_action = "Inhibit pathway",
        confidence_score            = 88,
        evidence_quote              = "Test evidence.",
        abstract_source             = "cache",
    )
    return eng.match(mech)


@pytest.fixture(scope="module")
def safety_filter():
    from backend.core.safety_filter import SafetyFilter
    return SafetyFilter()


# ── Safety Filter Tests ────────────────────────────────────────

class TestSafetyFilter:

    def test_pediatric_red_flag_applied(self, safety_filter):
        """Rituximab has RED pediatric flag — age 5 patient should get RED."""
        from backend.core.safety_filter import PatientConstraints, RED
        match = make_mechanism(pathway="FAS/Apoptosis")
        result = safety_filter.apply(match, PatientConstraints(patient_age=5))
        rituximab = next(
            (d for d in result.ranked_drugs if d.drug_name == "Rituximab"), None
        )
        assert rituximab is not None
        assert rituximab.traffic_light == RED

    def test_adult_patient_no_pediatric_flag(self, safety_filter):
        """Adult patient (age 35) should not get pediatric RED."""
        from backend.core.safety_filter import PatientConstraints, RED
        match = make_mechanism(pathway="mTOR")
        result = safety_filter.apply(match, PatientConstraints(patient_age=35))
        sirolimus = next(
            (d for d in result.ranked_drugs if d.drug_name == "Sirolimus"), None
        )
        assert sirolimus is not None
        assert sirolimus.traffic_light != RED or "pediatric" not in sirolimus.traffic_reason.lower()

    def test_liver_avoidance_constraint(self, safety_filter):
        """Valproic acid SEVERE liver toxicity + avoid_liver_toxicity=True → RED."""
        from backend.core.safety_filter import PatientConstraints, RED
        match = make_mechanism(pathway="Sodium Channel", mechanism="Loss of Function")
        result = safety_filter.apply(match, PatientConstraints(avoid_liver_toxicity=True))
        valproate = next(
            (d for d in result.ranked_drugs if "Valproate" in d.drug_name or "Valproic" in d.drug_name), None
        )
        assert valproate is not None
        assert valproate.traffic_light == RED

    def test_cardiac_avoidance_constraint(self, safety_filter):
        """Trametinib cardiomyopathy risk + avoid_cardiac_risk=True → RED."""
        from backend.core.safety_filter import PatientConstraints, RED
        match = make_mechanism(pathway="RAS/MAPK")
        result = safety_filter.apply(match, PatientConstraints(avoid_cardiac_risk=True))
        trametinib = next(
            (d for d in result.ranked_drugs if d.drug_name == "Trametinib"), None
        )
        assert trametinib is not None
        assert trametinib.traffic_light == RED

    def test_safety_summary_counts(self, safety_filter):
        """safety_summary RED+YELLOW+GREEN must equal total."""
        from backend.core.safety_filter import PatientConstraints, GREEN, YELLOW, RED
        match = make_mechanism(pathway="mTOR")
        result = safety_filter.apply(match, PatientConstraints(patient_age=5))
        total   = result.safety_summary["total"]
        counted = (
            result.safety_summary.get(GREEN, 0) +
            result.safety_summary.get(YELLOW, 0) +
            result.safety_summary.get(RED, 0)
        )
        assert total == counted == len(result.ranked_drugs)

    def test_no_constraints_uses_db_flags(self, safety_filter):
        """Without constraints, traffic light reflects DB pediatric_flag."""
        from backend.core.safety_filter import PatientConstraints, RED
        match = make_mechanism(pathway="Complement")
        result = safety_filter.apply(match)
        eculi = next(
            (d for d in result.ranked_drugs if d.drug_name == "Eculizumab"), None
        )
        assert eculi is not None
        assert eculi.traffic_light != RED

    def test_direction_blocked_always_red(self, safety_filter):
        """Carbamazepine in Dravet = BLOCKED direction → always RED."""
        from backend.core.safety_filter import PatientConstraints, RED
        match = make_mechanism(pathway="Sodium Channel", mechanism="Loss of Function")
        result = safety_filter.apply(match, PatientConstraints())
        carba = next(
            (d for d in result.ranked_drugs if d.drug_name == "Carbamazepine"), None
        )
        assert carba is not None
        assert carba.traffic_light == RED

    def test_openfda_failure_uses_db_fallback(self, safety_filter):
        """If OpenFDA unreachable, DB safety data must still produce valid output."""
        from backend.core.safety_filter import PatientConstraints, GREEN, YELLOW, RED
        # Patch at the class method level — works regardless of instance scope
        with patch("backend.services.openfda_client.OpenFDAClient.fetch_label",
                   return_value=None):
            match = make_mechanism(pathway="mTOR")
            result = safety_filter.apply(match, PatientConstraints(patient_age=5))
        assert len(result.ranked_drugs) > 0
        for drug in result.ranked_drugs:
            assert drug.traffic_light in [GREEN, YELLOW, RED]
            assert drug.safety.fda_source == "db_only"

    def test_green_flag_hydroxychloroquine_pediatric(self, safety_filter):
        """Hydroxychloroquine GREEN pediatric flag — should not be RED for child."""
        from backend.core.safety_filter import PatientConstraints, RED
        match = make_mechanism(pathway="FAS/Apoptosis")
        result = safety_filter.apply(match, PatientConstraints(patient_age=10))
        hcq = next(
            (d for d in result.ranked_drugs if "Hydroxychloroquine" in d.drug_name), None
        )
        assert hcq is not None
        assert hcq.traffic_light != RED