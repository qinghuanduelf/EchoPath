/**
 * EchoPath API Client
 * Typed fetch wrappers for all 7 backend REST endpoints.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ────────── Types ────────── */

export interface StudentInput {
    zip_code?: string;
    fips_code?: string;
    current_education: string;
    target_function: string;
    target_level: string;
    expected_salary_min?: number;
    expected_salary_max?: number;
    dream_description?: string;
    school_name?: string;
}

export interface EducationSummary {
    degree: string | null;
    field: string | null;
}

export interface MentorSnapshot {
    current_title: string | null;
    current_level: string | null;
    industry: string | null;
    company_size: number | null;
    initial_salary?: number | null;
    final_salary?: number | null;
    education_summary: EducationSummary[];
}

export interface MatchResult {
    profile_id: string;
    total_score: number;
    dimension_scores: Record<string, number>;
    profile_snapshot: MentorSnapshot;
}

export interface CareerNode {
    stage: string;
    label: string;
    typical_duration: number;
    count: number;
}

export interface CareerPath {
    nodes: CareerNode[];
    total_people: number;
    avg_years: number;
    source?: string;
    confidence?: number;
    evidence_count?: number;
}

export interface AnalyzeResponse {
    session_id: string;
    hardship_score: number;
    fips_code: string;
    matches: MatchResult[];
    paths: CareerPath[];
    total_matches: number;
    rag_hits_count?: number;
    path_source?: string;
}

export interface EmailRequest {
    student_id: string;
    mentor_id: string;
    match_score: number;
    dream_description?: string;
}

export interface EmailResponse {
    email: string;
    mentor_label: string;
    match_score: number;
    provider?: string;
    model?: string;
    used_fallback?: boolean;
}

/* ────────── API Functions ────────── */

async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API error: ${res.status}`);
    }
    return res.json();
}

/** POST /api/v1/student/analyze */
export async function analyzeStudent(input: StudentInput): Promise<AnalyzeResponse> {
    return request<AnalyzeResponse>("/api/v1/student/analyze", {
        method: "POST",
        body: JSON.stringify(input),
    });
}

/** GET /api/v1/student/{sessionId}/paths */
export async function getStudentPaths(sessionId: string): Promise<{ paths: CareerPath[] }> {
    return request(`/api/v1/student/${sessionId}/paths`);
}

/** GET /api/v1/student/{sessionId}/matches */
export async function getStudentMatches(sessionId: string): Promise<{ matches: MatchResult[] }> {
    return request(`/api/v1/student/${sessionId}/matches`);
}

/** GET /api/v1/match/{profileId} */
export async function getMatchDetail(profileId: string): Promise<{ profile_id: string; snapshot: MentorSnapshot }> {
    return request(`/api/v1/match/${profileId}`);
}

/** POST /api/v1/email/generate */
export async function generateEmail(req: EmailRequest): Promise<EmailResponse> {
    return request<EmailResponse>("/api/v1/email/generate", {
        method: "POST",
        body: JSON.stringify(req),
    });
}

/** POST /api/v1/email/regenerate */
export async function regenerateEmail(req: EmailRequest): Promise<EmailResponse> {
    return request<EmailResponse>("/api/v1/email/regenerate", {
        method: "POST",
        body: JSON.stringify(req),
    });
}

/** GET /api/v1/hardship/{fips} */
export async function getHardship(fips: string): Promise<{ fips_code: string; hardship_score: number }> {
    return request(`/api/v1/hardship/${fips}`);
}
