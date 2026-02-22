"use client";

import { motion } from "framer-motion";
import type { MatchResult } from "@/lib/api";
import { useI18n } from "@/components/LanguageProvider";

interface MentorCardProps {
    match: MatchResult;
    index: number;
    onConnect: (profileId: string, score: number) => void;
}

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
    const { t } = useI18n();
    const snap = match.profile_snapshot;
    const totalPercent = Math.round(match.total_score * 100);
    const dimLabels: Record<string, string> = {
        geo_score: t("mentor.geography"),
        edu_tier_score: t("mentor.education"),
        hardship_score: t("mentor.background"),
        function_score: t("mentor.careerGoal"),
        state_score: t("mentor.state"),
        level_score: t("mentor.level"),
        salary_score: t("mentor.salaryFit"),
    };
    const keySignals = ["geo_score", "edu_tier_score", "hardship_score"];
    const extraSignals = Object.entries(match.dimension_scores).filter(
        ([key]) => !keySignals.includes(key)
    );

    const bestSimilarity = (() => {
        const entries = Object.entries(match.dimension_scores).filter(
            ([k]) => dimLabels[k]
        );
        if (!entries.length) return t("mentor.balanced");
        const [topKey] = entries.sort((a, b) => b[1] - a[1])[0];
        if (topKey === "edu_tier_score") return t("mentor.keySchool");
        if (topKey === "hardship_score") return t("mentor.keyHardship");
        if (topKey === "geo_score" || topKey === "state_score") return t("mentor.keyGeo");
        if (topKey === "function_score") return t("mentor.keyFunction");
        if (topKey === "level_score") return t("mentor.keyLevel");
        return t("mentor.keyOverall");
    })();

    const companySizeLabel = (size: number | null) => {
        if (!size) return t("mentor.unknownSize");
        if (size < 50) return t("mentor.sizeSmall");
        if (size < 500) return t("mentor.sizeMid");
        if (size < 5000) return t("mentor.sizeLarge");
        return t("mentor.sizeEnterprise");
    };
    const formatMoney = (n?: number | null) =>
        typeof n === "number" ? `$${n.toLocaleString()}` : t("mentor.na");

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
                            {snap.current_title || t("mentor.professional")} · {snap.current_level || t("mentor.na")}
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
                    <span className="text-[0.65rem] text-[var(--color-muted)] mt-1">{t("mentor.match")}</span>
                </div>
            </div>

            {/* Info grid */}
            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                <div className="glass rounded-lg p-3">
                    <p className="text-[var(--color-muted)] text-xs mb-1">{t("mentor.industry")}</p>
                    <p className="font-medium">{snap.industry || "-"}</p>
                </div>
                <div className="glass rounded-lg p-3">
                    <p className="text-[var(--color-muted)] text-xs mb-1">{t("mentor.companySize")}</p>
                    <p className="font-medium">{companySizeLabel(snap.company_size)}</p>
                </div>
                <div className="glass rounded-lg p-3 col-span-2">
                    <p className="text-[var(--color-muted)] text-xs mb-1">{t("mentor.salaryTrajectory")}</p>
                    <p className="font-medium">
                        {formatMoney(snap.initial_salary)} → {formatMoney(snap.final_salary)}
                    </p>
                </div>
            </div>

            <div className="mb-4">
                <span className="text-xs px-2.5 py-1 rounded-full border border-[var(--color-primary)]/40 bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                    {bestSimilarity}
                </span>
            </div>

            {/* Education */}
            {snap.education_summary.length > 0 && (
                <div className="mb-4">
                    <p className="text-xs text-[var(--color-muted)] mb-1.5">{t("mentor.education")}</p>
                    <div className="flex flex-wrap gap-2">
                        {snap.education_summary.map((edu, i) => (
                            <span
                                key={i}
                                className="text-xs px-2.5 py-1 rounded-full bg-[var(--color-surface)] border border-[var(--color-border)]"
                            >
                                {edu.degree || "Título"}{edu.field ? ` en ${edu.field}` : ""}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Dimension scores */}
            <div className="space-y-2 mb-5">
                {keySignals.map((key) => (
                    <ScoreBar
                        key={key}
                        label={dimLabels[key] || key}
                        value={match.dimension_scores[key] ?? 0}
                    />
                ))}
                {extraSignals.length > 0 && (
                    <details className="pt-1">
                        <summary className="cursor-pointer text-xs text-[var(--color-muted)] hover:text-[var(--color-foreground)]">
                            {t("mentor.details")}
                        </summary>
                        <div className="space-y-2 mt-2">
                            {extraSignals.map(([key, val]) => (
                                <ScoreBar key={key} label={dimLabels[key] || key} value={val} />
                            ))}
                        </div>
                    </details>
                )}
            </div>

            {/* CTA */}
            <button
                onClick={() => onConnect(match.profile_id, match.total_score)}
                className="btn-primary w-full text-center text-sm"
            >
                ✉️ &nbsp; {t("mentor.generateIntro")}
            </button>
        </motion.div>
    );
}
