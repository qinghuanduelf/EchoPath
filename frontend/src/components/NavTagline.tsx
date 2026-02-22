"use client";

import { useI18n } from "@/components/LanguageProvider";

export default function NavTagline() {
  const { t } = useI18n();
  return (
    <p className="text-sm text-[var(--color-muted)] hidden md:block">
      {t("nav.tagline")}
    </p>
  );
}
