import os
import pytest
from unittest.mock import MagicMock, patch


# ── Environment Setup ──────────────────────────────────────────

def pytest_configure(config):
    """
    Set a dummy GEMINI_API_KEY before any tests run.
    This prevents InferenceEngine.__init__ from raising
    EnvironmentError when tests that mock the API are collected.
    """
    os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")


# ── Shared Fixtures ────────────────────────────────────────────

@pytest.fixture(scope="session")
def matching_engine():
    """
    MatchingEngine instance shared across the entire test session.
    No API key needed — pure DB lookup.
    """
    from backend.core.matching_engine import MatchingEngine
    return MatchingEngine()


@pytest.fixture(scope="session")
def safety_filter():
    """
    SafetyFilter instance shared across the entire test session.
    OpenFDA calls are made live — tests mock them where needed.
    """
    from backend.core.safety_filter import SafetyFilter
    return SafetyFilter()


@pytest.fixture
def mock_inference_engine():
    """
    InferenceEngine with Gemini API fully mocked.
    Use this in any test that needs an InferenceEngine
    without making real API calls.
    """
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel") as MockModel:
                mock_instance = MagicMock()
                MockModel.return_value = mock_instance
                from backend.core.inference_engine import InferenceEngine
                engine = InferenceEngine()
                engine.model = mock_instance
                yield engine


@pytest.fixture
def sample_alps_mechanism():
    """
    Pre-built MechanismResult for ALPS — used across matching + safety tests.
    """
    from backend.core.inference_engine import MechanismResult
    return MechanismResult(
        disease_name                = "ALPS",
        causative_gene              = "FAS",
        inferred_mechanism          = "Loss of Function",
        disrupted_pathway           = "mTOR",
        pathway_status              = "Overactive",
        required_therapeutic_action = "Inhibit mTOR pathway",
        confidence_score            = 92,
        evidence_quote              = "mTOR pathway is overactive in ALPS.",
        abstract_source             = "cache",
    )


@pytest.fixture
def sample_dravet_mechanism():
    """
    Pre-built MechanismResult for Dravet — tests the safety trap (Carbamazepine).
    """
    from backend.core.inference_engine import MechanismResult
    return MechanismResult(
        disease_name                = "Dravet Syndrome",
        causative_gene              = "SCN1A",
        inferred_mechanism          = "Loss of Function",
        disrupted_pathway           = "Sodium Channel",
        pathway_status              = "Deficient",
        required_therapeutic_action = "Enhance inhibitory signaling",
        confidence_score            = 88,
        evidence_quote              = "SCN1A loss of function causes sodium channel deficiency.",
        abstract_source             = "cache",
    )