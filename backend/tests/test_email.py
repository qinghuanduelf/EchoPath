"""
Tests for EmailGenerator — Prompt building and helper functions (no LLM calls).
"""

import pytest
import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.engines.email_generator import EmailGenerator
from backend.services.llm_service import LLMResult


@pytest.fixture(scope="module")
def generator():
    return EmailGenerator(openai_api_key="")  # No real API key for tests


SAMPLE_STUDENT = {
    "fips_code": "06099",
    "state": "California",
    "hardship_score": 0.45,
    "current_education": "Community College",
    "target_function": "Marketing",
    "target_level": "Manager",
    "dream_description": "I want to work at a top advertising firm",
    "location": "Modesto, CA",
    "school_name": "Modesto Junior College",
}

SAMPLE_MENTOR = {
    "id": "mentor-001",
    "origin_fips": "06099",
    "education": [
        {"school": "Modesto Junior College", "degree": "AA", "field": "Business"},
        {"school": "UC Davis", "degree": "BS", "field": "Marketing"},
    ],
    "position": {
        "title": "Client Marketing Manager",
        "level": "Manager",
        "function": "Marketing",
        "company": {
            "name": "Ad Agency Co",
            "industry": "Advertising",
            "employee_count": 2000,
            "type": "Private",
        },
    },
    "jobs": [
        {
            "title": "Marketing Intern",
            "started_at": "2015-06-01",
            "company": {"name": "Local Firm"},
            "location_details": {"fips_code": "06099"},
        },
        {
            "title": "Marketing Coordinator",
            "started_at": "2017-01-01",
            "company": {"name": "Regional Agency"},
            "location_details": {"fips_code": "06037"},
        },
        {
            "title": "Client Marketing Manager",
            "started_at": "2020-03-01",
            "company": {"name": "Ad Agency Co"},
            "location_details": {"fips_code": "06037"},
        },
    ],
}


class TestBuildPrompt:
    """Test prompt construction."""

    def test_prompt_contains_student_info(self, generator):
        prompt = generator.build_prompt(SAMPLE_STUDENT, SAMPLE_MENTOR, 0.85)
        assert "Modesto, CA" in prompt
        assert "Community College" in prompt
        assert "Marketing" in prompt
        assert "Manager" in prompt
        assert "0.45" in prompt

    def test_prompt_contains_mentor_info(self, generator):
        prompt = generator.build_prompt(SAMPLE_STUDENT, SAMPLE_MENTOR, 0.85)
        assert "Client Marketing Manager" in prompt
        assert "Advertising" in prompt

    def test_prompt_contains_match_score(self, generator):
        prompt = generator.build_prompt(SAMPLE_STUDENT, SAMPLE_MENTOR, 0.85)
        assert "85.0%" in prompt

    def test_prompt_in_english(self, generator):
        prompt = generator.build_prompt(SAMPLE_STUDENT, SAMPLE_MENTOR, 0.85)
        assert "Write in English" in prompt

    def test_prompt_contains_writing_guidelines(self, generator):
        prompt = generator.build_prompt(SAMPLE_STUDENT, SAMPLE_MENTOR, 0.85)
        assert "150-200 words" in prompt
        assert "15-minute call" in prompt


class TestCommonOrigin:
    """Test shared origin detection."""

    def test_same_fips(self, generator):
        result = generator._find_common_origin(SAMPLE_STUDENT, SAMPLE_MENTOR)
        assert "Same region" in result

    def test_same_school(self, generator):
        result = generator._find_common_origin(SAMPLE_STUDENT, SAMPLE_MENTOR)
        assert "Modesto Junior College" in result

    def test_no_overlap(self, generator):
        student = {**SAMPLE_STUDENT, "fips_code": "36061", "school_name": "NYU"}
        mentor = {**SAMPLE_MENTOR, "origin_fips": "06099"}
        # Only state check — different states
        result = generator._find_common_origin(student, mentor)
        # Should still return a fallback connection
        assert "Similar starting background" in result or "Same state" in result


class TestHighlights:
    """Test career highlight extraction."""

    def test_last_three_jobs(self, generator):
        highlights = generator._extract_highlights(SAMPLE_MENTOR)
        assert "Client Marketing Manager" in highlights
        assert "→" in highlights  # Arrow separator

    def test_empty_jobs(self, generator):
        mentor = {"jobs": []}
        highlights = generator._extract_highlights(mentor)
        assert highlights == "N/A"


class TestFormatEducation:
    """Test education formatting."""

    def test_format(self, generator):
        result = generator._format_education(SAMPLE_MENTOR["education"])
        assert "AA" in result
        assert "BS" in result
        assert "UC Davis" in result


class _FakeLLMService:
    async def generate_email(self, prompt, context_documents=None, temperature=0.7, max_tokens=500):
        return LLMResult(
            text="Hello from fake provider",
            provider="rapidfire",
            model="rapidfire-test",
            used_fallback=False,
        )


class _FailingLLMService:
    async def generate_email(self, prompt, context_documents=None, temperature=0.7, max_tokens=500):
        raise RuntimeError("simulated provider failure")


class TestProviderMetadata:
    def test_llm_service_metadata(self):
        gen = EmailGenerator(llm_service=_FakeLLMService())
        text = asyncio.run(gen.generate_email(SAMPLE_STUDENT, SAMPLE_MENTOR, 0.9))
        meta = gen.get_last_generation_metadata()
        assert "fake provider" in text
        assert meta["provider"] == "rapidfire"
        assert meta["model"] == "rapidfire-test"
        assert meta["used_fallback"] is False

    def test_template_fallback_metadata(self):
        gen = EmailGenerator(openai_api_key="", llm_service=_FailingLLMService())
        text = asyncio.run(gen.generate_email(SAMPLE_STUDENT, SAMPLE_MENTOR, 0.8))
        meta = gen.get_last_generation_metadata()
        assert "Email generation requires an API key" in text
        assert meta["provider"] == "template"
        assert meta["used_fallback"] is True
