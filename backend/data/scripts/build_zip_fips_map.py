#!/usr/bin/env python3
"""
Zip Code → FIPS Code Mapping Builder
Extracts zip→fips mappings from existing JSONL profile data.
Supplements with Census ZCTA-County relationship file.
Output: backend/data/fips_zip_map.csv
"""

import csv
import io
import json
import os
import sys
from collections import Counter, defaultdict

import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
PROJECT_ROOT = os.path.join(DATA_DIR, "..", "..")
OUTPUT_FILE = os.path.join(DATA_DIR, "fips_zip_map.csv")

# Census ZCTA-County relationship file URL
ZCTA_COUNTY_URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt"

# JSONL files with profile data
JSONL_FILES = [
    os.path.join(PROJECT_ROOT, f"live_data_persons_history_2026-02-19_0{i}.jsonl")
    for i in range(3)
]


def extract_from_jsonl():
    """Extract zip→fips pairs from the JSONL profile data."""
    print("Extracting zip→fips mappings from JSONL profiles...")
    zip_fips_counter = defaultdict(Counter)
    zip_state = {}
    zip_county = {}
    total_extracted = 0

    for filepath in JSONL_FILES:
        if not os.path.exists(filepath):
            print(f"  Warning: {filepath} not found, skipping")
            continue

        filename = os.path.basename(filepath)
        print(f"  Processing {filename}...")
        count = 0

        with open(filepath, "r") as f:
            for line in f:
                try:
                    profile = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract from all jobs + current position
                locations = []
                if profile.get("position", {}).get("location_details"):
                    locations.append(profile["position"]["location_details"])
                for job in profile.get("jobs", []):
                    if job.get("location_details"):
                        locations.append(job["location_details"])
                # Also check top-level location_details
                if profile.get("location_details"):
                    locations.append(profile["location_details"])

                for loc in locations:
                    postal = loc.get("postal_code", "")
                    fips = loc.get("fips_code", "")
                    state = loc.get("region_abbreviation", "") or loc.get("region", "")
                    county = loc.get("county", "")

                    if postal and fips and len(postal) >= 5 and len(fips) == 5:
                        zip5 = postal[:5]
                        zip_fips_counter[zip5][fips] += 1
                        if state:
                            zip_state[zip5] = state
                        if county:
                            zip_county[zip5] = county
                        count += 1

        total_extracted += count
        print(f"    Extracted {count} zip→fips pairs")

    # For each zip, pick the most common fips
    result = {}
    for zip5, fips_counts in zip_fips_counter.items():
        most_common_fips = fips_counts.most_common(1)[0][0]
        result[zip5] = {
            "fips_code": most_common_fips,
            "state": zip_state.get(zip5, ""),
            "county": zip_county.get(zip5, ""),
        }

    print(f"  Total unique zip codes from JSONL: {len(result)}")
    return result


def download_census_zcta():
    """Download Census ZCTA-County relationship file as supplement."""
    print("\nDownloading Census ZCTA-County relationship file...")
    try:
        resp = requests.get(ZCTA_COUNTY_URL, timeout=60)
        resp.raise_for_status()

        # Parse the pipe-delimited file
        reader = csv.DictReader(io.StringIO(resp.text), delimiter="|")
        zcta_map = {}
        for row in reader:
            zcta = row.get("GEOID_ZCTA5_20", "").strip()
            county_fips = row.get("GEOID_COUNTY_20", "").strip()

            if zcta and county_fips and len(zcta) == 5 and len(county_fips) == 5:
                # Keep only the first (primary) mapping per ZCTA
                if zcta not in zcta_map:
                    zcta_map[zcta] = county_fips

        print(f"  Downloaded {len(zcta_map)} ZCTA→County mappings")
        return zcta_map
    except Exception as e:
        print(f"  Warning: Census ZCTA download failed: {e}")
        print("  Continuing with JSONL-only data")
        return {}


def merge_and_save(jsonl_map, zcta_map):
    """Merge JSONL and ZCTA data, save to CSV."""
    # Start with JSONL data (higher quality - real observations)
    merged = dict(jsonl_map)

    # Add ZCTA entries for zips not in JSONL
    added_from_zcta = 0
    for zcta, fips in zcta_map.items():
        if zcta not in merged:
            merged[zcta] = {
                "fips_code": fips,
                "state": "",
                "county": "",
            }
            added_from_zcta += 1

    print(f"\n  Total zip→fips mappings: {len(merged)}")
    print(f"    From JSONL: {len(jsonl_map)}")
    print(f"    Added from Census ZCTA: {added_from_zcta}")

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["zip_code", "fips_code", "state", "county"])
        for zip5 in sorted(merged.keys()):
            entry = merged[zip5]
            writer.writerow([zip5, entry["fips_code"], entry["state"], entry["county"]])

    print(f"  Saved to {OUTPUT_FILE}")


def main():
    jsonl_map = extract_from_jsonl()
    zcta_map = download_census_zcta()
    merge_and_save(jsonl_map, zcta_map)
    print("\n✅ Zip→FIPS mapping complete!")


if __name__ == "__main__":
    main()
