"""
Match Engine — Multi-dimensional scoring to find alumni with similar starting points.
5 dimensions: geography, education tier, hardship similarity, career function, state.
"""

import json
from datetime import datetime
from functools import lru_cache

from backend.config import (
    SCHOOL_TIERS_PATH, MATCH_WEIGHTS, EDU_LABEL_TO_TIER,
    FUNCTION_ALIAS_MAP, STATE_FIPS_MAP, LEVEL_ORDER,
)
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
        """Compute all 6 dimension scores (each 0-1)."""
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
            "level_score": self._level_score(
                student.get("target_level", ""),
                alumni.get("career_end_level", ""),
            ),
            "salary_score": self._salary_score(
                student.get("expected_salary_min"),
                student.get("expected_salary_max"),
                alumni.get("initial_salary"),
                alumni.get("final_salary"),
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
        """Same state → 1.0, else → 0.0.  Handles FIPS prefix or full name."""
        if not student_state or not alumni_state:
            return 0.0
        # Normalise student_state: convert 2-digit FIPS prefix to full name
        s = STATE_FIPS_MAP.get(student_state, student_state).lower()
        a = alumni_state.lower()
        return 1.0 if s == a else 0.0

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
        """Career function match via alias mapping.
        Direct alias hit → 1.0, partial keyword overlap → 0.3, else → 0.0."""
        if not target_fn or not alumni_fn:
            return 0.0

        # Exact match (case-insensitive)
        if target_fn.lower() == alumni_fn.lower():
            return 1.0

        # Alias map lookup
        aliases = FUNCTION_ALIAS_MAP.get(target_fn, [])
        if alumni_fn in aliases:
            return 1.0

        # Partial keyword overlap (e.g. "Marketing" in "Marketing and Product")
        t_lower = target_fn.lower()
        a_lower = alumni_fn.lower()
        if t_lower in a_lower or a_lower in t_lower:
            return 0.5

        return 0.0

    def _level_score(self, target_level: str, alumni_level: str) -> float:
        """Career level proximity: closer levels score higher."""
        if not target_level or not alumni_level:
            return 0.3  # neutral default
        t = LEVEL_ORDER.get(target_level, 3)
        a = LEVEL_ORDER.get(alumni_level, 3)
        diff = abs(t - a)
        # 0 gap → 1.0, 1 → 0.85, 2 → 0.7, … 7 → 0.0
        return max(0.0, round(1.0 - diff * 0.15, 4))

    @staticmethod
    def _distance_to_range(value: int, low: int, high: int) -> int:
        if value < low:
            return low - value
        if value > high:
            return value - high
        return 0

    def _salary_score(
        self,
        student_min: int | None,
        student_max: int | None,
        alumni_initial: int | None,
        alumni_final: int | None,
    ) -> float:
        """
        Salary range affinity.
        - If student range is not provided, keep neutral score (0.5).
        - If mentor salary fields are missing, keep neutral score (0.5).
        - Closer initial/final salary to expected range => higher score.
        """
        if student_min is None or student_max is None:
            return 0.5

        low = min(student_min, student_max)
        high = max(student_min, student_max)
        span = max(10000, high - low)

        values = [v for v in [alumni_initial, alumni_final] if isinstance(v, int) and v >= 0]
        if not values:
            return 0.5

        scores: list[float] = []
        for val in values:
            dist = self._distance_to_range(val, low, high)
            score = max(0.0, 1.0 - (dist / span))
            scores.append(score)
        return round(sum(scores) / len(scores), 4)

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
            initial_salary=alumni.get("initial_salary"),
            final_salary=alumni.get("final_salary"),
            education_summary=edu_summary,
        )
