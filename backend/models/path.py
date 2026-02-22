"""
Pydantic models for career path data.
"""

from pydantic import BaseModel


class CareerNode(BaseModel):
    """A single node in a career path."""
    stage: str              # "education" / "first_job" / "mid_career" / "current"
    label: str              # e.g. "Community College" / "Tech Startup (Staff)"
    typical_duration: int   # Average months at this stage
    count: int              # Number of people who passed through this node


class CareerPath(BaseModel):
    """An abstracted career path (sequence of nodes)."""
    nodes: list[CareerNode]
    total_people: int       # Total people who followed this path
    avg_years: float        # Average total career duration in years
    source: str = "path_builder"
    confidence: float = 0.0
    evidence_count: int = 0
