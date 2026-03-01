import pytest

pytestmark = pytest.mark.unit


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    from backend.core.matching_engine import MatchingEngine
    return MatchingEngine()


def make_mechanism(
    disease="ALPS",
    mechanism="Loss of Function",
    pathway="mTOR",
    status="Overactive",
    confidence=92,
    action="Inhibit mTOR pathway"
):
    from backend.core.inference_engine import MechanismResult
    return MechanismResult(
        disease_name                = disease,
        causative_gene              = "FAS",
        inferred_mechanism          = mechanism,
        disrupted_pathway           = pathway,
        pathway_status              = status,
        required_therapeutic_action = action,
        confidence_score            = confidence,
        evidence_quote              = "Test evidence quote.",
        abstract_source             = "cache",
    )


# ── Matching Engine Tests ──────────────────────────────────────

class TestMatchingEngine:

    def test_alps_matches_mtor_drugs(self, engine):
        """ALPS → mTOR pathway → should return Sirolimus and Everolimus."""
        result = engine.match(make_mechanism())
        drug_names = [c.drug_name for c in result.candidates]
        assert "Sirolimus" in drug_names
        assert result.pathway_matched is True
        assert result.total_found > 0

    def test_syngap1_matches_ras_mapk_drugs(self, engine):
        """SYNGAP1 → RAS/MAPK → should return Selumetinib, Trametinib, Lovastatin."""
        result = engine.match(make_mechanism(
            disease="SYNGAP1",
            pathway="RAS/MAPK",
            action="Inhibit RAS/MAPK pathway"
        ))
        drug_names = [c.drug_name for c in result.candidates]
        assert any(d in drug_names for d in ["Selumetinib", "Trametinib", "Lovastatin"])
        assert result.pathway_matched is True

    def test_synonym_resolution(self, engine):
        """LLM returning 'PIK3CA' should resolve to PI3K/AKT pathway."""
        result = engine.match(make_mechanism(
            disease="PIK3CA-ROS",
            pathway="PIK3CA",
            action="Inhibit PI3K"
        ))
        assert result.pathway_matched is True
        assert result.disrupted_pathway == "PI3K/AKT"

    def test_unknown_pathway_returns_empty(self, engine):
        """Unknown pathway should return empty candidates, not crash."""
        result = engine.match(make_mechanism(pathway="Unknown"))
        assert result.pathway_matched is False
        assert result.total_found == 0

    def test_gof_blocks_activators(self, engine):
        """GoF disease should flag Enhancers as BLOCKED."""
        result = engine.match(make_mechanism(
            mechanism="Gain of Function",
            pathway="GABA",
            action="Inhibit overactive GABA"
        ))
        blocked = [c for c in result.candidates if c.direction_flag == "BLOCKED"]
        assert len(blocked) > 0, "GoF should block Enhancer drugs"

    def test_lof_allows_inhibitors(self, engine):
        """LoF disease should allow Inhibitors (downstream overactivation case)."""
        result = engine.match(make_mechanism(
            mechanism="Loss of Function",
            pathway="mTOR",
            action="Inhibit overactive downstream mTOR"
        ))
        ok_drugs = [c for c in result.candidates if c.direction_flag == "OK"]
        assert len(ok_drugs) > 0, "LoF with Inhibitors should be allowed"

    def test_candidates_ranked_by_confidence(self, engine):
        """First OK candidate should have highest confidence score."""
        result = engine.match(make_mechanism())
        ok_candidates = [c for c in result.candidates if c.direction_flag == "OK"]
        if len(ok_candidates) > 1:
            assert ok_candidates[0].confidence_score >= ok_candidates[1].confidence_score

    def test_carbamazepine_blocked_in_dravet(self, engine):
        """Carbamazepine confidence=0 in Sodium Channel results — critical safety test."""
        result = engine.match(make_mechanism(
            disease="Dravet Syndrome",
            mechanism="Loss of Function",
            pathway="Sodium Channel",
            action="Enhance inhibitory signaling"
        ))
        carba = next(
            (c for c in result.candidates if c.drug_name == "Carbamazepine"), None
        )
        assert carba is not None, "Carbamazepine should appear in Sodium Channel results"
        assert carba.confidence_score == 0

    def test_mechanistic_mismatch_wrong_isoform(self, engine):
        """Idelalisib (PI3Kδ) should have low confidence for PIK3CA-alpha disease."""
        result = engine.match(make_mechanism(
            disease="PIK3CA-ROS",
            mechanism="Gain of Function",
            pathway="PI3K/AKT",
            action="Inhibit PI3K"
        ))
        idelalisib = next(
            (c for c in result.candidates if c.drug_name == "Idelalisib"), None
        )
        assert idelalisib is not None
        assert idelalisib.confidence_score < 20, "Wrong isoform should have very low confidence"