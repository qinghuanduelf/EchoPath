#!/usr/bin/env python3
"""
Build a RapidFire-compatible RAG eval dataset from EchoPath alumni data.

Outputs:
  rapidfire/datasets/echopath/corpus.jsonl
  rapidfire/datasets/echopath/queries.jsonl
  rapidfire/datasets/echopath/test-queries.jsonl
  rapidfire/datasets/echopath/qrels.tsv
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.data_loader import DataLoader


def _profile_to_document(profile: dict) -> str:
    position = profile.get("position", {}) or {}
    company = position.get("company", {}) or {}
    education = profile.get("education", []) or []
    jobs = profile.get("jobs", []) or []

    edu_summary = "; ".join(
        f"{(e or {}).get('degree', 'N/A')} in {(e or {}).get('field', 'N/A')} @ {(e or {}).get('school', 'Unknown')}"
        for e in education
        if isinstance(e, dict)
    )
    career_steps = " -> ".join(
        f"{(j or {}).get('title', 'Unknown')} @ {((j or {}).get('company', {}) or {}).get('name', 'Unknown')}"
        for j in jobs
        if isinstance(j, dict)
    )
    return (
        f"Origin FIPS: {profile.get('origin_fips', 'N/A')}. "
        f"Origin state: {profile.get('origin_state', 'N/A')}. "
        f"Career function: {profile.get('career_function', 'N/A')}. "
        f"Current role: {position.get('title', 'N/A')} ({position.get('level', 'N/A')}) at "
        f"{company.get('name', 'N/A')} in {company.get('industry', 'N/A')}. "
        f"Education: {edu_summary or 'N/A'}. "
        f"Career path: {career_steps or 'N/A'}."
    )


def _profile_to_query(profile: dict) -> str:
    position = profile.get("position", {}) or {}
    company = position.get("company", {}) or {}
    jobs = profile.get("jobs", []) or []
    first_job = jobs[0] if jobs else {}
    return (
        f"What is a realistic career path for a student from {profile.get('origin_state', 'this region')} "
        f"starting around {first_job.get('level', 'Staff')} in {((first_job.get('company', {}) or {}).get('industry', 'their field'))}, "
        f"aiming for {position.get('level', 'senior roles')} in {company.get('industry', 'the same industry')}?"
    )


def build_dataset(limit: int, seed: int, output_dir: Path):
    random.seed(seed)
    loader = DataLoader()
    profiles = loader.get_alumni()

    filtered = [
        p for p in profiles
        if p.get("jobs") and p.get("education") and p.get("position")
    ]
    random.shuffle(filtered)
    selected = filtered[:limit] if limit > 0 else filtered

    output_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = output_dir / "corpus.jsonl"
    queries_path = output_dir / "queries.jsonl"
    test_queries_path = output_dir / "test-queries.jsonl"
    qrels_path = output_dir / "qrels.tsv"

    corpus_rows = []
    query_rows = []
    qrels_rows = [("query-id", "corpus-id", "score")]

    for idx, profile in enumerate(selected):
        doc_id = idx
        query_id = idx
        corpus_rows.append({"_id": doc_id, "text": _profile_to_document(profile)})
        query_rows.append({"_id": query_id, "text": _profile_to_query(profile)})
        qrels_rows.append((str(query_id), str(doc_id), "1"))

    with corpus_path.open("w", encoding="utf-8") as f:
        for row in corpus_rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    with queries_path.open("w", encoding="utf-8") as f:
        for row in query_rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    # Hold out 20% for quick test file.
    split_idx = max(1, int(len(query_rows) * 0.2))
    with test_queries_path.open("w", encoding="utf-8") as f:
        for row in query_rows[:split_idx]:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    with qrels_path.open("w", encoding="utf-8") as f:
        for row in qrels_rows:
            f.write("\t".join(row) + "\n")

    print(f"Saved {len(corpus_rows)} corpus docs -> {corpus_path}")
    print(f"Saved {len(query_rows)} train queries -> {queries_path}")
    print(f"Saved {split_idx} test queries -> {test_queries_path}")
    print(f"Saved {len(qrels_rows) - 1} qrels -> {qrels_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500, help="Number of profiles to sample")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROJECT_ROOT / "rapidfire" / "datasets" / "echopath"),
        help="Output directory for RapidFire dataset files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    build_dataset(limit=args.limit, seed=args.seed, output_dir=output_dir)


if __name__ == "__main__":
    main()
