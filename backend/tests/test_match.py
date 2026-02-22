"""
Tests for MatchEngine — Multi-dimensional scoring.
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.engines.hardship_scorer import HardshipScorer
from backend.engines.match_engine import MatchEngine


@pytest.fixture(scope="module")
def hardship_scorer():
    return HardshipScorer()


@pytest.fixture(scope="module")
def engine(hardship_scorer):
    return MatchEngine(hardship_scorer)


# ──────────── Synthetic test data ────────────

SAMPLE_STUDENT = {
    "fips_code": "06099",      # Modesto CA
    "state": "California",
    "hardship_score": 0.45,
    "current_education": "Community College",
    "target_function": "Marketing",
    "target_level": "Manager",
}

SAMPLE_ALUMNI_PERFECT = {
    "id": "alumni-001",
    "origin_fips": "06099",
    "origin_state": "California",
    "career_function": "Marketing",
    "career_end_level": "Manager",
    "education": [
        {"school": "Modesto Junior College", "degree": "AA", "field": "Business"},
        {"school": "UC Davis", "degree": "BS", "field": "Marketing"},
    ],
    "position": {
        "title": "Marketing Manager",
        "level": "Manager",
        "function": "Marketing",
        "company": {
            "name": "Acme Corp",
            "industry": "Technology",
            "employee_count": 5000,
            "type": "Private",
        },
    },
    "jobs": [
        {
            "title": "Intern",
            "level": "Intern",
            "function": "Marketing",
            "started_at": "2015-06-01",
            "ended_at": "2016-01-01",
            "duration": 7,
            "company": {"name": "Local Agency", "industry": "Advertising"},
            "location_details": {"fips_code": "06099", "region": "California"},
        },
    ],
}

SAMPLE_ALUMNI_DIFFERENT = {
    "id": "alumni-002",
    "origin_fips": "36061",      # New York County
    "origin_state": "New York",
    "career_function": "Engineering",
    "career_end_level": "VP",
    "education": [
        {"school": "Columbia University", "degree": "BS", "field": "CS"},
    ],
    "position": {
        "title": "VP of Engineering",
        "level": "VP",
        "function": "Engineering",
        "company": {
            "name": "BigCo",
            "industry": "Technology",
            "employee_count": 20000,
            "type": "Public",
        },
    },
    "jobs": [],
}


class TestDimensionScorers:
    """Test individual dimension scoring functions."""

    def test_geo_same_fips(self, engine):
        score = engine._geo_score("06099", "06099")
        assert score == 1.0

    def test_geo_same_state(self, engine):
        score = engine._geo_score("06099", "06037")
        assert score == 0.5

    def test_geo_different_state(self, engine):
        score = engine._geo_score("06099", "36061")
        assert score == 0.0

    def test_geo_empty(self, engine):
        assert engine._geo_score("", "06099") == 0.0
        assert engine._geo_score("06099", "") == 0.0

    def test_state_match(self, engine):
        assert engine._state_score("California", "California") == 1.0

    def test_state_mismatch(self, engine):
        assert engine._state_score("California", "New York") == 0.0

    def test_state_case_insensitive(self, engine):
        assert engine._state_score("california", "California") == 1.0

    def test_edu_tier_same(self, engine):
        """Community college student + alumni from community college → 1.0."""
        score = engine._edu_tier_score(
            "Community College",
            [{"school": "Modesto Junior College"}],
        )
        assert score == 1.0

    def test_edu_tier_far(self, engine):
        """Community college student + alumni from Ivy → low score."""
        score = engine._edu_tier_score(
            "Community College",
            [{"school": "Harvard University"}],
        )
        # Tier 1 vs Tier 5 = diff 4 → 1.0 - 4*0.25 = 0.0
        assert score == 0.0

    def test_hardship_identical(self, engine):
        assert engine._hardship_similarity(0.5, 0.5) == 1.0

    def test_hardship_opposite(self, engine):
        assert engine._hardship_similarity(0.0, 1.0) == 0.0

    def test_function_match(self, engine):
        assert engine._function_score("Marketing", "Marketing") == 1.0

    def test_function_mismatch(self, engine):
        assert engine._function_score("Marketing", "Engineering") == 0.0

    def test_function_case_insensitive(self, engine):
        assert engine._function_score("marketing", "Marketing") == 1.0


class TestFindMatches:
    """Test the full matching pipeline."""

    def test_perfect_match_ranks_higher(self, engine):
        """Alumni with same origin should rank higher than dissimilar."""
        results = engine.find_matches(
            SAMPLE_STUDENT,
            [SAMPLE_ALUMNI_DIFFERENT, SAMPLE_ALUMNI_PERFECT],
            top_k=2,
        )
        assert len(results) == 2
        assert results[0].profile_id == "alumni-001"
        assert results[0].total_score > results[1].total_score

    def test_top_k_limit(self, engine):
        """Should respect top_k limit."""
        many = [SAMPLE_ALUMNI_PERFECT.copy() for _ in range(20)]
        for i, a in enumerate(many):
            a["id"] = f"bulk-{i}"
        results = engine.find_matches(SAMPLE_STUDENT, many, top_k=5)
        assert len(results) == 5

    def test_snapshot_populated(self, engine):
        """Match results should include a valid mentor snapshot."""
        results = engine.find_matches(
            SAMPLE_STUDENT, [SAMPLE_ALUMNI_PERFECT], top_k=1
        )
        snap = results[0].profile_snapshot
        assert snap.current_title == "Marketing Manager"
        assert snap.industry == "Technology"

    def test_empty_alumni_list(self, engine):
        results = engine.find_matches(SAMPLE_STUDENT, [], top_k=10)
        assert results == []
