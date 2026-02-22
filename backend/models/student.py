"""
Pydantic models for student data.
"""

import re
from pydantic import BaseModel, field_validator
from typing import Optional


class StudentInput(BaseModel):
    """Raw student input from the frontend form."""
    zip_code: Optional[str] = None
    fips_code: Optional[str] = None
    current_education: str          # Dropdown: "Community College", "High School", etc.
    target_function: str            # Dropdown: "Software Engineering", "Marketing", etc.
    target_level: str               # Dropdown: "Manager", "Senior Staff", etc.
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    dream_description: Optional[str] = None   # Free text, only for email personalization
    school_name: Optional[str] = None

    @field_validator("zip_code", mode="before")
    @classmethod
    def validate_us_zip_code(cls, value: Optional[str]) -> Optional[str]:
        """Allow only US ZIP formats/range: 5 digits or ZIP+4, 00501-99950."""
        if value is None:
            return None
        zip_code = str(value).strip()
        if not zip_code:
            return None
        if not re.fullmatch(r"\d{5}(-\d{4})?", zip_code):
            raise ValueError("zip_code must be a valid US ZIP code (12345 or 12345-6789)")
        zip5 = int(zip_code[:5])
        if zip5 < 501 or zip5 > 99950:
            raise ValueError("zip_code must be within US ZIP range 00501 to 99950")
        return zip_code

    @field_validator("expected_salary_min", "expected_salary_max")
    @classmethod
    def validate_salary_bounds(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value < 0:
            raise ValueError("salary must be non-negative")
        if value > 2_000_000:
            raise ValueError("salary must be less than or equal to 2000000")
        return value


class StudentData(BaseModel):
    """Resolved & enriched student data used by the matching engine."""
    fips_code: str
    state: str                      # Derived from FIPS (first 2 digits → state code)
    hardship_score: float           # 0-1, from HardshipScorer
    current_education: str
    target_function: str
    target_level: str
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    dream_description: Optional[str] = None
    school_name: Optional[str] = None
    location: Optional[str] = None  # Human-readable location for email prompt
