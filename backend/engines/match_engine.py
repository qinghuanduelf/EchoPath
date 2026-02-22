"""
Match Engine — Multi-dimensional scoring to find alumni with similar starting points.
5 dimensions: geography, education tier, hardship similarity, career function, state.
"""

import json
from datetime import datetime
from functools import lru_cache

from backend.config import SCHOOL_TIERS_PATH, MATCH_WEIGHTS, EDU_LABEL_TO_TIER
from backend.models.mentor import MatchResult, MentorSnapshot, EducationSummary


class MatchEngine:
    """Multi-dimensional scoring engine: find alumni whose starting point
    is most similar to the current student's background."""

    def __init__(self, hardship_scorer, school_tiers_path: str | None = None):
        self.hardship_scorer = hardship_scorer

        # Load school → tier mapping from IPEDS JSON
        tiers_path = school_tiers_path or str(SCHOOL_TIERS_PATH)
        with open(tiers_path, "r") as f:
            self.school_tier_db: dict[str, int] = json.load(f)

        self.weights = MATCH_WEIGHTS

    def find_matches(
        self, student: dict, alumni_list: list, top_k: int = 10
    ) -> list[MatchResult]:
        """
        Score every alumni against the student, return Top-K by total score.

        student keys: fips_code, state, hardship_score, current_education,
                      target_function, target_level
        alumni_list:  list of processed profile dicts (from ETL output)
        """
        results = []
        for alumni in alumni_list:
            scores = self._score_all_dimensions(student, alumni)
            total = sum(scores[k] * self.weights[k] for k in self.weights)
            results.append(MatchResult(
                profile_id=alumni.get("id", ""),
                total_score=round(total, 4),
                dimension_scores={k: round(v, 4) for k, v in scores.items()},
                profile_snapshot=self._build_snapshot(alumni),
            ))

        results.sort(key=lambda r: r.total_score, reverse=True)
        return results[:top_k]

    # ──────────── Dimension Scorers ────────────

    def _score_all_dimensions(self, student: dict, alumni: dict) -> dict:
        """Compute all 5 dimension scores (each 0-1)."""
        alumni_origin_fips = alumni.get("origin_fips", "")
        alumni_origin_state = alumni.get("origin_state", "")

        # Get alumni hardship score from their origin FIPS
        alumni_hardship = self.hardship_scorer.get_score(alumni_origin_fips) if alumni_origin_fips else 0.5

        return {
            "geo_score": self._geo_score(
                student.get("fips_code", ""), alumni_origin_fips
            ),
            "state_score": self._state_score(
                student.get("state", ""), alumni_origin_state
            ),
            "edu_tier_score": self._edu_tier_score(
                student.get("current_education", ""),
                alumni.get("education", []),
            ),
            "hardship_score": self._hardship_similarity(
                student.get("hardship_score", 0.5), alumni_hardship
            ),
            "function_score": self._function_score(
                student.get("target_function", ""),
                alumni.get("career_function", ""),
            ),
        }

    def _geo_score(self, student_fips: str, alumni_fips: str) -> float:
        """Same FIPS=1.0, same state (first 2 digits)=0.5, else 0.0."""
        if not student_fips or not alumni_fips:
            return 0.0
        if student_fips == alumni_fips:
            return 1.0
        if student_fips[:2] == alumni_fips[:2]:
            return 0.5
        return 0.0

    def _state_score(self, student_state: str, alumni_state: str) -> float:
        """Binary: same state → 1.0, else → 0.0."""
        if not student_state or not alumni_state:
            return 0.0
        # Handle both full name and abbreviation
        return 1.0 if student_state.lower() == alumni_state.lower() else 0.0

    def _edu_tier_score(self, student_edu: str, alumni_education: list) -> float:
        """Education tier proximity: tier gap 0→1.0, 1→0.75, ..., 4+→0.0."""
        student_tier = EDU_LABEL_TO_TIER.get(student_edu, 2)

        # Find the earliest (lowest-tier) education for the alumni
        alumni_tiers = []
        for e in alumni_education:
            school = e.get("school", "") if isinstance(e, dict) else ""
            if school:
                alumni_tiers.append(self._school_to_tier(school))

        alumni_earliest_tier = min(alumni_tiers) if alumni_tiers else 2
        diff = abs(student_tier - alumni_earliest_tier)
        return max(0.0, 1.0 - diff * 0.25)

    def _hardship_similarity(self, student_hs: float, alumni_hs: float) -> float:
        """Hardship similarity: closer → higher score."""
        return max(0.0, 1.0 - abs(student_hs - alumni_hs))

    def _function_score(self, target_fn: str, alumni_fn: str) -> float:
        """Career function match: exact match → 1.0, else → 0.0."""
        if not target_fn or not alumni_fn:
            return 0.0
        return 1.0 if target_fn.lower() == alumni_fn.lower() else 0.0

    # ──────────── Helpers ────────────

    def _school_to_tier(self, school_name: str) -> int:
        """Look up school tier from IPEDS database. Default: tier 2."""
        return self.school_tier_db.get(school_name, 2)

    def _build_snapshot(self, alumni: dict) -> MentorSnapshot:
        """Build anonymized mentor snapshot for frontend display."""
        position = alumni.get("position", {})
        company = position.get("company", {})
        education = alumni.get("education", [])

        edu_summary = [
            EducationSummary(
                degree=e.get("degree"),
                field=e.get("field"),
            )
            for e in education
        ]

        return MentorSnapshot(
            current_title=position.get("title"),
            current_level=position.get("level"),
            industry=company.get("industry"),
            company_size=company.get("employee_count"),
            education_summary=edu_summary,
        )
