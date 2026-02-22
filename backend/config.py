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
    "geo_score": 0.30,
    "edu_tier_score": 0.25,
    "hardship_score": 0.20,
    "function_score": 0.15,
    "state_score": 0.10,
}
