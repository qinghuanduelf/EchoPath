"use client";

import { useEffect, useState, use } from "react";
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

interface PageProps {
    params: Promise<{ sessionId: string }>;
}

export default function ResultsPage({ params }: PageProps) {
    const { sessionId } = use(params);
    const router = useRouter();

    const [paths, setPaths] = useState<CareerPath[]>([]);
    const [matches, setMatches] = useState<MatchResult[]>([]);
    const [hardship, setHardship] = useState<number | null>(null);
    const [fips, setFips] = useState<string>("");
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
                        Your <span className="gradient-text">Career Analysis</span>
                    </h1>
                    <p className="text-[var(--color-muted)] mt-1">
                        {matches.length} potential mentor{matches.length !== 1 ? "s" : ""} found ·{" "}
                        {paths.length} career path{paths.length !== 1 ? "s" : ""} identified
                    </p>
                </div>
                {hardship !== null && <HardshipBadge score={hardship} fips={fips || undefined} />}
            </motion.div>

            {/* Paths section */}
            <section>
                <motion.h2
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.1 }}
                    className="text-xl font-semibold mb-4 flex items-center gap-2"
                >
                    🗺️ Career Paths
                </motion.h2>
                <PathVisualization paths={paths} />
            </section>

            {/* Mentors section */}
            <section>
                <motion.h2
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-xl font-semibold mb-4 flex items-center gap-2"
                >
                    👤 Matched Mentors
                </motion.h2>
                {matches.length === 0 ? (
                    <div className="glass rounded-2xl p-8 text-center text-[var(--color-muted)]">
                        No matches found. Try adjusting your criteria.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        {matches.map((m, i) => (
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

            {/* Back button */}
            <div className="text-center pt-4">
                <button
                    onClick={() => router.push("/")}
                    className="text-sm text-[var(--color-muted)] hover:text-[var(--color-foreground)] transition-colors"
                >
                    ← Start a new search
                </button>
            </div>
        </div>
    );
}
