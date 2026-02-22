"use client";

import { useEffect, useState, use } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
    generateEmail,
    regenerateEmail,
    getMatchDetail,
    getStudentMatches,
    type EmailResponse,
    type MentorSnapshot,
    type MatchResult,
} from "@/lib/api";
import EmailPreview from "@/components/EmailPreview";
import { useI18n } from "@/components/LanguageProvider";

interface PageProps {
    params: Promise<{ sessionId: string; mentorId: string }>;
}

export default function EmailPage({ params }: PageProps) {
    const { sessionId, mentorId } = use(params);
    const router = useRouter();
    const { t } = useI18n();
    const searchParams = useSearchParams();
    const score = parseFloat(searchParams.get("score") || "0.5");

    const [emailData, setEmailData] = useState<EmailResponse | null>(null);
    const [mentor, setMentor] = useState<MentorSnapshot | null>(null);
    const [match, setMatch] = useState<MatchResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [regenerating, setRegenerating] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        async function load() {
            try {
                const [emailRes, mentorRes, matchRes] = await Promise.all([
                    generateEmail({
                        student_id: sessionId,
                        mentor_id: mentorId,
                        match_score: score,
                    }),
                    getMatchDetail(mentorId),
                    getStudentMatches(sessionId),
                ]);
                setEmailData(emailRes);
                setMentor(mentorRes.snapshot);
                setMatch(matchRes.matches.find((m) => m.profile_id === mentorId) || null);
            } catch (err: unknown) {
                setError(err instanceof Error ? err.message : t("email.error.generate"));
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [sessionId, mentorId, score, t]);

    const explainBullets = (() => {
        if (!match) return [];
        const s = match.dimension_scores;
        const rows: Array<{ value: number; text: string }> = [
            { value: s.geo_score || 0, text: t("email.why1") },
            { value: s.edu_tier_score || 0, text: t("email.why2") },
            { value: s.hardship_score || 0, text: t("email.why3") },
            { value: s.function_score || 0, text: "Función objetivo alineada" },
            { value: s.salary_score || 0, text: "La trayectoria salarial se alinea con tu rango esperado" },
        ];
        return rows
            .sort((a, b) => b.value - a.value)
            .slice(0, 3)
            .map((r) => `${r.text} (${Math.round(r.value * 100)}%)`);
    })();

    const hooks = (() => {
        const base = [
            t("email.hook1"),
            t("email.hook2"),
            t("email.hook3"),
        ];
        if (match?.dimension_scores.salary_score && match.dimension_scores.salary_score > 0.7) {
            base.unshift(t("email.hookSalary"));
        }
        return base.slice(0, 3);
    })();

    const handleRegenerate = async () => {
        setRegenerating(true);
        try {
            const res = await regenerateEmail({
                student_id: sessionId,
                mentor_id: mentorId,
                match_score: score,
            });
            setEmailData(res);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : t("email.error.regen"));
        } finally {
            setRegenerating(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <span className="inline-block w-10 h-10 border-3 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
                    <p className="text-[var(--color-muted)]">{t("email.loading")}</p>
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
                    <button onClick={() => router.back()} className="btn-primary">
                        ← {t("email.goBack")}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10 space-y-8">
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
                <button
                    onClick={() => router.back()}
                    className="text-sm text-[var(--color-muted)] hover:text-[var(--color-foreground)] transition-colors mb-4"
                >
                    ← {t("email.back")}
                </button>
                <h1 className="text-3xl font-bold">
                    {t("email.connectWith")}{" "}
                    <span className="gradient-text">{emailData?.mentor_label || "Mentor/a"}</span>
                </h1>
                {emailData?.provider && (
                    <p className="text-xs mt-2 text-[var(--color-muted)]">
                        {t("email.generatedBy")} <span className="font-semibold uppercase">{emailData.provider}</span>
                        {emailData.model ? ` · ${emailData.model}` : ""}
                        {emailData.used_fallback ? ` · ${t("email.fallbackUsed")}` : ""}
                    </p>
                )}
            </motion.div>

            {/* Mentor snapshot */}
            {mentor && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="glass rounded-2xl p-6"
                >
                    <h2 className="font-semibold mb-3 text-sm uppercase tracking-wider text-[var(--color-muted)]">
                        {t("email.mentorProfile")}
                    </h2>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                        <div>
                            <p className="text-[var(--color-muted)] text-xs mb-1">{t("email.field.title")}</p>
                            <p className="font-medium">{mentor.current_title || t("mentor.na")}</p>
                        </div>
                        <div>
                            <p className="text-[var(--color-muted)] text-xs mb-1">{t("email.field.level")}</p>
                            <p className="font-medium">{mentor.current_level || t("mentor.na")}</p>
                        </div>
                        <div>
                            <p className="text-[var(--color-muted)] text-xs mb-1">{t("email.field.industry")}</p>
                            <p className="font-medium">{mentor.industry || t("mentor.na")}</p>
                        </div>
                        <div>
                            <p className="text-[var(--color-muted)] text-xs mb-1">{t("email.field.matchScore")}</p>
                            <p className="font-medium text-[var(--color-primary)]">
                                {Math.round(score * 100)}%
                            </p>
                        </div>
                    </div>
                    {mentor.education_summary.length > 0 && (
                        <div className="mt-4">
                            <p className="text-[var(--color-muted)] text-xs mb-1.5">{t("email.field.education")}</p>
                            <div className="flex flex-wrap gap-2">
                                {mentor.education_summary.map((edu, i) => (
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
                </motion.div>
            )}

            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="glass rounded-2xl p-6"
            >
                <h2 className="font-semibold mb-3 text-sm uppercase tracking-wider text-[var(--color-muted)]">
                    {t("email.whyMatched")}
                </h2>
                <ul className="space-y-2 text-sm">
                    {(explainBullets.length ? explainBullets : [
                        t("email.why1"),
                        t("email.why2"),
                        t("email.why3"),
                    ]).map((b) => (
                        <li key={b} className="text-[var(--color-muted)]">• {b}</li>
                    ))}
                </ul>
                <h3 className="font-semibold mt-4 mb-2 text-sm">{t("email.hooks")}</h3>
                <ul className="space-y-2 text-sm text-[var(--color-muted)]">
                    {hooks.map((h) => (
                        <li key={h}>• {h}</li>
                    ))}
                </ul>
            </motion.div>

            {/* Email preview */}
            {emailData && (
                <EmailPreview
                    email={emailData.email}
                    mentorLabel={emailData.mentor_label}
                    matchScore={emailData.match_score}
                    onRegenerate={handleRegenerate}
                    isRegenerating={regenerating}
                />
            )}

            {/* Tips */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="glass rounded-2xl p-6"
            >
                <h3 className="font-semibold mb-3">💡 {t("email.tips")}</h3>
                <ul className="space-y-2 text-sm text-[var(--color-muted)]">
                    <li>✅ {t("email.tip1")}</li>
                    <li>✅ {t("email.tip2")}</li>
                    <li>✅ {t("email.tip3")}</li>
                    <li>✅ {t("email.tip4")}</li>
                    <li>⚠️ {t("email.tip5")}</li>
                </ul>
            </motion.div>
        </div>
    );
}
