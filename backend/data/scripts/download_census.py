#!/usr/bin/env python3
"""
Census ACS 5-Year Data Download Script
Downloads economic/education indicators for all US counties and computes hardship scores.
Output: backend/data/census_hardship.csv
"""

import requests
import csv
import os
import sys

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")
YEAR = 2022
BASE_URL = f"https://api.census.gov/data/{YEAR}/acs/acs5"

# ACS variables we need:
# B17001_002E = Population below poverty level
# B17001_001E = Total population (for poverty denominator)
# B15003_001E = Total pop 25+ (education denominator)
# B15003_022E = Bachelor's degree holders (25+)
# B19013_001E = Median household income
# B23025_005E = Unemployed (civilian labor force)
# B23025_002E = In labor force (civilian, denominator for unemployment)
VARIABLES = "B17001_002E,B17001_001E,B15003_001E,B15003_022E,B19013_001E,B23025_005E,B23025_002E"

# Hardship score weights (from PROJECT_DOC §5.4)
WEIGHTS = {
    "poverty_rate": 0.30,
    "no_bachelor_rate": 0.25,
    "median_income_inv": 0.20,
    "unemployment_rate": 0.15,
    # title1_school_pct (0.10) omitted for MVP — data not easily available
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "census_hardship.csv")


def download_acs_data():
    """Download ACS 5-Year data for ALL US counties."""
    if not CENSUS_API_KEY:
        raise RuntimeError("CENSUS_API_KEY is required. Export it before running this script.")

    print(f"Downloading ACS {YEAR} 5-Year data for all US counties...")

    params = {
        "get": VARIABLES,
        "for": "county:*",
        "key": CENSUS_API_KEY,
    }

    resp = requests.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    headers = data[0]
    rows = data[1:]
    print(f"  Downloaded {len(rows)} county records")
    return headers, rows


def safe_int(val):
    """Convert to int, treating negatives and None as 0."""
    try:
        v = int(val)
        return v if v >= 0 else 0
    except (TypeError, ValueError):
        return 0


def safe_float(val):
    """Convert to float, treating negatives and None as 0."""
    try:
        v = float(val)
        return v if v >= 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def compute_indicators(headers, rows):
    """Compute raw indicator rates for each county."""
    records = []

    for row in rows:
        d = dict(zip(headers, row))

        state = d["state"]
        county = d["county"]
        fips_code = f"{state}{county}"

        poverty_pop = safe_int(d["B17001_002E"])
        total_pop_poverty = safe_int(d["B17001_001E"])
        total_25plus = safe_int(d["B15003_001E"])
        bachelors = safe_int(d["B15003_022E"])
        median_income = safe_float(d["B19013_001E"])
        unemployed = safe_int(d["B23025_005E"])
        labor_force = safe_int(d["B23025_002E"])

        # Compute rates (with zero-division protection)
        poverty_rate = poverty_pop / total_pop_poverty if total_pop_poverty > 0 else 0.0
        no_bachelor_rate = 1.0 - (bachelors / total_25plus) if total_25plus > 0 else 1.0
        unemployment_rate = unemployed / labor_force if labor_force > 0 else 0.0

        records.append({
            "fips_code": fips_code,
            "poverty_rate": poverty_rate,
            "no_bachelor_rate": no_bachelor_rate,
            "median_income_raw": median_income,
            "unemployment_rate": unemployment_rate,
        })

    return records


def normalize_and_score(records):
    """Min-max normalize indicators and compute weighted hardship score."""
    # Find min/max for median_income to create inverted normalized score
    incomes = [r["median_income_raw"] for r in records if r["median_income_raw"] > 0]
    income_min = min(incomes) if incomes else 0
    income_max = max(incomes) if incomes else 1

    for r in records:
        # median_income_inv: lower income → higher hardship
        if income_max > income_min and r["median_income_raw"] > 0:
            r["median_income_inv"] = 1.0 - (r["median_income_raw"] - income_min) / (income_max - income_min)
        else:
            r["median_income_inv"] = 0.5  # Default for missing

        # Compute weighted hardship score
        r["hardship_score"] = round(
            r["poverty_rate"] * WEIGHTS["poverty_rate"]
            + r["no_bachelor_rate"] * WEIGHTS["no_bachelor_rate"]
            + r["median_income_inv"] * WEIGHTS["median_income_inv"]
            + r["unemployment_rate"] * WEIGHTS["unemployment_rate"],
            6
        )

        # Round rates
        r["poverty_rate"] = round(r["poverty_rate"], 6)
        r["no_bachelor_rate"] = round(r["no_bachelor_rate"], 6)
        r["median_income_inv"] = round(r["median_income_inv"], 6)
        r["unemployment_rate"] = round(r["unemployment_rate"], 6)

    return records


def save_csv(records):
    """Save to CSV."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    fields = ["fips_code", "poverty_rate", "no_bachelor_rate", "median_income_inv",
              "unemployment_rate", "hardship_score"]

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    print(f"  Saved {len(records)} rows to {OUTPUT_FILE}")


def main():
    headers, rows = download_acs_data()
    records = compute_indicators(headers, rows)
    records = normalize_and_score(records)
    save_csv(records)

    # Summary stats
    scores = [r["hardship_score"] for r in records]
    print(f"\n  Summary:")
    print(f"    Counties: {len(records)}")
    print(f"    Hardship score range: {min(scores):.4f} — {max(scores):.4f}")
    print(f"    Mean hardship: {sum(scores)/len(scores):.4f}")
    print(f"    Top 5 hardest:")
    for r in sorted(records, key=lambda x: x["hardship_score"], reverse=True)[:5]:
        print(f"      FIPS {r['fips_code']}: {r['hardship_score']:.4f}")

    print("\n✅ Census data download complete!")


if __name__ == "__main__":
    main()
