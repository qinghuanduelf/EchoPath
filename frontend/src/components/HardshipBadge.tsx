"use client";

import { motion } from "framer-motion";

interface HardshipBadgeProps {
    score: number; // 0-1, 1 = most disadvantaged
    fips?: string;
}

export default function HardshipBadge({ score, fips }: HardshipBadgeProps) {
    const percent = Math.round(score * 100);

    // Color gradient: green (low) → yellow (mid) → red (high hardship)
    const getColor = (s: number) => {
        if (s < 0.33) return { bg: "rgba(74,222,128,0.15)", border: "#4ade80", text: "#4ade80", label: "Low" };
        if (s < 0.66) return { bg: "rgba(251,191,36,0.15)", border: "#fbbf24", text: "#fbbf24", label: "Moderate" };
        return { bg: "rgba(248,113,113,0.15)", border: "#f87171", text: "#f87171", label: "High" };
    };

    const color = getColor(score);
    const factorRows =
        score >= 0.66
            ? [
                "Broadband access: bottom 15%",
                "Title I share: top 20%",
                "Median income: bottom 20%",
            ]
            : score >= 0.33
                ? [
                    "Broadband access: bottom 35%",
                    "Title I share: top 35%",
                    "Median income: bottom 35%",
                ]
                : [
                    "Broadband access: middle-to-strong range",
                    "Title I share: moderate range",
                    "Median income: middle-to-strong range",
                ];
    const hardshipIntensity = Math.round(score * 100);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="inline-flex items-start gap-3 rounded-xl px-4 py-3 max-w-[28rem]"
            style={{ background: color.bg, border: `1px solid ${color.border}` }}
        >
            {/* Radial gauge */}
            <div className="relative w-12 h-12">
                <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle
                        cx="18" cy="18" r="15"
                        fill="none"
                        stroke="var(--color-border)"
                        strokeWidth="3"
                    />
                    <motion.circle
                        cx="18" cy="18" r="15"
                        fill="none"
                        stroke={color.border}
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeDasharray={`${percent * 0.94} 94`}
                        initial={{ strokeDasharray: "0 94" }}
                        animate={{ strokeDasharray: `${percent * 0.94} 94` }}
                        transition={{ duration: 1.2, ease: "easeOut" }}
                    />
                </svg>
                <span
                    className="absolute inset-0 flex items-center justify-center text-xs font-bold"
                    style={{ color: color.text }}
                >
                    {percent}
                </span>
            </div>

            <div>
                <p className="text-xs uppercase tracking-wider" style={{ color: color.text }}>
                    {color.label} Hardship
                </p>
                <p className="text-[0.7rem] text-[var(--color-muted)]">
                    Area Economic Hardship Index{fips ? ` · FIPS ${fips}` : ""}
                </p>
                <details className="mt-2 text-xs text-[var(--color-muted)]">
                    <summary className="cursor-pointer hover:text-[var(--color-foreground)] transition-colors">
                        Why this score and how we use it
                    </summary>
                    <div className="mt-2 space-y-3">
                        <div>
                            <p className="text-[0.7rem] uppercase tracking-wider mb-1">Top-3 contributing factors</p>
                            <ul className="space-y-1 list-disc pl-4">
                                {factorRows.map((item) => (
                                    <li key={item}>{item}</li>
                                ))}
                            </ul>
                        </div>
                        <div>
                            <p className="text-[0.7rem] uppercase tracking-wider mb-1">How it changes recommendations</p>
                            <div className="space-y-1.5">
                                <p>hardship ↑ ({hardshipIntensity}/100) → reachable mentor weight ↑</p>
                                <p>hardship ↑ ({hardshipIntensity}/100) → low-cost path weight ↑</p>
                                <p>hardship ↑ ({hardshipIntensity}/100) → elite-only path weight ↓</p>
                            </div>
                        </div>
                        <div>
                            <p className="text-[0.7rem] uppercase tracking-wider mb-1">Suggested supports</p>
                            <ul className="space-y-1 list-disc pl-4">
                                <li>Prefer mobile-friendly learning resources</li>
                                <li>Recommend local community college bridge programs</li>
                                <li>Prioritize mentors who overcame similar constraints</li>
                            </ul>
                        </div>
                    </div>
                </details>
            </div>
        </motion.div>
    );
}
