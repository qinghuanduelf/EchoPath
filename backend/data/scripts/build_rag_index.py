#!/usr/bin/env python3
"""
Build pgvector RAG index from alumni processed data.
"""

import asyncio
import argparse
import os
import sys


THIS_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.services.data_loader import DataLoader
from backend.services.llm_service import LLMService
from backend.services.vector_store import VectorStore


def _make_profile_chunks(profile: dict) -> list[dict]:
    profile_id = str(profile.get("id", ""))
    if not profile_id:
        return []

    position = profile.get("position", {}) or {}
    company = position.get("company", {}) or {}
    jobs = profile.get("jobs", []) or []
    education = profile.get("education", []) or []

    educations = [
        f"{e.get('degree', 'N/A')} in {e.get('field', 'N/A')} @ {e.get('school', 'Unknown')}"
        for e in education
        if isinstance(e, dict)
    ]
    job_steps = [
        f"{j.get('title', 'Unknown')} @ {(j.get('company', {}) or {}).get('name', 'Unknown')}"
        for j in jobs
        if isinstance(j, dict)
    ]
    industries = [
        (((j.get("company", {}) or {}).get("industry")) or "Unknown")
        for j in jobs
        if isinstance(j, dict)
    ]

    summary = (
        f"Profile {profile_id}. Origin FIPS: {profile.get('origin_fips', 'N/A')}. "
        f"Origin state: {profile.get('origin_state', 'N/A')}. "
        f"Career function: {profile.get('career_function', 'N/A')}. "
        f"Current role: {position.get('title', 'N/A')} ({position.get('level', 'N/A')}) at "
        f"{company.get('name', 'N/A')} in {company.get('industry', 'N/A')}. "
        f"Education: {'; '.join(educations) if educations else 'N/A'}. "
        f"Career path: {' -> '.join(job_steps) if job_steps else 'N/A'}."
    )

    return [
        {
            "chunk_id": f"{profile_id}:summary",
            "profile_id": profile_id,
            "chunk_text": summary,
            "metadata": {
                "origin_fips": profile.get("origin_fips", ""),
                "origin_state": profile.get("origin_state", ""),
                "career_function": profile.get("career_function", ""),
                "career_end_level": profile.get("career_end_level", ""),
            },
        },
        {
            "chunk_id": f"{profile_id}:industry_path",
            "profile_id": profile_id,
            "chunk_text": "Industry path: " + " -> ".join(industries) if industries else "Industry path: N/A",
            "metadata": {"chunk_type": "industry_path"},
        },
    ]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40, help="Number of profiles to index (0 means all)")
    parser.add_argument("--offset", type=int, default=0, help="Starting profile offset")
    parser.add_argument("--batch-size", type=int, default=20, help="Profiles per upsert batch")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Sleep between batches to avoid API quota spikes",
    )
    args = parser.parse_args()

    loader = DataLoader()
    profiles = loader.load_alumni()
    profiles = profiles[args.offset:]
    if args.limit > 0:
        profiles = profiles[:args.limit]

    vector_store = VectorStore()
    if not vector_store.enabled:
        raise RuntimeError("VectorStore disabled. Set PG_DSN and install psycopg.")

    llm_service = LLMService()

    print("Ensuring pgvector schema...")
    await vector_store.ensure_schema()

    total_profiles = len(profiles)
    total_upserted = 0
    print(f"Indexing {total_profiles} profiles in batches of {args.batch_size}...")

    for i in range(0, total_profiles, args.batch_size):
        batch_profiles = profiles[i:i + args.batch_size]
        chunks: list[dict] = []
        for profile in batch_profiles:
            chunks.extend(_make_profile_chunks(profile))
        if not chunks:
            continue
        print(f"Batch {i // args.batch_size + 1}: upserting {len(chunks)} chunks...")
        upserted = await vector_store.upsert_chunks(chunks, llm_service.embed_text)
        total_upserted += upserted
        if args.sleep_seconds > 0:
            await asyncio.sleep(args.sleep_seconds)

    print(f"Done. Upserted {total_upserted} chunks total.")


if __name__ == "__main__":
    asyncio.run(main())
