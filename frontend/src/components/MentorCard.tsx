"use client";

import { motion } from "framer-motion";
import type { MatchResult } from "@/lib/api";

interface MentorCardProps {
    match: MatchResult;
    index: number;
    onConnect: (profileId: string, score: number) => void;
}

const DIM_LABELS: Record<string, string> = {
    geo_score: "Geography",
    edu_tier_score: "Education",
    hardship_score: "Background",
    function_score: "Career Goal",
    state_score: "State",
};

function ScoreBar({ label, value }: { label: string; value: number }) {
    return (
        <div className="flex items-center gap-2 text-xs">
            <span className="w-20 text-[var(--color-muted)] truncate">{label}</span>
            <div className="flex-1 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                <motion.div
                    className="h-full rounded-full"
                    style={{ background: "linear-gradient(90deg, #667eea, #f093fb)" }}
                    initial={{ width: 0 }}
                    animate={{ width: `${value * 100}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                />
            </div>
            <span className="w-8 text-right text-[var(--color-muted)]">
                {Math.round(value * 100)}
            </span>
        </div>
    );
}

export default function MentorCard({ match, index, onConnect }: MentorCardProps) {
    const snap = match.profile_snapshot;
    const totalPercent = Math.round(match.total_score * 100);

    const companySizeLabel = (size: number | null) => {
        if (!size) return "Unknown size";
        if (size < 50) return "Small Company (< 50)";
        if (size < 500) return "Mid-size Company (50–500)";
        if (size < 5000) return "Large Company (500–5K)";
        return "Enterprise (5K+)";
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="glass rounded-2xl p-6 glass-hover transition-all duration-300"
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold"
                        style={{ background: "linear-gradient(135deg, #667eea, #764ba2)" }}>
                        {index + 1}
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg">
                            Mentor #{match.profile_id.slice(0, 6).toUpperCase()}
                        </h3>
                        <p className="text-sm text-[var(--color-muted)]">
                            {snap.current_title || "Professional"} · {snap.current_level || "N/A"}
                        </p>
                    </div>
                </div>

                {/* Match score badge */}
                <div className="flex flex-col items-center">
                    <div
                        className="w-14 h-14 rounded-full flex items-center justify-center text-sm font-bold border-2"
                        style={{
                            borderColor: totalPercent > 70 ? "#4ade80" : totalPercent > 40 ? "#fbbf24" : "#667eea",
                            color: totalPercent > 70 ? "#4ade80" : totalPercent > 40 ? "#fbbf24" : "#667eea",
                        }}
                    >
                        {totalPercent}%
                    </div>
                    <span className="text-[0.65rem] text-[var(--color-muted)] mt-1">Match</span>
                </div>
            </div>

            {/* Info grid */}
            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                <div className="glass rounded-lg p-3">
                    <p className="text-[var(--color-muted)] text-xs mb-1">Industry</p>
                    <p className="font-medium">{snap.industry || "Various"}</p>
                </div>
                <div className="glass rounded-lg p-3">
                    <p className="text-[var(--color-muted)] text-xs mb-1">Company Size</p>
                    <p className="font-medium">{companySizeLabel(snap.company_size)}</p>
                </div>
            </div>

            {/* Education */}
            {snap.education_summary.length > 0 && (
                <div className="mb-4">
                    <p className="text-xs text-[var(--color-muted)] mb-1.5">Education</p>
                    <div className="flex flex-wrap gap-2">
                        {snap.education_summary.map((edu, i) => (
                            <span
                                key={i}
                                className="text-xs px-2.5 py-1 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)]"
                            >
                                {edu.degree || "Degree"}{edu.field ? ` in ${edu.field}` : ""}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Dimension scores */}
            <div className="space-y-2 mb-5">
                {Object.entries(match.dimension_scores).map(([key, val]) => (
                    <ScoreBar key={key} label={DIM_LABELS[key] || key} value={val} />
                ))}
            </div>

            {/* CTA */}
            <button
                onClick={() => onConnect(match.profile_id, match.total_score)}
                className="btn-primary w-full text-center text-sm"
            >
                ✉️ &nbsp; Connect with this Mentor
            </button>
        </motion.div>
    );
}
