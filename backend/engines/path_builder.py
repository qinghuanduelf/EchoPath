"""
Path Builder — Extract 4-stage career fingerprints and group into common paths.
Uses simplified Pandas groupby approach (no sequence clustering).
"""

import pandas as pd

from backend.config import SCHOOL_TIERS_PATH, TIER_LABELS
from backend.models.path import CareerNode, CareerPath

import json


class PathBuilder:
    """Build abstracted career paths from matched alumni profiles via
    4-stage fingerprinting + Pandas groupby."""

    def __init__(self, school_tiers_path: str | None = None):
        tiers_path = school_tiers_path or str(SCHOOL_TIERS_PATH)
        with open(tiers_path, "r") as f:
            self.school_tier_db: dict[str, int] = json.load(f)

    def build_paths(
        self, matched_profiles: list, target_function: str = "", top_n: int = 3
    ) -> list[CareerPath]:
        """
        Extract 4-stage fingerprints from matched profiles, group by
        (edu_tier, first_industry, current_level), return Top-N most
        common career paths.
        """
        records = []
        for profile in matched_profiles:
            fp = self._extract_fingerprint(profile)
            if fp:
                records.append(fp)

        if not records:
            return []

        df = pd.DataFrame(records)

        # Group by the 3-key fingerprint
        grouped = df.groupby(["edu_tier", "first_industry", "current_level"])

        paths = []
        for (edu_tier, first_ind, curr_level), group in grouped:
            if len(group) < 1:
                continue

            nodes = [
                CareerNode(
                    stage="education",
                    label=self._safe_mode(group, "edu_label"),
                    typical_duration=int(group["edu_duration"].mean()),
                    count=len(group),
                ),
                CareerNode(
                    stage="first_job",
                    label=f"{first_ind} ({self._safe_mode(group, 'first_level')})",
                    typical_duration=int(group["first_job_duration"].mean()),
                    count=len(group),
                ),
                CareerNode(
                    stage="mid_career",
                    label=self._safe_mode(group, "mid_label"),
                    typical_duration=int(group["mid_duration"].mean()),
                    count=len(group),
                ),
                CareerNode(
                    stage="current",
                    label=f"{curr_level} in {self._safe_mode(group, 'current_industry')}",
                    typical_duration=0,
                    count=len(group),
                ),
            ]

            paths.append(CareerPath(
                nodes=nodes,
                total_people=len(group),
                avg_years=round(group["total_months"].mean() / 12, 1),
            ))

        paths.sort(key=lambda p: p.total_people, reverse=True)
        return paths[:top_n]

    def _extract_fingerprint(self, profile: dict) -> dict | None:
        """Reduce a profile to a 4-stage fingerprint dict for groupby."""
        education = profile.get("education", [])
        jobs = profile.get("jobs", [])

        # Need both education and jobs
        if not jobs or not education:
            return None

        # Sort jobs chronologically
        sorted_jobs = sorted(jobs, key=lambda j: j.get("started_at", "") or "")
        first_job = sorted_jobs[0]
        current_job = sorted_jobs[-1]
        mid_jobs = sorted_jobs[1:-1] if len(sorted_jobs) > 2 else []

        # Education info (earliest entry)
        earliest_edu = education[-1] if education else {}  # last in list is often earliest
        edu_school = earliest_edu.get("school", "")

        return {
            "edu_tier": self._school_tier_label(edu_school),
            "edu_label": f"{earliest_edu.get('degree', 'N/A')} @ {edu_school or 'Unknown'}",
            "edu_duration": earliest_edu.get("duration", 48),  # Default 4 years
            "first_industry": first_job.get("company", {}).get("industry", "Unknown"),
            "first_level": first_job.get("level", "Staff") or "Staff",
            "first_job_duration": first_job.get("duration", 24) or 24,
            "mid_label": (
                mid_jobs[len(mid_jobs) // 2].get("title", "Various")
                if mid_jobs else "Direct"
            ),
            "mid_duration": sum(j.get("duration", 0) or 0 for j in mid_jobs),
            "current_level": current_job.get("level", "Unknown") or "Unknown",
            "current_industry": current_job.get("company", {}).get("industry", "Unknown"),
            "total_months": sum(j.get("duration", 0) or 0 for j in sorted_jobs),
        }

    def _school_tier_label(self, school_name: str) -> str:
        """Map school name → tier label string for groupby key."""
        tier_num = self.school_tier_db.get(school_name, 2)
        return TIER_LABELS.get(tier_num, "State Univ")

    @staticmethod
    def _safe_mode(group: pd.DataFrame, col: str) -> str:
        """Get the mode (most common value) of a column, with fallback."""
        if col not in group.columns:
            return "Various"
        mode = group[col].mode()
        if len(mode) > 0:
            return str(mode.iloc[0])
        return "Various"
