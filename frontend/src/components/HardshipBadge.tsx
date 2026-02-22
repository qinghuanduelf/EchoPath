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

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="inline-flex items-center gap-3 rounded-xl px-4 py-3"
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
            </div>
        </motion.div>
    );
}
