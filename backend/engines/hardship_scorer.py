"""
Hardship Scorer — Offline Census CSV lookup.
Maps FIPS codes to education-resource-deprivation scores (0-1, 1 = most underserved).
Also provides Zip → FIPS resolution via HUD crosswalk data.
"""

import pandas as pd
from functools import lru_cache

from backend.config import CENSUS_CSV_PATH, FIPS_ZIP_MAP_PATH, STATE_FIPS_MAP


class HardshipScorer:
    """Look up pre-computed hardship scores for any US county by FIPS code."""

    INDICATORS = {
        "poverty_rate":       0.30,
        "no_bachelor_rate":   0.25,
        "median_income_inv":  0.20,
        "unemployment_rate":  0.15,
        # title1_school_pct omitted — not in current CSV
    }

    def __init__(self, csv_path: str | None = None, zip_fips_path: str | None = None):
        csv_path = csv_path or str(CENSUS_CSV_PATH)
        zip_fips_path = zip_fips_path or str(FIPS_ZIP_MAP_PATH)

        # Load Census hardship data
        self.df = pd.read_csv(csv_path, dtype={"fips_code": str})
        self.df.set_index("fips_code", inplace=True)

        # If 'hardship_score' is not pre-computed in the CSV, compute it
        if "hardship_score" not in self.df.columns:
            self.df["hardship_score"] = sum(
                self.df[col] * weight
                for col, weight in self.INDICATORS.items()
                if col in self.df.columns
            )

        # Load Zip → FIPS mapping
        self._zip_df = pd.read_csv(zip_fips_path, dtype={"zip_code": str, "fips_code": str})
        self._zip_to_fips = dict(
            zip(self._zip_df["zip_code"], self._zip_df["fips_code"])
        )

    @lru_cache(maxsize=4096)
    def get_score(self, fips_code: str) -> float:
        """Return 0-1 hardship score for a FIPS code. 1 = most underserved."""
        if fips_code in self.df.index:
            return float(self.df.loc[fips_code, "hardship_score"])
        return 0.5  # Unknown region defaults to midpoint

    def resolve_fips(self, zip_or_fips: str) -> str:
        """
        Resolve a zip code or FIPS code to a FIPS code.
        If input is already a valid FIPS, return it directly.
        Otherwise try zip → FIPS lookup.
        """
        clean = zip_or_fips.strip()

        # If it's in the FIPS index, return directly
        if clean in self.df.index:
            return clean

        # Try zip → FIPS resolution
        if clean in self._zip_to_fips:
            return self._zip_to_fips[clean]

        # Fallback: return as-is (caller handles unknown)
        return clean

    def resolve_zip_to_fips(self, zip_code: str) -> str | None:
        """
        Resolve a US ZIP code to FIPS.
        Supports ZIP+4 by normalizing to ZIP5.
        """
        clean = zip_code.strip()
        zip5 = clean[:5]
        return self._zip_to_fips.get(zip5)

    def get_state_from_fips(self, fips_code: str) -> str:
        """Convert FIPS code to full state name via 2-digit prefix lookup."""
        prefix = fips_code[:2] if fips_code and len(fips_code) >= 2 else ""
        return STATE_FIPS_MAP.get(prefix, prefix)
