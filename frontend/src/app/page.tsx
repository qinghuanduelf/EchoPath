"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { analyzeStudent, type StudentInput } from "@/lib/api";
import {
  EDUCATION_OPTIONS,
  FUNCTION_OPTIONS,
  LEVEL_OPTIONS,
} from "@/lib/constants";

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState<StudentInput>({
    zip_code: "",
    current_education: "",
    target_function: "",
    target_level: "",
    dream_description: "",
    school_name: "",
  });

  const update = (key: keyof StudentInput, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!form.zip_code && !form.fips_code) {
      setError("Please enter a Zip Code or FIPS Code.");
      return;
    }
    if (!form.current_education || !form.target_function || !form.target_level) {
      setError("Please fill in all required fields.");
      return;
    }

    setLoading(true);
    try {
      const result = await analyzeStudent(form);
      router.push(`/results/${result.session_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center px-4 py-16">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12 max-w-2xl"
      >
        <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight">
          Find Your{" "}
          <span className="gradient-text">Career Path</span>
        </h1>
        <p className="text-lg text-[var(--color-muted)] leading-relaxed">
          Discover real career journeys from people who started where you are.
          Connect with mentors who understand your background.
        </p>
      </motion.div>

      {/* Form card */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        onSubmit={handleSubmit}
        className="glass rounded-2xl p-8 w-full max-w-2xl space-y-6 glow-primary"
      >
        <h2 className="text-xl font-semibold mb-1">Tell us about yourself</h2>
        <p className="text-sm text-[var(--color-muted)] mb-4">
          We&apos;ll find mentors and career paths that match your background.
        </p>

        {/* Row 1: Zip + School */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Zip Code <span className="text-[var(--color-danger)]">*</span>
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. 95354"
              value={form.zip_code || ""}
              onChange={(e) => update("zip_code", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">
              School Name <span className="text-[var(--color-muted)]">(optional)</span>
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. Modesto Junior College"
              value={form.school_name || ""}
              onChange={(e) => update("school_name", e.target.value)}
            />
          </div>
        </div>

        {/* Row 2: Education */}
        <div>
          <label className="block text-sm font-medium mb-1.5">
            Current Education Level <span className="text-[var(--color-danger)]">*</span>
          </label>
          <select
            className="input-field"
            value={form.current_education}
            onChange={(e) => update("current_education", e.target.value)}
          >
            <option value="">Select your education level</option>
            {EDUCATION_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>

        {/* Row 3: Target Function + Level */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Target Career Function <span className="text-[var(--color-danger)]">*</span>
            </label>
            <select
              className="input-field"
              value={form.target_function}
              onChange={(e) => update("target_function", e.target.value)}
            >
              <option value="">Select a function</option>
              {FUNCTION_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Target Level <span className="text-[var(--color-danger)]">*</span>
            </label>
            <select
              className="input-field"
              value={form.target_level}
              onChange={(e) => update("target_level", e.target.value)}
            >
              <option value="">Select a level</option>
              {LEVEL_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 4: Dream description */}
        <div>
          <label className="block text-sm font-medium mb-1.5">
            Your Dream &amp; Goals <span className="text-[var(--color-muted)]">(optional)</span>
          </label>
          <textarea
            className="input-field resize-none"
            rows={3}
            placeholder="Tell us about your career aspirations in a few sentences..."
            value={form.dream_description || ""}
            onChange={(e) => update("dream_description", e.target.value)}
          />
          <p className="text-xs text-[var(--color-muted)] mt-1">
            This is only used to personalize your icebreaker email — not for matching.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="text-sm text-[var(--color-danger)] bg-[var(--color-danger)]/10 rounded-lg px-4 py-2">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full text-center flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Analyzing...
            </>
          ) : (
            "🔍  Find My Path"
          )}
        </button>
      </motion.form>

      {/* Feature highlights */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mt-16 text-center"
      >
        {[
          { icon: "🗺️", title: "Career Paths", desc: "See the most common career trajectories from similar backgrounds" },
          { icon: "👤", title: "Mentor Matching", desc: "Get matched with professionals who started where you are" },
          { icon: "✉️", title: "Smart Icebreakers", desc: "AI-generated personalized emails to connect with mentors" },
        ].map((f, i) => (
          <div key={i} className="glass rounded-xl p-6 glass-hover transition-all">
            <span className="text-3xl mb-3 block">{f.icon}</span>
            <h3 className="font-semibold mb-1">{f.title}</h3>
            <p className="text-sm text-[var(--color-muted)]">{f.desc}</p>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
