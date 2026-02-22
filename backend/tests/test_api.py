"""
Integration tests for the FastAPI REST API.
Uses TestClient (synchronous wrapper around httpx).
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient that triggers lifespan (engine loading)."""
    with TestClient(app) as c:
        yield c


# ──────────── Health ────────────


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ──────────── Hardship endpoint ────────────


class TestHardship:
    def test_known_fips(self, client):
        resp = client.get("/api/v1/hardship/06099")
        assert resp.status_code == 200
        data = resp.json()
        assert data["fips_code"] == "06099"
        assert 0.0 <= data["hardship_score"] <= 1.0

    def test_unknown_fips(self, client):
        resp = client.get("/api/v1/hardship/99999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hardship_score"] == 0.5  # default for unknown


# ──────────── Analyze endpoint ────────────


class TestAnalyze:
    """Tests for POST /api/v1/student/analyze."""

    def test_analyze_with_fips(self, client):
        payload = {
            "fips_code": "06099",
            "current_education": "Community College",
            "target_function": "Marketing",
            "target_level": "Manager",
        }
        resp = client.post("/api/v1/student/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Must have a session ID
        assert "session_id" in data
        assert isinstance(data["session_id"], str)

        # Must have hardship + fips
        assert data["fips_code"] == "06099"
        assert 0.0 <= data["hardship_score"] <= 1.0

        # Matches and paths are lists
        assert isinstance(data["matches"], list)
        assert isinstance(data["paths"], list)
        assert "path_source" in data
        assert "rag_hits_count" in data

    def test_analyze_with_zip(self, client):
        payload = {
            "zip_code": "90210",
            "current_education": "High School",
            "target_function": "Software Engineering",
            "target_level": "Staff",
        }
        resp = client.post("/api/v1/student/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data

    def test_analyze_missing_location(self, client):
        payload = {
            "current_education": "High School",
            "target_function": "Software Engineering",
            "target_level": "Staff",
        }
        resp = client.post("/api/v1/student/analyze", json=payload)
        assert resp.status_code == 400

    def test_analyze_returns_match_structure(self, client):
        payload = {
            "fips_code": "06037",
            "current_education": "State University",
            "target_function": "Engineering",
            "target_level": "Senior Staff",
        }
        resp = client.post("/api/v1/student/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        if data["matches"]:
            match = data["matches"][0]
            assert "profile_id" in match
            assert "total_score" in match
            assert "dimension_scores" in match
            assert "profile_snapshot" in match


# ──────────── Session retrieval ────────────


class TestSessionRetrieval:
    """Tests for GET /student/{id}/paths and /student/{id}/matches."""

    @pytest.fixture(scope="class")
    def session_id(self, client):
        """Run an analyze call and return the session id."""
        payload = {
            "fips_code": "06037",
            "current_education": "Community College",
            "target_function": "Marketing",
            "target_level": "Manager",
        }
        resp = client.post("/api/v1/student/analyze", json=payload)
        return resp.json()["session_id"]

    def test_get_paths(self, client, session_id):
        resp = client.get(f"/api/v1/student/{session_id}/paths")
        assert resp.status_code == 200
        assert "paths" in resp.json()

    def test_get_matches(self, client, session_id):
        resp = client.get(f"/api/v1/student/{session_id}/matches")
        assert resp.status_code == 200
        assert "matches" in resp.json()

    def test_invalid_session(self, client):
        resp = client.get("/api/v1/student/nonexistent/paths")
        assert resp.status_code == 404


# ──────────── Match detail ────────────


class TestMatchDetail:
    def test_nonexistent_profile(self, client):
        resp = client.get("/api/v1/match/does-not-exist")
        assert resp.status_code == 404


# ──────────── Email generation ────────────


class TestEmailGeneration:
    """Tests for POST /api/v1/email/generate and /regenerate."""

    @pytest.fixture(scope="class")
    def analyze_result(self, client):
        payload = {
            "fips_code": "06037",
            "current_education": "Community College",
            "target_function": "Marketing",
            "target_level": "Manager",
        }
        resp = client.post("/api/v1/student/analyze", json=payload)
        return resp.json()

    def test_generate_email(self, client, analyze_result):
        if not analyze_result["matches"]:
            pytest.skip("No matches to generate email for")

        first_match = analyze_result["matches"][0]
        payload = {
            "student_id": analyze_result["session_id"],
            "mentor_id": first_match["profile_id"],
            "match_score": first_match["total_score"],
        }
        resp = client.post("/api/v1/email/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert len(data["email"]) > 0
        assert "mentor_label" in data
        assert data["mentor_label"].startswith("Mentor #")
        assert "provider" in data
        assert "used_fallback" in data

    def test_regenerate_email(self, client, analyze_result):
        if not analyze_result["matches"]:
            pytest.skip("No matches to generate email for")

        first_match = analyze_result["matches"][0]
        payload = {
            "student_id": analyze_result["session_id"],
            "mentor_id": first_match["profile_id"],
            "match_score": first_match["total_score"],
        }
        resp = client.post("/api/v1/email/regenerate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert "provider" in data

    def test_generate_with_invalid_session(self, client):
        payload = {
            "student_id": "fake-session",
            "mentor_id": "fake-mentor",
            "match_score": 0.5,
        }
        resp = client.post("/api/v1/email/generate", json=payload)
        assert resp.status_code == 404
