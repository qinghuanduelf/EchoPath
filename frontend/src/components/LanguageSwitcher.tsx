"use client";

import { useI18n } from "@/components/LanguageProvider";

export default function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n();

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-[var(--color-muted)] hidden sm:inline">
        {t("lang.label")}
      </span>
      <select
        aria-label={t("lang.label")}
        value={locale}
        onChange={(e) => setLocale(e.target.value as "en" | "es")}
        className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md px-2 py-1 text-xs"
      >
        <option value="en">{t("lang.english")}</option>
        <option value="es">{t("lang.spanish")}</option>
      </select>
    </div>
  );
}
