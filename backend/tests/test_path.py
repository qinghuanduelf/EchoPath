"""
Tests for PathBuilder — 4-stage fingerprint extraction and path aggregation.
"""

import pytest
import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.engines.path_builder import PathBuilder
from backend.engines.path_planner import PathPlanner
from backend.services.llm_service import LLMResult


@pytest.fixture(scope="module")
def builder():
    return PathBuilder()


# ──────────── Synthetic profiles ────────────

def make_profile(edu_school, first_ind, current_level, first_level="Staff",
                 num_jobs=3, career_months=60):
    """Helper: generate a synthetic alumni profile."""
    jobs = []
    for i in range(num_jobs):
        jobs.append({
            "title": f"Job {i}",
            "level": first_level if i == 0 else current_level,
            "function": "Marketing",
            "started_at": f"201{i}-01-01",
            "ended_at": f"201{i+1}-01-01",
            "duration": career_months // num_jobs,
            "company": {"name": f"Company {i}", "industry": first_ind},
            "location_details": {"fips_code": "06099", "region": "California"},
        })

    return {
        "id": f"test-{edu_school}-{current_level}",
        "education": [
            {"school": edu_school, "degree": "BA", "field": "Business"},
        ],
        "jobs": jobs,
        "position": {
            "title": f"{current_level} Role",
            "level": current_level,
            "company": {"industry": first_ind},
        },
    }


class TestFingerprint:
    """Test fingerprint extraction from a single profile."""

    def test_basic_extraction(self, builder):
        profile = make_profile("Modesto Junior College", "Technology", "Manager")
        fp = builder._extract_fingerprint(profile)
        assert fp is not None
        assert fp["edu_tier"] == "Community College"
        assert fp["first_industry"] == "Technology"
        assert fp["current_level"] == "Manager"

    def test_no_jobs_returns_none(self, builder):
        profile = {
            "education": [{"school": "MIT", "degree": "BS", "field": "CS"}],
            "jobs": [],
        }
        fp = builder._extract_fingerprint(profile)
        assert fp is None

    def test_no_education_returns_none(self, builder):
        profile = {
            "education": [],
            "jobs": [{"title": "Dev", "started_at": "2020-01-01", "duration": 12,
                       "company": {"industry": "Tech"}}],
        }
        fp = builder._extract_fingerprint(profile)
        assert fp is None


class TestBuildPaths:
    """Test path building from groups of profiles."""

    def test_single_group(self, builder):
        """5 profiles with same fingerprint → 1 path."""
        profiles = [
            make_profile("Modesto Junior College", "Technology", "Manager")
            for _ in range(5)
        ]
        paths = builder.build_paths(profiles)
        assert len(paths) == 1
        assert paths[0].total_people == 5
        assert paths[0].avg_years > 0
        assert len(paths[0].nodes) == 4

    def test_two_groups(self, builder):
        """Profiles with different fingerprints → 2 paths."""
        group_a = [make_profile("Modesto Junior College", "Technology", "Manager") for _ in range(3)]
        group_b = [make_profile("Stanford", "Finance", "Director") for _ in range(2)]
        paths = builder.build_paths(group_a + group_b, top_n=5)
        assert len(paths) == 2
        # Larger group first
        assert paths[0].total_people == 3

    def test_top_n_limit(self, builder):
        """Should respect top_n limit."""
        profiles = (
            [make_profile("School A", "Industry A", "Staff") for _ in range(5)] +
            [make_profile("School B", "Industry B", "Manager") for _ in range(3)] +
            [make_profile("School C", "Industry C", "Director") for _ in range(2)]
        )
        paths = builder.build_paths(profiles, top_n=2)
        assert len(paths) == 2

    def test_empty_input(self, builder):
        paths = builder.build_paths([])
        assert paths == []

    def test_node_stages(self, builder):
        """Each path should have exactly 4 stages."""
        profiles = [make_profile("Modesto Junior College", "Technology", "Manager")]
        paths = builder.build_paths(profiles)
        assert len(paths) == 1
        stages = [n.stage for n in paths[0].nodes]
        assert stages == ["education", "first_job", "mid_career", "current"]
        assert paths[0].source == "path_builder"
        assert paths[0].evidence_count == 0


class _RapidfireRankerOK:
    async def generate_with_provider(self, provider, prompt, context_documents=None, temperature=0.2, max_tokens=250):
        return LLMResult(
            text='{"ranked_path_indices":[1,0]}',
            provider="rapidfire",
            model="rapidfire-test",
            used_fallback=False,
        )


class _RapidfireRankerFail:
    async def generate_with_provider(self, provider, prompt, context_documents=None, temperature=0.2, max_tokens=250):
        raise RuntimeError("rapidfire unavailable")


class TestPathPlanner:
    def test_path_planner_rapidfire_success(self, builder):
        profiles = (
            [make_profile("Modesto Junior College", "Technology", "Manager") for _ in range(4)] +
            [make_profile("Stanford", "Finance", "Director") for _ in range(3)]
        )
        planner = PathPlanner(path_builder=builder, llm_service=_RapidfireRankerOK())
        paths, meta = asyncio.run(
            planner.plan_paths(
                student={"target_function": "Marketing", "target_level": "Manager"},
                matched_profiles=profiles,
                rag_hits=[{"profile_id": "x1", "similarity": 0.8, "chunk_text": "sample"}],
                top_n=2,
            )
        )
        assert len(paths) == 2
        assert paths[0].source == "rapidfire"
        assert meta["source"] == "rapidfire"

    def test_path_planner_fallback_when_rapidfire_fails(self, builder):
        profiles = [make_profile("Modesto Junior College", "Technology", "Manager") for _ in range(3)]
        planner = PathPlanner(path_builder=builder, llm_service=_RapidfireRankerFail())
        paths, meta = asyncio.run(
            planner.plan_paths(
                student={"target_function": "Marketing", "target_level": "Manager"},
                matched_profiles=profiles,
                rag_hits=[{"profile_id": "x1", "similarity": 0.8, "chunk_text": "sample"}],
                top_n=2,
            )
        )
        assert len(paths) >= 1
        assert paths[0].source == "fallback"
        assert meta["source"] == "fallback"
