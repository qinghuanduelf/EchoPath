"""
EchoPath Backend Configuration.
Centralized paths, constants, and environment variable loading.
"""

import os
from pathlib import Path

# ──────────── Paths ────────────

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

CENSUS_CSV_PATH = DATA_DIR / "census_hardship.csv"
SCHOOL_TIERS_PATH = DATA_DIR / "school_tiers.json"
FIPS_ZIP_MAP_PATH = DATA_DIR / "fips_zip_map.csv"
ALUMNI_PROCESSED_PATH = PROCESSED_DIR / "alumni_processed.json"


def _load_env_file(path: Path):
    """
    Minimal .env loader to keep runtime dependency-free.
    Existing exported env vars take precedence.
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


# Load from project root first, then backend-local override.
_load_env_file(PROJECT_ROOT / ".env")
_load_env_file(BACKEND_DIR / ".env")

# ──────────── API Keys ────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
RAPIDFIRE_API_KEY = os.getenv("RAPIDFIRE_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")

# ──────────── AI / Retrieval Runtime ────────────

RAPIDFIRE_BASE_URL = os.getenv("RAPIDFIRE_BASE_URL", "")
RAPIDFIRE_MODEL = os.getenv("RAPIDFIRE_MODEL", "rapidfire-default")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# Comma-separated list, e.g. "rapidfire,gemini,openai"
LLM_PROVIDER_ORDER = [
    item.strip().lower()
    for item in os.getenv("LLM_PROVIDER_ORDER", "gemini,openai").split(",")
    if item.strip()
]

PG_DSN = os.getenv("PG_DSN", "")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "auto").strip().lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "8"))

# ──────────── Constants ────────────

# Job level ordering (for level progression calculation)
LEVEL_ORDER = {
    "Intern": 0,
    "Staff": 1,
    "Senior Staff": 2,
    "Manager": 3,
    "Senior Manager": 4,
    "Director": 5,
    "VP": 6,
    "C-Suite": 7,
    "CXO": 7,
    "Owner": 7,
    "Partner": 6,
}

# Education label → tier number mapping (for user dropdown input)
EDU_LABEL_TO_TIER = {
    "High School": 0,
    "Community College": 1,
    "State University": 2,
    "Flagship State University": 3,
    "Private University": 4,
    "Ivy League": 5,
}

# Tier number → display label (for path builder groupby keys)
TIER_LABELS = {
    0: "High School",
    1: "Community College",
    2: "State Univ",
    3: "Flagship State",
    4: "Private Elite",
    5: "Ivy League",
}

# Match engine weights
MATCH_WEIGHTS = {
    "geo_score": 0.20,
    "edu_tier_score": 0.20,
    "hardship_score": 0.15,
    "function_score": 0.20,
    "state_score": 0.10,
    "level_score": 0.15,
}

# Frontend target_function → alumni career_function alias mapping
# This bridges the user-friendly frontend labels to the alumni data categories.
FUNCTION_ALIAS_MAP: dict[str, list[str]] = {
    "Software Engineering": ["Engineering", "Information Technology"],
    "Data Science": ["Engineering", "Information Technology"],
    "Product Management": ["Marketing and Product", "Program and Project Management"],
    "Marketing": ["Marketing and Product"],
    "Finance": ["Finance and Administration", "Banking and Wealth Management"],
    "Consulting": ["Consulting", "Business Management"],
    "Design": ["Marketing and Product", "Engineering"],
    "Sales": ["Sales and Support"],
    "Operations": ["Operations", "Business Management"],
    "Human Resources": ["Human Resources"],
    "Legal": ["Legal", "Risk, Safety, Compliance"],
    "Healthcare": ["Healthcare"],
    "Education": ["Education"],
    "Research": ["Engineering", "Education", "Healthcare"],
}

# 2-digit state FIPS prefix → full state name
STATE_FIPS_MAP: dict[str, str] = {
    "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
    "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
    "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
    "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa",
    "20": "Kansas", "21": "Kentucky", "22": "Louisiana", "23": "Maine",
    "24": "Maryland", "25": "Massachusetts", "26": "Michigan", "27": "Minnesota",
    "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska",
    "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
    "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio",
    "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
    "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
    "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
    "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming",
    "72": "Puerto Rico",
}
