"""
Data Loader — Singleton service for loading and caching alumni data.
Provides lazy loading of the large alumni_processed.json file.
"""

import json
from typing import Optional

from backend.config import ALUMNI_PROCESSED_PATH


class DataLoader:
    """Lazy-loading alumni data store with optional FIPS-based indexing."""

    _instance: Optional["DataLoader"] = None
    _alumni_data: Optional[list] = None

    def __new__(cls):
        """Singleton pattern — only one instance ever created."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_alumni(self, filepath: str | None = None) -> list:
        """Load alumni data from JSON file (lazy, cached)."""
        if self._alumni_data is not None:
            return self._alumni_data

        path = filepath or str(ALUMNI_PROCESSED_PATH)
        print(f"Loading alumni data from {path}...")
        with open(path, "r") as f:
            self._alumni_data = json.load(f)
        print(f"Loaded {len(self._alumni_data)} alumni profiles.")
        return self._alumni_data

    def get_alumni(self) -> list:
        """Get cached alumni data (loads if not yet loaded)."""
        if self._alumni_data is None:
            return self.load_alumni()
        return self._alumni_data

    def get_profile_by_id(self, profile_id: str) -> dict | None:
        """Look up a single profile by ID."""
        for p in self.get_alumni():
            if p.get("id") == profile_id:
                return p
        return None

    def filter_by_state(self, state_fips_prefix: str) -> list:
        """Return alumni whose origin_fips starts with the given state code."""
        return [
            p for p in self.get_alumni()
            if p.get("origin_fips", "").startswith(state_fips_prefix)
        ]

    def reset(self):
        """Clear cached data (for testing)."""
        self._alumni_data = None
        DataLoader._instance = None
