"""
Pydantic models for mentor / match result data.
"""

from pydantic import BaseModel
from typing import Optional


class EducationSummary(BaseModel):
    """Single education record (anonymized)."""
    degree: Optional[str] = None
    field: Optional[str] = None


class MentorSnapshot(BaseModel):
    """Anonymized mentor info for frontend display."""
    current_title: Optional[str] = None
    current_level: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[int] = None
    education_summary: list[EducationSummary] = []


class MatchResult(BaseModel):
    """A single match result with score breakdown."""
    profile_id: str
    total_score: float                  # Weighted sum (0-1)
    dimension_scores: dict[str, float]  # Per-dimension score detail
    profile_snapshot: MentorSnapshot
