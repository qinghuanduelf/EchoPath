"""
Tests for HardshipScorer — Census CSV lookup and Zip→FIPS resolution.
"""

import pytest
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.engines.hardship_scorer import HardshipScorer


@pytest.fixture(scope="module")
def scorer():
    """Create a shared HardshipScorer instance (loads CSV once)."""
    return HardshipScorer()


class TestGetScore:
    """Test hardship score lookups."""

    def test_known_fips_returns_score(self, scorer):
        """Modesto CA (06099) should return a non-default score."""
        score = scorer.get_score("06099")
        assert 0.0 <= score <= 1.0
        assert score != 0.5  # Should NOT be the default

    def test_san_diego_less_hardship_than_modesto(self, scorer):
        """San Diego (06073) should have lower hardship than Modesto (06099)."""
        sd = scorer.get_score("06073")
        modesto = scorer.get_score("06099")
        assert sd < modesto, f"San Diego ({sd}) should be less underserved than Modesto ({modesto})"

    def test_unknown_fips_returns_default(self, scorer):
        """Unknown FIPS should return 0.5 default."""
        score = scorer.get_score("99999")
        assert score == 0.5

    def test_empty_fips_returns_default(self, scorer):
        """Empty string should return 0.5 default."""
        score = scorer.get_score("")
        assert score == 0.5

    def test_score_is_float(self, scorer):
        """Score should be a float."""
        score = scorer.get_score("06037")  # LA County
        assert isinstance(score, float)


class TestResolveFips:
    """Test Zip → FIPS resolution."""

    def test_fips_passthrough(self, scorer):
        """A known FIPS should pass through unchanged."""
        result = scorer.resolve_fips("06073")
        assert result == "06073"

    def test_zip_to_fips(self, scorer):
        """A known zip code should resolve to its FIPS."""
        result = scorer.resolve_fips("90210")
        assert len(result) == 5  # FIPS codes are 5 digits
        assert result.startswith("06")  # Beverly Hills is in California

    def test_unknown_zip_returns_as_is(self, scorer):
        """Unknown input returns as-is."""
        result = scorer.resolve_fips("ZZZZZ")
        assert result == "ZZZZZ"


class TestGetState:
    """Test state extraction from FIPS."""

    def test_california(self, scorer):
        assert scorer.get_state_from_fips("06073") == "06"

    def test_new_york(self, scorer):
        assert scorer.get_state_from_fips("36061") == "36"

    def test_empty(self, scorer):
        assert scorer.get_state_from_fips("") == ""
