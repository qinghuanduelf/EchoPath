"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
    ClipboardDocumentIcon,
    ArrowPathIcon,
    CheckIcon,
} from "@heroicons/react/24/outline";

interface EmailPreviewProps {
    email: string;
    mentorLabel: string;
    matchScore: number;
    onRegenerate: () => Promise<void>;
    isRegenerating: boolean;
}

export default function EmailPreview({
    email,
    mentorLabel,
    matchScore,
    onRegenerate,
    isRegenerating,
}: EmailPreviewProps) {
    const [editedEmail, setEditedEmail] = useState(email);
    const [copied, setCopied] = useState(false);
    const [isEditing, setIsEditing] = useState(false);

    // Sync if parent regenerates
    if (email !== editedEmail && !isEditing) {
        setEditedEmail(email);
    }

    const handleCopy = async () => {
        await navigator.clipboard.writeText(editedEmail);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass rounded-2xl overflow-hidden"
        >
            {/* Header */}
            <div className="px-6 py-4 border-b border-[var(--color-border)] flex items-center justify-between">
                <div>
                    <h3 className="font-semibold text-lg">Icebreaker Email</h3>
                    <p className="text-sm text-[var(--color-muted)]">
                        To: {mentorLabel} · Match Score: {Math.round(matchScore * 100)}%
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={onRegenerate}
                        disabled={isRegenerating}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm
                       bg-[var(--color-surface)] border border-[var(--color-border)]
                       hover:border-[var(--color-primary)] transition-all disabled:opacity-50"
                    >
                        <ArrowPathIcon className={`w-4 h-4 ${isRegenerating ? "animate-spin" : ""}`} />
                        Regenerate
                    </button>
                    <button
                        onClick={handleCopy}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm
                       bg-[var(--color-surface)] border border-[var(--color-border)]
                       hover:border-[var(--color-primary)] transition-all"
                    >
                        {copied ? (
                            <>
                                <CheckIcon className="w-4 h-4 text-[var(--color-success)]" />
                                <span className="text-[var(--color-success)]">Copied!</span>
                            </>
                        ) : (
                            <>
                                <ClipboardDocumentIcon className="w-4 h-4" />
                                Copy
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Email body */}
            <div className="p-6">
                <textarea
                    value={editedEmail}
                    onChange={(e) => {
                        setEditedEmail(e.target.value);
                        setIsEditing(true);
                    }}
                    onBlur={() => setIsEditing(false)}
                    rows={12}
                    className="w-full bg-[var(--color-surface)] border border-[var(--color-border)]
                     rounded-xl p-4 text-sm leading-relaxed resize-y
                     focus:outline-none focus:border-[var(--color-primary)]
                     focus:ring-2 focus:ring-[var(--color-primary)]/20 transition-all"
                    placeholder="Your generated email will appear here..."
                />
                <p className="mt-3 text-xs text-[var(--color-muted)]">
                    💡 You can edit the email above before copying. Make it personal!
                </p>
            </div>
        </motion.div>
    );
}
