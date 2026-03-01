import pytest
import json
from unittest.mock import MagicMock, patch
from backend.core.inference_engine import InferenceEngine, MechanismResult
from backend.prompts.mechanism_prompt import VALID_MECHANISMS, VALID_PATHWAYS

pytestmark = pytest.mark.unit  # Gemini is mocked — no real API calls


# ── Fixtures ───────────────────────────────────────────────────

MOCK_ALPS_RESPONSE = json.dumps({
    "disease_name": "ALPS",
    "causative_gene": "FAS",
    "inferred_mechanism": "Loss of Function",
    "disrupted_pathway": "mTOR",
    "pathway_status": "Overactive",
    "required_therapeutic_action": "Inhibit mTOR pathway",
    "confidence_score": 92,
    "evidence_quote": "mTOR pathway is constitutively overactive in ALPS lymphocytes due to impaired FAS-mediated apoptosis."
})

MOCK_SYNGAP1_RESPONSE = json.dumps({
    "disease_name": "SYNGAP1",
    "causative_gene": "SYNGAP1",
    "inferred_mechanism": "Loss of Function",
    "disrupted_pathway": "RAS/MAPK",
    "pathway_status": "Overactive",
    "required_therapeutic_action": "Inhibit RAS/MAPK pathway",
    "confidence_score": 85,
    "evidence_quote": "Heterozygous loss-of-function mutations in SYNGAP1 cause constitutively active RAS/MAPK signaling."
})

MOCK_LOW_CONFIDENCE_RESPONSE = json.dumps({
    "disease_name": "Unknown Disease",
    "causative_gene": "Unknown",
    "inferred_mechanism": "Unknown",
    "disrupted_pathway": "Unknown",
    "pathway_status": "Unknown",
    "required_therapeutic_action": "Manual review required",
    "confidence_score": 30,
    "evidence_quote": "Insufficient evidence in provided text."
})


@pytest.fixture
def engine_with_mock_api():
    """
    InferenceEngine with Gemini API mocked out.
    Tests logic without real API calls.
    """
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"}):
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel") as MockModel:
                mock_model_instance = MagicMock()
                MockModel.return_value = mock_model_instance
                engine = InferenceEngine()
                engine.model = mock_model_instance
                yield engine


# ── Tests ──────────────────────────────────────────────────────

class TestMechanismExtraction:

    def test_alps_benchmark(self, engine_with_mock_api):
        """
        ALPS should return: LoF mechanism, mTOR pathway, Overactive status.
        This is the ground truth benchmark — if this fails, the engine is broken.
        """
        engine = engine_with_mock_api
        engine.model.generate_content.return_value.text = MOCK_ALPS_RESPONSE

        result = engine.analyze("ALPS")

        assert result.disease_name == "ALPS"
        assert result.causative_gene == "FAS"
        assert result.inferred_mechanism == "Loss of Function"
        assert result.disrupted_pathway == "mTOR"
        assert result.pathway_status == "Overactive"
        assert result.confidence_score == 92
        assert result.low_confidence_flag is False

    def test_syngap1_benchmark(self, engine_with_mock_api):
        """
        SYNGAP1 should return: LoF mechanism, RAS/MAPK pathway, Overactive.
        Note: LoF of a negative regulator = Overactive pathway (important nuance).
        """
        engine = engine_with_mock_api
        engine.model.generate_content.return_value.text = MOCK_SYNGAP1_RESPONSE

        result = engine.analyze("SYNGAP1")

        assert result.inferred_mechanism == "Loss of Function"
        assert result.disrupted_pathway == "RAS/MAPK"
        assert result.pathway_status == "Overactive"
        assert result.confidence_score >= 80
        assert result.low_confidence_flag is False

    def test_low_confidence_flag(self, engine_with_mock_api):
        """
        confidence_score < 50 should set low_confidence_flag = True.
        """
        engine = engine_with_mock_api
        # First call: mechanism extraction (low confidence)
        # Second call: missing data analysis
        engine.model.generate_content.return_value.text = MOCK_LOW_CONFIDENCE_RESPONSE

        result = engine.analyze("Unknown Disease")

        assert result.low_confidence_flag is True
        assert result.confidence_score < 50

    def test_valid_mechanism_values(self, engine_with_mock_api):
        """
        inferred_mechanism must always be in the controlled vocabulary.
        """
        engine = engine_with_mock_api
        engine.model.generate_content.return_value.text = MOCK_ALPS_RESPONSE

        result = engine.analyze("ALPS")
        assert result.inferred_mechanism in VALID_MECHANISMS + ["Unknown"]

    def test_valid_pathway_values(self, engine_with_mock_api):
        """
        disrupted_pathway must always be in the controlled vocabulary.
        """
        engine = engine_with_mock_api
        engine.model.generate_content.return_value.text = MOCK_ALPS_RESPONSE

        result = engine.analyze("ALPS")
        assert result.disrupted_pathway in VALID_PATHWAYS


class TestRobustness:

    def test_malformed_json_returns_fallback(self, engine_with_mock_api):
        """
        If the LLM returns garbage, the engine should NOT crash.
        It should return a safe Unknown fallback.
        """
        engine = engine_with_mock_api
        engine.model.generate_content.return_value.text = "This is not JSON at all!!!"

        result = engine.analyze("Some Disease")

        assert isinstance(result, MechanismResult)
        assert result.inferred_mechanism == "Unknown"
        assert result.confidence_score == 0
        assert result.low_confidence_flag is True

    def test_api_failure_returns_fallback(self, engine_with_mock_api):
        """
        If Gemini API throws an exception, return fallback gracefully.
        """
        engine = engine_with_mock_api
        engine.model.generate_content.side_effect = Exception("API quota exceeded")

        result = engine.analyze("ALPS")

        assert isinstance(result, MechanismResult)
        assert result.confidence_score == 0

    def test_pathway_synonym_normalization(self, engine_with_mock_api):
        """
        The validator in MechanismResult resolves known synonyms.
        'PIK3CA' in the synonym_map → normalizes to 'PI3K/AKT' before validation.
        Confidence score stays at the LLM-returned value since the pathway is valid.
        """
        engine = engine_with_mock_api
        response_with_synonym = json.dumps({
            "disease_name": "PIK3CA Disease",
            "causative_gene": "PIK3CA",
            "inferred_mechanism": "Gain of Function",
            "disrupted_pathway": "PIK3CA",   # synonym in validator map → PI3K/AKT
            "pathway_status": "Overactive",
            "required_therapeutic_action": "Inhibit PI3K",
            "confidence_score": 88,
            "evidence_quote": "PIK3CA mutation leads to constitutive PI3K activation."
        })
        engine.model.generate_content.return_value.text = response_with_synonym

        result = engine.analyze("PIK3CA Disease")
        # Validator resolves PIK3CA → PI3K/AKT — pathway is valid, score preserved
        assert isinstance(result, MechanismResult)
        assert result.disrupted_pathway == "PI3K/AKT"
        assert result.confidence_score == 88


class TestAbstractLoading:

    def test_pubmed_client_initialized(self, engine_with_mock_api):
        """PubMedClient must be initialized inside InferenceEngine."""
        engine = engine_with_mock_api
        assert hasattr(engine, '_pubmed'), \
            "InferenceEngine must have _pubmed attribute (PubMedClient)"

    def test_load_abstracts_returns_tuple(self, engine_with_mock_api):
        """
        _load_abstracts must return (text, source) tuple.
        Mocks PubMed client to avoid real network call in unit tests.
        """
        engine = engine_with_mock_api
        with patch.object(engine._pubmed, 'fetch_abstracts',
                         return_value=("abstract text", "cache")):
            text, source = engine._load_abstracts("ALPS")
            assert isinstance(text, str)
            assert source in ["pubmed_live", "cache", "fallback"]

    def test_alps_cache_exists_after_live_fetch(self):
        """
        If alps.txt cache exists it means PubMed was fetched at least once.
        Run a real search first if this fails:
          POST /api/search with disease_name='ALPS'
        """
        from pathlib import Path
        cache = Path("backend/data/abstracts/alps.txt")
        if not cache.exists():
            pytest.skip(
                "alps.txt cache not yet created — "
                "run POST /api/search with disease_name='ALPS' first"
            )