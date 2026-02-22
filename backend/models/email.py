"""
Pydantic models for email generation requests / responses.
"""

from pydantic import BaseModel
from typing import Optional


class EmailRequest(BaseModel):
    """Request body for email generation."""
    student_id: str               # Session ID from /student/analyze
    mentor_id: str                # Profile ID of the matched mentor
    match_score: float            # 0-1 score from MatchEngine
    dream_description: Optional[str] = None  # Extra personalization text


class EmailResponse(BaseModel):
    """Response body for email generation."""
    email: str                    # Generated email text
    mentor_label: str             # Anonymized label, e.g. "Mentor #a1b2"
    match_score: float
    provider: str = "template"
    model: str = ""
    used_fallback: bool = False
