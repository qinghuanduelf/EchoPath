"""
Pydantic models for student data.
"""

from pydantic import BaseModel
from typing import Optional


class StudentInput(BaseModel):
    """Raw student input from the frontend form."""
    zip_code: Optional[str] = None
    fips_code: Optional[str] = None
    current_education: str          # Dropdown: "Community College", "High School", etc.
    target_function: str            # Dropdown: "Software Engineering", "Marketing", etc.
    target_level: str               # Dropdown: "Manager", "Senior Staff", etc.
    dream_description: Optional[str] = None   # Free text, only for email personalization
    school_name: Optional[str] = None


class StudentData(BaseModel):
    """Resolved & enriched student data used by the matching engine."""
    fips_code: str
    state: str                      # Derived from FIPS (first 2 digits → state code)
    hardship_score: float           # 0-1, from HardshipScorer
    current_education: str
    target_function: str
    target_level: str
    dream_description: Optional[str] = None
    school_name: Optional[str] = None
    location: Optional[str] = None  # Human-readable location for email prompt
