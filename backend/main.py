"""
EchoPath Backend — FastAPI REST API.

Endpoints:
  POST /api/v1/student/analyze      → Core matching + path pipeline
  GET  /api/v1/student/{id}/paths   → Cached career paths
  GET  /api/v1/student/{id}/matches → Cached match list
  GET  /api/v1/match/{id}           → Single alumni snapshot
  POST /api/v1/email/generate       → Generate icebreaker email
  POST /api/v1/email/regenerate     → Regenerate email
  GET  /api/v1/hardship/{fips}      → Hardship score lookup
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models.student import StudentInput, StudentData
from backend.models.mentor import MatchResult, MentorSnapshot
from backend.models.path import CareerPath
from backend.models.email import EmailRequest, EmailResponse

from backend.engines.hardship_scorer import HardshipScorer
from backend.engines.match_engine import MatchEngine
from backend.engines.path_builder import PathBuilder
from backend.engines.path_planner import PathPlanner
from backend.engines.email_generator import EmailGenerator
from backend.config import RAG_TOP_K
from backend.services.data_loader import DataLoader
from backend.services.llm_service import LLMService
from backend.services.vector_store import VectorStore


# ──────────── In-memory session store ────────────
# Maps session_id → {"student": StudentData, "matches": [...], "paths": [...]}
_sessions: dict[str, dict] = {}

# ──────────── Singleton engine instances ────────────
_hardship_scorer: HardshipScorer | None = None
_match_engine: MatchEngine | None = None
_path_builder: PathBuilder | None = None
_email_generator: EmailGenerator | None = None
_data_loader: DataLoader | None = None
_llm_service: LLMService | None = None
_vector_store: VectorStore | None = None
_path_planner: PathPlanner | None = None
MIN_MATCH_SCORE = 0.50
MAX_MATCHES = 6


def _build_rag_query(student: dict) -> str:
    """Compact student intent/query used for semantic retrieval."""
    return (
        f"Student from FIPS {student.get('fips_code', 'N/A')} in {student.get('state', 'N/A')}. "
        f"Education {student.get('current_education', 'N/A')}. "
        f"Target function {student.get('target_function', 'N/A')} at level {student.get('target_level', 'N/A')}. "
        f"Hardship score {student.get('hardship_score', 0.5):.2f}."
    )


def _merge_matches_with_rag(base_matches: list[MatchResult], rag_hits: list[dict]) -> list[MatchResult]:
    """Merge semantic retrieval signal into deterministic match results."""
    if not rag_hits:
        return base_matches

    rag_best: dict[str, float] = {}
    for hit in rag_hits:
        profile_id = str(hit.get("profile_id", ""))
        if not profile_id:
            continue
        sim = float(hit.get("similarity", 0.0) or 0.0)
        rag_best[profile_id] = max(rag_best.get(profile_id, 0.0), sim)

    if not rag_best:
        return base_matches

    merged: list[MatchResult] = []
    for m in base_matches:
        bonus = max(0.0, min(0.08, rag_best.get(m.profile_id, 0.0) * 0.08))
        merged.append(
            m.model_copy(
                update={
                    "total_score": round(min(1.0, m.total_score + bonus), 4),
                    "dimension_scores": {
                        **m.dimension_scores,
                        "rag_score": round(rag_best.get(m.profile_id, 0.0), 4),
                    },
                }
            )
        )

    # Keep deterministic ranking stable while still allowing RAG boost.
    merged.sort(key=lambda r: r.total_score, reverse=True)
    return merged


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize engines on startup, cleanup on shutdown."""
    global _hardship_scorer, _match_engine, _path_builder
    global _email_generator, _data_loader, _llm_service, _vector_store, _path_planner

    print("🚀 Initializing EchoPath engines...")
    _hardship_scorer = HardshipScorer()
    _match_engine = MatchEngine(_hardship_scorer)
    _path_builder = PathBuilder()
    _llm_service = LLMService()
    _vector_store = VectorStore()
    _email_generator = EmailGenerator(llm_service=_llm_service)
    _path_planner = PathPlanner(path_builder=_path_builder, llm_service=_llm_service)
    _data_loader = DataLoader()
    _data_loader.load_alumni()
    if _vector_store.enabled:
        try:
            await _vector_store.ensure_schema()
            print("✅ pgvector schema ready.")
        except Exception as e:
            print(f"⚠️ pgvector setup failed, continuing without retrieval: {e}")
    print("✅ All engines ready.")

    yield  # App is running

    # Cleanup
    _sessions.clear()
    print("🛑 EchoPath shutdown complete.")


app = FastAPI(
    title="EchoPath API",
    description="Career navigation & mentorship platform for underserved students.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════


@app.post("/api/v1/student/analyze")
async def analyze_student(student: StudentInput):
    """
    Accept student input, resolve FIPS, compute hardship,
    run matching + path building, return session + results.
    """
    # 1. Resolve location to FIPS (prefer explicit fips_code, else zip_code)
    if not student.fips_code and not student.zip_code:
        raise HTTPException(status_code=400, detail="Either zip_code or fips_code is required.")

    if student.fips_code:
        fips = _hardship_scorer.resolve_fips(student.fips_code)
    else:
        resolved = _hardship_scorer.resolve_zip_to_fips(student.zip_code or "")
        # For valid US ZIPs that are not in the local crosswalk yet,
        # keep request valid and fall back to neutral hardship/state.
        fips = resolved or "00000"

    state = _hardship_scorer.get_state_from_fips(fips)
    hardship = _hardship_scorer.get_score(fips)

    # 2. Build enriched student data
    if (
        student.expected_salary_min is not None
        and student.expected_salary_max is not None
        and student.expected_salary_min > student.expected_salary_max
    ):
        raise HTTPException(
            status_code=400,
            detail="expected_salary_min must be less than or equal to expected_salary_max.",
        )

    student_data = StudentData(
        fips_code=fips,
        state=state,
        hardship_score=hardship,
        current_education=student.current_education,
        target_function=student.target_function,
        target_level=student.target_level,
        expected_salary_min=student.expected_salary_min,
        expected_salary_max=student.expected_salary_max,
        dream_description=student.dream_description,
        school_name=student.school_name,
        location=f"FIPS {fips}",
    )

    # 3. Run matching engine
    alumni_list = _data_loader.get_alumni()
    matches = _match_engine.find_matches(
        student_data.model_dump(), alumni_list, top_k=20
    )

    # 3.5 RAG retrieval (pgvector) and score fusion
    rag_hits: list[dict] = []
    if _vector_store and _vector_store.enabled and _llm_service:
        try:
            rag_hits = await _vector_store.search_profiles(
                query_text=_build_rag_query(student_data.model_dump()),
                embedding_fn=_llm_service.embed_text,
                top_k=RAG_TOP_K,
            )
            matches = _merge_matches_with_rag(matches, rag_hits)
        except Exception as e:
            print(f"RAG retrieval failed, using base matches only: {e}")

    # 4. Enforce quality bar and list size for mentor output.
    matches = [m for m in matches if m.total_score >= MIN_MATCH_SCORE]
    matches = matches[:MAX_MATCHES]

    # 5. Build career paths from top matched profiles
    matched_profiles = []
    for m in matches:
        profile = _data_loader.get_profile_by_id(m.profile_id)
        if profile:
            matched_profiles.append(profile)

    paths, path_planning = await _path_planner.plan_paths(
        student=student_data.model_dump(),
        matched_profiles=matched_profiles,
        rag_hits=rag_hits,
        top_n=3,
    )

    # 6. Store session for later retrieval
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "student": student_data.model_dump(),
        "matches": [m.model_dump() for m in matches],
        "paths": [p.model_dump() for p in paths],
        "rag_hits": rag_hits,
        "path_planning": path_planning,
    }

    return {
        "session_id": session_id,
        "hardship_score": hardship,
        "fips_code": fips,
        "matches": [m.model_dump() for m in matches],
        "paths": [p.model_dump() for p in paths[:3]],      # Top 3 paths
        "total_matches": len(matches),
        "rag_hits_count": len(rag_hits),
        "path_source": path_planning.get("source", "fallback"),
    }


@app.get("/api/v1/student/{session_id}/paths")
async def get_student_paths(session_id: str):
    """Retrieve cached career paths for a previous analysis session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Run /student/analyze first.")
    return {"paths": session["paths"]}


@app.get("/api/v1/student/{session_id}/matches")
async def get_student_matches(session_id: str):
    """Retrieve cached matches for a previous analysis session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Run /student/analyze first.")
    return {"matches": session["matches"]}


@app.get("/api/v1/match/{profile_id}")
async def get_match_detail(profile_id: str):
    """Look up a single alumni profile and return an anonymized snapshot."""
    profile = _data_loader.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found.")

    # Build an anonymized snapshot
    position = profile.get("position", {})
    company = position.get("company", {})
    education = profile.get("education", [])

    snapshot = MentorSnapshot(
        current_title=position.get("title"),
        current_level=position.get("level"),
        industry=company.get("industry"),
        company_size=company.get("employee_count"),
        education_summary=[
            {"degree": e.get("degree"), "field": e.get("field")}
            for e in education
        ],
    )

    return {
        "profile_id": profile_id,
        "snapshot": snapshot.model_dump(),
    }


@app.post("/api/v1/email/generate")
async def generate_email(request: EmailRequest):
    """Generate a personalized icebreaker email for a student-mentor pair."""
    # Look up mentor profile
    mentor = _data_loader.get_profile_by_id(request.mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail=f"Mentor '{request.mentor_id}' not found.")

    # Look up student data from session
    session = _sessions.get(request.student_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Run /student/analyze first to get a student_id (session_id).",
        )

    student = session["student"]
    # Merge dream_description from request if provided
    if request.dream_description:
        student = {**student, "dream_description": request.dream_description}

    email_text = await _email_generator.generate_email(
        student, mentor, request.match_score
    )
    email_meta = _email_generator.get_last_generation_metadata()

    return EmailResponse(
        email=email_text,
        mentor_label=f"Mentor #{request.mentor_id[:8]}",
        match_score=request.match_score,
        provider=email_meta.get("provider", "template"),
        model=email_meta.get("model", ""),
        used_fallback=bool(email_meta.get("used_fallback", False)),
    )


@app.post("/api/v1/email/regenerate")
async def regenerate_email(request: EmailRequest):
    """Regenerate the icebreaker email (same logic, new LLM call)."""
    return await generate_email(request)


@app.get("/api/v1/hardship/{fips}")
async def get_hardship(fips: str):
    """Look up hardship score for a FIPS code."""
    score = _hardship_scorer.get_score(fips)
    return {
        "fips_code": fips,
        "hardship_score": score,
    }


# ──────────── Health check ────────────

@app.get("/health")
async def health():
    return {"status": "ok", "sessions": len(_sessions)}
