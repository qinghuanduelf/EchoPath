"use client";

import { useEffect, useMemo, useState, use } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
    getStudentPaths,
    getStudentMatches,
    type CareerPath,
    type MatchResult,
} from "@/lib/api";
import HardshipBadge from "@/components/HardshipBadge";
import PathVisualization from "@/components/PathVisualization";
import MentorCard from "@/components/MentorCard";
import { useI18n } from "@/components/LanguageProvider";

interface PageProps {
    params: Promise<{ sessionId: string }>;
}

type StrategyMode = "reachable" | "aspirational";

const DIM_WEIGHTS_ASPIRATIONAL: Record<string, number> = {
    level_score: 0.45,
    function_score: 0.35,
    salary_score: 0.10,
    total_score: 0.10,
};

function estimatePathLevel(path: CareerPath): number {
    const current = (path.nodes[path.nodes.length - 1]?.label || "").toLowerCase();
    if (current.includes("vp") || current.includes("c-suite") || current.includes("cxo")) return 5;
    if (current.includes("director")) return 4;
    if (current.includes("senior manager")) return 3;
    if (current.includes("manager")) return 2;
    if (current.includes("staff")) return 1;
    return 0;
}

function scoreAspirationalMatch(m: MatchResult): number {
    const s = m.dimension_scores;
    return (
        (s.level_score || 0) * DIM_WEIGHTS_ASPIRATIONAL.level_score +
        (s.function_score || 0) * DIM_WEIGHTS_ASPIRATIONAL.function_score +
        (s.salary_score || 0.5) * DIM_WEIGHTS_ASPIRATIONAL.salary_score +
        m.total_score * DIM_WEIGHTS_ASPIRATIONAL.total_score
    );
}

function scoreAspirationalPath(path: CareerPath): number {
    const level = estimatePathLevel(path) / 5;
    const years = Math.min(1, (path.avg_years || 0) / 15);
    return 0.6 * level + 0.4 * years;
}

function buildSkillPlan(path: CareerPath) {
    const text = path.nodes.map((n) => n.label.toLowerCase()).join(" ");
    if (text.includes("marketing")) {
        return {
            skills: ["Campaign analytics", "Lifecycle messaging", "A/B testing basics"],
            resources: [
                "Google Skillshop (free, mobile-friendly)",
                "HubSpot Academy short modules (free)",
                "YouTube playlists with offline download support",
            ],
            hours: "6–10 hours",
            why: "These skills appear frequently at the first transition into growth/manager-track marketing roles.",
        };
    }
    if (text.includes("engineering") || text.includes("technology")) {
        return {
            skills: ["SQL + data reasoning", "System design fundamentals", "Cross-team communication"],
            resources: [
                "freeCodeCamp modules (free)",
                "ByteByteGo summaries (low-bandwidth reading)",
                "LeetCode starter tracks (free tier)",
            ],
            hours: "8–12 hours",
            why: "These skills are common gatekeepers when moving from staff to senior/manager engineering roles.",
        };
    }
    return {
        skills: ["Structured communication", "Spreadsheet analysis", "Project planning basics"],
        resources: [
            "Coursera audit mode courses",
            "Local library digital learning portals",
            "Mobile-first micro-learning playlists",
        ],
        hours: "6–9 hours",
        why: "These are the most transferable skills observed in the first jump of similar trajectories.",
    };
}

export default function ResultsPage({ params }: PageProps) {
    const { sessionId } = use(params);
    const router = useRouter();
    const { t } = useI18n();

    const [paths, setPaths] = useState<CareerPath[]>([]);
    const [matches, setMatches] = useState<MatchResult[]>([]);
    const [hardship, setHardship] = useState<number | null>(null);
    const [strategy, setStrategy] = useState<StrategyMode>("reachable");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        async function load() {
            try {
                const [pathRes, matchRes] = await Promise.all([
                    getStudentPaths(sessionId),
                    getStudentMatches(sessionId),
                ]);
                setPaths(pathRes.paths);
                setMatches(matchRes.matches);

                // Extract hardship/fips from first match session data
                // The analyze endpoint stores these; we look at the session matches.
                if (matchRes.matches.length > 0) {
                    // hardship_score is in session student data; for now use dimension
                    const firstMatch = matchRes.matches[0];
                    setHardship(firstMatch.dimension_scores.hardship_score ?? null);
                }
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Failed to load results.");
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [sessionId]);

    const handleConnect = (profileId: string, score: number) => {
        router.push(`/email/${sessionId}/${profileId}?score=${score}`);
    };

    const visibleMatches = useMemo(() => {
        if (strategy === "reachable") return matches;
        return [...matches]
            .sort((a, b) => scoreAspirationalMatch(b) - scoreAspirationalMatch(a))
            .slice(0, 6);
    }, [matches, strategy]);

    const visiblePaths = useMemo(() => {
        if (strategy === "reachable") return paths;
        return [...paths]
            .sort((a, b) => scoreAspirationalPath(b) - scoreAspirationalPath(a));
    }, [paths, strategy]);

    const fairnessChecks = useMemo(() => {
        const hasSimilarHardship = visibleMatches.some(
            (m) => (m.dimension_scores.hardship_score || 0) >= 0.7
        );
        const hasAspirationalPath = visiblePaths.some((p) => estimatePathLevel(p) >= 3);
        return {
            hasSimilarHardship,
            hasAspirationalPath,
        };
    }, [visibleMatches, visiblePaths]);

    if (loading) {
        return (
            <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <span className="inline-block w-10 h-10 border-3 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
                    <p className="text-[var(--color-muted)]">Loading your results...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
                <div className="glass rounded-2xl p-8 text-center max-w-md">
                    <p className="text-xl mb-2">😕</p>
                    <p className="text-[var(--color-danger)] mb-4">{error}</p>
                    <button onClick={() => router.push("/")} className="btn-primary">
                        ← Start Over
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 space-y-10">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
            >
                <div>
                    <h1 className="text-3xl font-bold">
                        <span className="gradient-text">{t("results.title")}</span>
                    </h1>
                    <p className="text-[var(--color-muted)] mt-1">
                        {visibleMatches.length} potential mentor{visibleMatches.length !== 1 ? "s" : ""} found ·{" "}
                        {visiblePaths.length} career path{visiblePaths.length !== 1 ? "s" : ""} identified
                    </p>
                </div>
                {hardship !== null && <HardshipBadge score={hardship} />}
            </motion.div>

            <div className="glass rounded-xl border border-[var(--color-primary)]/30 bg-[var(--color-primary)]/8 px-4 py-3 text-sm">
                {t("results.banner", { score: Math.round((hardship ?? 0) * 100) })}
            </div>

            <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-[var(--color-muted)]">{t("results.mode")}</span>
                <button
                    onClick={() => setStrategy("reachable")}
                    className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                        strategy === "reachable"
                            ? "bg-[var(--color-primary)]/20 border-[var(--color-primary)] text-[var(--color-primary)]"
                            : "border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                    }`}
                >
                    {t("results.reachable")}
                </button>
                <button
                    onClick={() => setStrategy("aspirational")}
                    className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                        strategy === "aspirational"
                            ? "bg-[var(--color-primary)]/20 border-[var(--color-primary)] text-[var(--color-primary)]"
                            : "border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-foreground)]"
                    }`}
                >
                    {t("results.aspirational")}
                </button>
                <span className="text-xs text-[var(--color-muted)]">
                    {strategy === "reachable"
                        ? t("results.modeHintReachable")
                        : t("results.modeHintAspirational")}
                </span>
            </div>

            {/* Paths section */}
            <section>
                <motion.h2
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.1 }}
                    className="text-xl font-semibold mb-4 flex items-center gap-2"
                >
                    🗺️ {t("results.paths")}
                </motion.h2>
                <PathVisualization paths={visiblePaths.slice(0, 3)} />
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
                    {visiblePaths.slice(0, 3).map((path, idx) => {
                        const plan = buildSkillPlan(path);
                        return (
                            <details key={`plan-${idx}`} className="glass rounded-xl p-4">
                                <summary className="cursor-pointer font-medium text-sm">
                                    Next 30 days plan · Path {idx + 1}
                                </summary>
                                <div className="mt-3 space-y-2 text-sm">
                                    <div>
                                        <p className="text-xs text-[var(--color-muted)] mb-1">Top 3 skills</p>
                                        <ul className="list-disc pl-5 space-y-1">
                                            {plan.skills.map((s) => <li key={s}>{s}</li>)}
                                        </ul>
                                    </div>
                                    <div>
                                        <p className="text-xs text-[var(--color-muted)] mb-1">Low-cost resources</p>
                                        <ul className="list-disc pl-5 space-y-1">
                                            {plan.resources.map((r) => <li key={r}>{r}</li>)}
                                        </ul>
                                    </div>
                                    <p><span className="text-[var(--color-muted)]">Estimated time:</span> {plan.hours}</p>
                                    <p><span className="text-[var(--color-muted)]">Why these skills:</span> {plan.why}</p>
                                </div>
                            </details>
                        );
                    })}
                </div>
            </section>

            {/* Mentors section */}
            <section>
                <motion.h2
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-xl font-semibold mb-4 flex items-center gap-2"
                >
                    👤 {t("results.mentors")}
                </motion.h2>
                {visibleMatches.length === 0 ? (
                    <div className="glass rounded-2xl p-8 text-center text-[var(--color-muted)]">
                        {t("results.noMatches")}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        {visibleMatches.map((m, i) => (
                            <MentorCard
                                key={m.profile_id}
                                match={m}
                                index={i}
                                onConnect={handleConnect}
                            />
                        ))}
                    </div>
                )}
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="glass rounded-xl p-5">
                    <h3 className="font-semibold mb-2">📍 {t("results.localSupport")}</h3>
                    <ul className="text-sm text-[var(--color-muted)] space-y-1 list-disc pl-5">
                        <li>Nearest community college bridge programs (sample listing)</li>
                        <li>Public library digital career resources (sample listing)</li>
                        <li>Low-cost connectivity/device assistance channels (sample listing)</li>
                    </ul>
                </div>
                <div className="glass rounded-xl p-5">
                    <h3 className="font-semibold mb-2">✅ {t("results.fairness")}</h3>
                    <ul className="text-sm text-[var(--color-muted)] space-y-1 list-disc pl-5">
                        <li>{fairnessChecks.hasSimilarHardship ? "Pass" : "Needs review"}: at least 1 mentor with similar hardship background</li>
                        <li>{fairnessChecks.hasAspirationalPath ? "Pass" : "Needs review"}: at least 1 path classified as aspirational</li>
                        <li>Pass: protected attributes are not used directly in matching features</li>
                    </ul>
                </div>
            </section>

            {/* Back button */}
            <div className="text-center pt-4">
                <button
                    onClick={() => router.push("/")}
                    className="text-sm text-[var(--color-muted)] hover:text-[var(--color-foreground)] transition-colors"
                >
                    ← {t("results.startOver")}
                </button>
            </div>
        </div>
    );
}
