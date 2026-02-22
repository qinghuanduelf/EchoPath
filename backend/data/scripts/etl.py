#!/usr/bin/env python3
"""
ETL Pipeline — Clean and process JSONL career profiles.
Applies data quality filters and extracts key features for the matching engine.
Output: backend/data/processed/alumni_processed.json
"""

import json
import os
import sys
from datetime import datetime
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "..")
PROJECT_ROOT = os.path.join(DATA_DIR, "..", "..")
OUTPUT_DIR = os.path.join(DATA_DIR, "processed")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "alumni_processed.json")

JSONL_FILES = [
    os.path.join(PROJECT_ROOT, f"live_data_persons_history_2026-02-19_0{i}.jsonl")
    for i in range(3)
]


def parse_date(date_str):
    """Flexible date parser supporting ISO, year-month, and year-only formats."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str[:len(fmt.replace('%', '0').replace('T', '0').replace('Z', '0'))], fmt)
        except (ValueError, TypeError):
            continue
    # Last resort: just try the first 10 chars
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


# ──────────── Data Quality Filter ────────────

def is_valid_for_model(profile):
    """
    Only profiles passing ALL quality checks are included.
    Returns (is_valid, reason_if_rejected)
    """
    # 1. Must have at least 1 valid job (non-null title)
    jobs = profile.get("jobs", [])
    valid_jobs = [j for j in jobs if j.get("title")]
    if len(valid_jobs) < 1:
        return False, "no_valid_jobs"

    # 2. Education info cannot be empty
    education = profile.get("education", [])
    if len(education) < 1:
        return False, "no_education"

    # 3. Currently employed
    if profile.get("employment_status") != "employed":
        return False, "not_employed"

    # 4. At least one job has a non-null level
    if not any(j.get("level") for j in jobs):
        return False, "no_job_level"

    # 5. At least one job has a FIPS code
    has_fips = False
    for j in jobs:
        loc = j.get("location_details") or {}
        if loc.get("fips_code"):
            has_fips = True
            break
    if not has_fips:
        return False, "no_fips_code"

    return True, None


# ──────────── Feature Extraction ────────────

def get_earliest_job(jobs):
    """Get the earliest job by start date."""
    valid = [j for j in jobs if j.get("title")]
    if not valid:
        return None

    def sort_key(j):
        d = parse_date(j.get("started_at", ""))
        return d if d else datetime(9999, 1, 1)

    return sorted(valid, key=sort_key)[0]


def get_latest_job(jobs):
    """Get the latest/current job."""
    valid = [j for j in jobs if j.get("title")]
    if not valid:
        return None

    def sort_key(j):
        d = parse_date(j.get("started_at", ""))
        return d if d else datetime(1900, 1, 1)

    return sorted(valid, key=sort_key)[-1]


def get_earliest_education(education):
    """Get the earliest education record."""
    if not education:
        return None

    def sort_key(e):
        d = parse_date(e.get("started_at", ""))
        return d if d else datetime(9999, 1, 1)

    return sorted(education, key=sort_key)[0]


def extract_features(profile):
    """Extract structured features from a raw profile for the matching engine."""
    jobs = profile.get("jobs", [])
    education = profile.get("education", [])
    position = profile.get("position", {})
    valid_jobs = sorted(
        [j for j in jobs if j.get("title")],
        key=lambda j: parse_date(j.get("started_at", "")) or datetime(9999, 1, 1)
    )

    earliest_job = valid_jobs[0] if valid_jobs else {}
    latest_job = valid_jobs[-1] if valid_jobs else {}
    earliest_edu = get_earliest_education(education)

    # Origin info (from earliest job)
    origin_loc = earliest_job.get("location_details") or {}
    origin_fips = origin_loc.get("fips_code", "")
    origin_state = origin_loc.get("region", "") or origin_loc.get("region_abbreviation", "")
    origin_msa = origin_loc.get("msa", "")

    # If earliest job has no FIPS, search other jobs
    if not origin_fips:
        for j in valid_jobs:
            loc = j.get("location_details") or {}
            if loc.get("fips_code"):
                origin_fips = loc["fips_code"]
                origin_state = loc.get("region", "") or origin_loc.get("region_abbreviation", "")
                origin_msa = loc.get("msa", "")
                break

    # Education features
    edu_school = earliest_edu.get("school", "") if earliest_edu else ""
    edu_degree = earliest_edu.get("degree", "") if earliest_edu else ""
    edu_field = earliest_edu.get("field", "") if earliest_edu else ""

    # All education summary
    edu_summary = [
        {
            "school": e.get("school", ""),
            "degree": e.get("degree", ""),
            "field": e.get("field", ""),
        }
        for e in education
    ]

    # Career trajectory
    career_start_level = earliest_job.get("level", "")
    career_end_level = position.get("level", "") or latest_job.get("level", "")
    career_function = position.get("function", "") or latest_job.get("function", "")

    # Tenure & company stats
    total_tenure_months = sum(j.get("duration", 0) or 0 for j in valid_jobs)
    companies = set()
    for j in valid_jobs:
        co = j.get("company", {})
        co_id = co.get("id") or co.get("name", "")
        if co_id:
            companies.add(co_id)
    company_count = len(companies)

    # Industry path (chronological)
    industry_path = []
    for j in valid_jobs:
        ind = j.get("company", {}).get("industry", "")
        if ind and (not industry_path or industry_path[-1] != ind):
            industry_path.append(ind)

    # Current position info
    current_company = position.get("company", {})
    current_company_size = current_company.get("employee_count", 0)
    current_company_type = current_company.get("type", "")
    current_company_industry = current_company.get("industry", "")

    # Level progression (numeric)
    level_order = {
        "Intern": 0, "Staff": 1, "Senior Staff": 2,
        "Manager": 3, "Senior Manager": 4, "Director": 5,
        "VP": 6, "C-Suite": 7, "CXO": 7, "Owner": 7, "Partner": 6,
    }
    start_num = level_order.get(career_start_level, -1)
    end_num = level_order.get(career_end_level, -1)
    level_progression = (end_num - start_num) if start_num >= 0 and end_num >= 0 else 0

    # Build the full jobs list for path builder (chronological)
    jobs_clean = []
    for j in valid_jobs:
        loc = j.get("location_details") or {}
        co = j.get("company") or {}
        jobs_clean.append({
            "title": j.get("title"),
            "level": j.get("level"),
            "function": j.get("function"),
            "started_at": j.get("started_at"),
            "ended_at": j.get("ended_at"),
            "duration": j.get("duration", 0),
            "company_tenure": j.get("company_tenure", 0),
            "is_first_at_company": j.get("is_first_at_company", False),
            "is_last_at_company": j.get("is_last_at_company", False),
            "company": {
                "name": co.get("name", ""),
                "industry": co.get("industry", ""),
                "employee_count": co.get("employee_count", 0),
                "type": co.get("type", ""),
            },
            "location_details": {
                "fips_code": loc.get("fips_code", ""),
                "region": loc.get("region", ""),
                "region_abbreviation": loc.get("region_abbreviation", ""),
                "locality": loc.get("locality", ""),
                "county": loc.get("county", ""),
                "msa": loc.get("msa", ""),
            },
        })

    return {
        "id": profile.get("id", ""),
        "employment_status": profile.get("employment_status", ""),
        "connections": profile.get("connections", 0),

        # Origin features
        "origin_fips": origin_fips,
        "origin_state": origin_state,
        "origin_msa": origin_msa,

        # Education features
        "education_school": edu_school,
        "education_degree": edu_degree,
        "education_field": edu_field,
        "education": edu_summary,

        # Career features
        "career_start_level": career_start_level,
        "career_end_level": career_end_level,
        "career_function": career_function,
        "total_tenure_months": total_tenure_months,
        "company_count": company_count,
        "industry_path": industry_path,
        "level_progression": level_progression,

        # Current position
        "position": {
            "title": position.get("title", ""),
            "level": position.get("level", ""),
            "function": position.get("function", ""),
            "company": {
                "name": current_company.get("name", ""),
                "industry": current_company_industry,
                "employee_count": current_company_size,
                "type": current_company_type,
            },
        },

        # Full job history (cleaned, for PathBuilder)
        "jobs": jobs_clean,
    }


# ──────────── Main Pipeline ────────────

def main():
    print("=" * 60)
    print("EchoPath ETL Pipeline")
    print("=" * 60)

    all_profiles = []
    valid_profiles = []
    rejection_reasons = Counter()
    total_read = 0

    for filepath in JSONL_FILES:
        if not os.path.exists(filepath):
            print(f"\n⚠ File not found: {filepath}")
            continue

        filename = os.path.basename(filepath)
        print(f"\nProcessing {filename}...")
        file_count = 0
        file_valid = 0

        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    profile = json.loads(line)
                except json.JSONDecodeError:
                    rejection_reasons["json_parse_error"] += 1
                    continue

                file_count += 1
                is_valid, reason = is_valid_for_model(profile)

                if is_valid:
                    features = extract_features(profile)
                    valid_profiles.append(features)
                    file_valid += 1
                else:
                    rejection_reasons[reason] += 1

        total_read += file_count
        print(f"  Read: {file_count} | Valid: {file_valid} | Rejected: {file_count - file_valid}")

    # Save output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(valid_profiles, f, indent=None, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("ETL Summary")
    print("=" * 60)
    print(f"Total profiles read:    {total_read}")
    print(f"Valid profiles:         {len(valid_profiles)} ({100*len(valid_profiles)/total_read:.1f}%)")
    print(f"Rejected profiles:      {total_read - len(valid_profiles)}")
    print(f"\nRejection breakdown:")
    for reason, count in rejection_reasons.most_common():
        print(f"  {reason}: {count}")

    # Feature coverage stats
    print(f"\nFeature coverage (of valid profiles):")
    coverage = {
        "origin_fips": sum(1 for p in valid_profiles if p["origin_fips"]),
        "education_school": sum(1 for p in valid_profiles if p["education_school"]),
        "career_function": sum(1 for p in valid_profiles if p["career_function"]),
        "career_end_level": sum(1 for p in valid_profiles if p["career_end_level"]),
        "industry_path": sum(1 for p in valid_profiles if p["industry_path"]),
    }
    for feat, count in coverage.items():
        print(f"  {feat}: {count}/{len(valid_profiles)} ({100*count/len(valid_profiles):.1f}%)")

    # Sample output
    if valid_profiles:
        print(f"\nSample profile keys: {list(valid_profiles[0].keys())}")
        print(f"Sample profile ID: {valid_profiles[0]['id']}")
        print(f"Sample origin FIPS: {valid_profiles[0]['origin_fips']}")
        print(f"Sample function: {valid_profiles[0]['career_function']}")
        print(f"Sample edu: {valid_profiles[0]['education_school']}")

    output_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\nOutput file: {OUTPUT_FILE}")
    print(f"Output size: {output_size_mb:.1f} MB")
    print("\n✅ ETL pipeline complete!")


if __name__ == "__main__":
    main()
