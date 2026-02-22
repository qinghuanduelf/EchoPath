"use client";

import { useI18n } from "@/components/LanguageProvider";

export default function FooterText() {
  const { t } = useI18n();
  return (
    <p>
      {t("footer.text")} &middot; EchoPath &copy; {new Date().getFullYear()}
    </p>
  );
}
