"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { analyzeStudent, type StudentInput } from "@/lib/api";
import { useI18n } from "@/components/LanguageProvider";
import {
  EDUCATION_OPTIONS,
  FUNCTION_OPTIONS,
  LEVEL_OPTIONS,
} from "@/lib/constants";

export default function HomePage() {
  const router = useRouter();
  const { t } = useI18n();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const educationLabelMap: Record<string, string> = {
    "High School": "Secundaria",
    "Community College": "Community College",
    "State University": "Universidad estatal",
    "Flagship State University": "Universidad estatal principal",
    "Private University": "Universidad privada",
    "Ivy League": "Ivy League",
  };
  const functionLabelMap: Record<string, string> = {
    "Software Engineering": "Ingeniería de software",
    "Data Science": "Ciencia de datos",
    "Product Management": "Gestión de producto",
    Marketing: "Marketing",
    Finance: "Finanzas",
    Consulting: "Consultoría",
    Design: "Diseño",
    Sales: "Ventas",
    Operations: "Operaciones",
    "Human Resources": "Recursos humanos",
    Legal: "Legal",
    Healthcare: "Salud",
    Education: "Educación",
    Research: "Investigación",
  };
  const levelLabelMap: Record<string, string> = {
    Intern: "Practicante",
    Staff: "Staff",
    "Senior Staff": "Senior Staff",
    Manager: "Manager",
    "Senior Manager": "Senior Manager",
    Director: "Director",
    VP: "VP",
    "C-Suite": "C-Suite",
  };

  const [form, setForm] = useState<StudentInput>({
    zip_code: "",
    current_education: "",
    target_function: "",
    target_level: "",
    dream_description: "",
    school_name: "",
  });

  const update = (key: keyof StudentInput, value: string | number | undefined) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const isValidUsZip = (zip: string) => {
    const clean = zip.trim();
    if (!/^\d{5}(-\d{4})?$/.test(clean)) return false;
    const zip5 = Number.parseInt(clean.slice(0, 5), 10);
    return zip5 >= 501 && zip5 <= 99950;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (!form.zip_code && !form.fips_code) {
      setError(t("home.error.zipOrFips"));
      return;
    }
    if (form.zip_code && !isValidUsZip(form.zip_code)) {
      setError(t("home.error.invalidZip"));
      return;
    }
    if (!form.current_education || !form.target_function || !form.target_level) {
      setError(t("home.error.required"));
      return;
    }
    if (
      form.expected_salary_min !== undefined &&
      form.expected_salary_max !== undefined &&
      form.expected_salary_min > form.expected_salary_max
    ) {
      setError(t("home.error.salaryRange"));
      return;
    }

    setLoading(true);
    try {
      const result = await analyzeStudent(form);
      router.push(`/results/${result.session_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("home.error.generic"));
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
          <span className="gradient-text">{t("home.title")}</span>
        </h1>
        <p className="text-sm sm:text-base font-medium text-[var(--color-foreground)]/90 mb-2">
          {t("home.subtitle")}
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
        <h2 className="text-xl font-semibold mb-1">{t("home.formTitle")}</h2>
        <p className="text-sm text-[var(--color-muted)] mb-4">
          {t("home.formHint")}
        </p>

        {/* Row 1: Zip + School */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">
              {t("home.label.zip")} <span className="text-[var(--color-danger)]">{t("home.required")}</span>
            </label>
            <input
              type="text"
              className="input-field"
              placeholder={t("home.placeholder.zip")}
              value={form.zip_code || ""}
              onChange={(e) => update("zip_code", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">
              {t("home.label.school")} <span className="text-[var(--color-muted)]">{t("home.optional")}</span>
            </label>
            <input
              type="text"
              className="input-field"
              placeholder={t("home.placeholder.school")}
              value={form.school_name || ""}
              onChange={(e) => update("school_name", e.target.value)}
            />
          </div>
        </div>

        {/* Row 2: Education */}
        <div>
          <label className="block text-sm font-medium mb-1.5">
            {t("home.label.education")} <span className="text-[var(--color-danger)]">{t("home.required")}</span>
          </label>
          <select
            className="input-field"
            value={form.current_education}
            onChange={(e) => update("current_education", e.target.value)}
          >
            <option value="">{t("home.placeholder.education")}</option>
            {EDUCATION_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{educationLabelMap[opt] || opt}</option>
            ))}
          </select>
        </div>

        {/* Row 3: Target Function + Level */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">
              {t("home.label.function")} <span className="text-[var(--color-danger)]">{t("home.required")}</span>
            </label>
            <select
              className="input-field"
              value={form.target_function}
              onChange={(e) => update("target_function", e.target.value)}
            >
              <option value="">{t("home.placeholder.function")}</option>
              {FUNCTION_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{functionLabelMap[opt] || opt}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">
              {t("home.label.level")} <span className="text-[var(--color-danger)]">{t("home.required")}</span>
            </label>
            <select
              className="input-field"
              value={form.target_level}
              onChange={(e) => update("target_level", e.target.value)}
            >
              <option value="">{t("home.placeholder.level")}</option>
              {LEVEL_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{levelLabelMap[opt] || opt}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 4: Expected salary range */}
        <div>
          <label className="block text-sm font-medium mb-1.5">
            {t("home.label.salary")} <span className="text-[var(--color-muted)]">{t("home.optional")}</span>
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <input
              type="number"
              min={0}
              step={1000}
              className="input-field"
              placeholder={t("home.placeholder.salaryMin")}
              value={form.expected_salary_min ?? ""}
              onChange={(e) =>
                update(
                  "expected_salary_min",
                  e.target.value === "" ? undefined : Number.parseInt(e.target.value, 10)
                )
              }
            />
            <input
              type="number"
              min={0}
              step={1000}
              className="input-field"
              placeholder={t("home.placeholder.salaryMax")}
              value={form.expected_salary_max ?? ""}
              onChange={(e) =>
                update(
                  "expected_salary_max",
                  e.target.value === "" ? undefined : Number.parseInt(e.target.value, 10)
                )
              }
            />
          </div>
        </div>

        {/* Row 5: Dream description */}
        <div>
          <label className="block text-sm font-medium mb-1.5">
            {t("home.label.dream")} <span className="text-[var(--color-muted)]">{t("home.optional")}</span>
          </label>
          <textarea
            className="input-field resize-none"
            rows={3}
            placeholder={t("home.placeholder.dream")}
            value={form.dream_description || ""}
            onChange={(e) => update("dream_description", e.target.value)}
          />
          <p className="text-xs text-[var(--color-muted)] mt-1">
            {t("home.dreamNote")}
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
              {t("home.analyzing")}
            </>
          ) : (
            `🔍  ${t("home.findPath")}`
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
          { icon: "🗺️", title: t("home.feature.paths.title"), desc: t("home.feature.paths.desc") },
          { icon: "👤", title: t("home.feature.mentor.title"), desc: t("home.feature.mentor.desc") },
          { icon: "✉️", title: t("home.feature.email.title"), desc: t("home.feature.email.desc") },
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
