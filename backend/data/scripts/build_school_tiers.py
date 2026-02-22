#!/usr/bin/env python3
"""
IPEDS School Tier Map Builder
Downloads IPEDS HD2023 institutional data and classifies schools into tiers (0-5).
Output: backend/data/school_tiers.json
"""

import csv
import io
import json
import os
import zipfile
import requests

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "school_tiers.json")

# IPEDS HD2023 data URL (institutional characteristics)
IPEDS_URL = "https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip"

# Carnegie Classification basic (C18BASIC) → tier mapping
# See: https://carnegieclassifications.acenet.edu/
# Values from IPEDS C18BASIC:
#   15 = Doctoral Universities: Very High Research Activity (R1)
#   16 = Doctoral Universities: High Research Activity (R2)
#   17 = Doctoral/Professional Universities
#   18 = Master's Colleges & Universities: Larger Programs
#   19 = Master's Colleges & Universities: Medium Programs
#   20 = Master's Colleges & Universities: Small Programs
#   21 = Baccalaureate Colleges: Arts & Sciences Focus
#   22 = Baccalaureate Colleges: Diverse Fields
#   23 = Baccalaureate/Associate's Colleges
#   1-14 = Associate's/Tribal/Special Focus
CARNEGIE_TO_TIER = {
    15: 4,  # R1 → Tier 4 (flagships promoted to 5 via overrides)
    16: 3,  # R2 → Tier 3
    17: 3,  # Doctoral/Professional → Tier 3
    18: 2,  # Master's Large → Tier 2
    19: 2,  # Master's Medium → Tier 2
    20: 2,  # Master's Small → Tier 2
    21: 2,  # Baccalaureate A&S → Tier 2
    22: 2,  # Baccalaureate Diverse → Tier 2
    23: 1,  # Baccalaureate/Associate's → Tier 1
}
# Associate's degree institutions (C18BASIC 1-14 for most)
ASSOCIATE_CODES = set(range(1, 15))

# Manual overrides for notable schools → Tier 5 (Ivy League / Top Private)
TIER_5_OVERRIDES = {
    "Harvard University", "Stanford University", "Massachusetts Institute of Technology",
    "Yale University", "Princeton University", "Columbia University",
    "University of Pennsylvania", "Brown University", "Dartmouth College",
    "Cornell University", "California Institute of Technology",
    "Duke University", "University of Chicago", "Northwestern University",
    "Johns Hopkins University", "Rice University", "Vanderbilt University",
    "Washington University in St Louis", "Emory University", "Notre Dame",
    "Georgetown University", "Carnegie Mellon University",
}

# Manual overrides for top public flagships → Tier 4
TIER_4_OVERRIDES = {
    "University of California-Berkeley", "University of California-Los Angeles",
    "University of Michigan-Ann Arbor", "University of Virginia-Main Campus",
    "University of North Carolina at Chapel Hill", "Georgia Institute of Technology-Main Campus",
    "University of Texas at Austin", "University of Wisconsin-Madison",
    "University of Illinois Urbana-Champaign", "University of Florida",
    "Ohio State University-Main Campus", "Pennsylvania State University-Main Campus",
    "University of Washington-Seattle Campus", "University of Southern California",
}


def download_ipeds():
    """Download and extract IPEDS HD2023 CSV."""
    print("Downloading IPEDS HD2023 data...")
    resp = requests.get(IPEDS_URL, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # Find the CSV file (usually hd2023.csv)
        csv_files = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not csv_files:
            raise ValueError(f"No CSV found in ZIP. Files: {zf.namelist()}")

        csv_name = csv_files[0]
        print(f"  Extracting {csv_name}...")
        raw = zf.read(csv_name)

        # Try different encodings
        for enc in ('utf-8', 'latin-1', 'cp1252'):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode('latin-1', errors='replace')

    return text


def classify_school(row, instnm):
    """Assign a tier (0-5) to a school based on Carnegie + overrides."""
    # Check manual overrides first
    if instnm in TIER_5_OVERRIDES:
        return 5
    if instnm in TIER_4_OVERRIDES:
        return 4

    # Use Carnegie Classification (C18BASIC)
    try:
        carnegie = int(row.get("C18BASIC", -1))
    except (ValueError, TypeError):
        carnegie = -1

    if carnegie in CARNEGIE_TO_TIER:
        return CARNEGIE_TO_TIER[carnegie]
    if carnegie in ASSOCIATE_CODES:
        return 1

    # Fallback: use institution category (INSTCAT)
    try:
        instcat = int(row.get("INSTCAT", -1))
    except (ValueError, TypeError):
        instcat = -1

    if instcat == 4:  # Degree-granting, associate's and certificates
        return 1
    if instcat in (2, 3):  # Degree-granting, primarily baccalaureate or above
        return 2

    # Check name-based heuristics
    name_lower = instnm.lower()
    if "community college" in name_lower or "community coll" in name_lower:
        return 1
    if "technical college" in name_lower:
        return 1

    return 2  # Default: Tier 2 (general university)


def build_school_tiers(csv_text):
    """Build school_name → tier mapping from IPEDS data."""
    reader = csv.DictReader(io.StringIO(csv_text))
    tiers = {}
    count_by_tier = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for row in reader:
        instnm = row.get("INSTNM", "").strip()
        if not instnm:
            continue

        # Only include US institutions
        country = row.get("COUNTRYCD", row.get("STABBR", ""))
        if country and len(country) > 2:
            continue

        tier = classify_school(row, instnm)
        tiers[instnm] = tier
        count_by_tier[tier] = count_by_tier.get(tier, 0) + 1

    print(f"  Classified {len(tiers)} institutions:")
    for t in sorted(count_by_tier.keys()):
        labels = {0: "High School", 1: "Community College", 2: "State Univ",
                  3: "Research Univ", 4: "Flagship/Top Public", 5: "Ivy League/Top Private"}
        print(f"    Tier {t} ({labels.get(t, '?')}): {count_by_tier[t]}")

    return tiers


def save_json(tiers):
    """Save tier map to JSON."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(tiers, f, indent=2)
    print(f"  Saved to {OUTPUT_FILE}")


def main():
    csv_text = download_ipeds()
    tiers = build_school_tiers(csv_text)
    save_json(tiers)

    # Quick sanity check
    checks = ["Harvard University", "Stanford University",
              "University of California-Berkeley", "University of California-Los Angeles"]
    print("\n  Sanity check:")
    for school in checks:
        print(f"    {school}: Tier {tiers.get(school, '?')}")

    print("\n✅ School tier map complete!")


if __name__ == "__main__":
    main()
