export type Locale = "en" | "es";

type Dict = Record<string, string>;

export const messages: Record<Locale, Dict> = {
  en: {
    "nav.tagline": "Every path was once walked by someone before you.",
    "footer.text":
      "Built with love for students from underserved communities",
    "lang.english": "English",
    "lang.spanish": "Español",
    "lang.label": "Language",
    "home.title": "Find Your Career Path",
    "home.subtitle":
      "Designed for students with limited access to career resources — we match mentors with similar starting points.",
    "home.formTitle": "Tell us about yourself",
    "home.formHint":
      "We'll find mentors and career paths that match your background.",
    "home.findPath": "Find My Path",
    "home.analyzing": "Analyzing...",
    "results.title": "Your Career Analysis",
    "results.banner":
      "Based on your area's hardship index ({score}/100), we prioritize reachable mentors + low-cost skill paths.",
    "results.mode": "Recommendation mode:",
    "results.reachable": "Reachable Paths",
    "results.aspirational": "Aspirational Paths",
    "results.modeHintReachable":
      "Default: emphasizes feasibility under resource constraints.",
    "results.modeHintAspirational":
      "Higher-upside option: more aggressive growth paths with potentially higher cost.",
    "results.paths": "Career Paths",
    "results.mentors": "Matched Mentors",
    "results.noMatches": "No matches found. Try adjusting your criteria.",
    "results.localSupport": "Local Support Finder (demo)",
    "results.fairness": "Fairness Check (prototype)",
    "results.startOver": "Start a new search",
    "email.back": "Back to Results",
    "email.connectWith": "Connect with",
    "email.whyMatched": "Why you were matched",
    "email.hooks": "Icebreaker hooks",
    "email.tips": "Tips for Reaching Out",
    "email.previewTitle": "Icebreaker Email",
    "email.regenerate": "Regenerate",
    "email.copy": "Copy",
    "email.copied": "Copied!",
  },
  es: {
    "nav.tagline": "Alguien recorrió antes cada camino que hoy exploras.",
    "footer.text":
      "Creado con cariño para estudiantes de comunidades con menos recursos",
    "lang.english": "English",
    "lang.spanish": "Español",
    "lang.label": "Idioma",
    "home.title": "Encuentra tu camino profesional",
    "home.subtitle":
      "Diseñado para estudiantes con acceso limitado a recursos de carrera: conectamos con mentores de puntos de partida similares.",
    "home.formTitle": "Cuéntanos sobre ti",
    "home.formHint":
      "Buscaremos mentores y rutas profesionales que encajen con tu contexto.",
    "home.findPath": "Encontrar mi ruta",
    "home.analyzing": "Analizando...",
    "results.title": "Tu análisis de carrera",
    "results.banner":
      "Según el índice de dificultad de tu zona ({score}/100), priorizamos mentores alcanzables y rutas de bajo costo.",
    "results.mode": "Modo de recomendación:",
    "results.reachable": "Rutas alcanzables",
    "results.aspirational": "Rutas aspiracionales",
    "results.modeHintReachable":
      "Predeterminado: prioriza viabilidad bajo restricciones de recursos.",
    "results.modeHintAspirational":
      "Mayor potencial: rutas más agresivas con posible mayor costo.",
    "results.paths": "Rutas profesionales",
    "results.mentors": "Mentores recomendados",
    "results.noMatches":
      "No se encontraron coincidencias. Prueba ajustando tus criterios.",
    "results.localSupport": "Apoyo local (demo)",
    "results.fairness": "Chequeo de equidad (prototipo)",
    "results.startOver": "Iniciar una nueva búsqueda",
    "email.back": "Volver a resultados",
    "email.connectWith": "Conectar con",
    "email.whyMatched": "Por qué hiciste match",
    "email.hooks": "Frases de apertura",
    "email.tips": "Consejos para contactar",
    "email.previewTitle": "Correo de presentación",
    "email.regenerate": "Regenerar",
    "email.copy": "Copiar",
    "email.copied": "¡Copiado!",
  },
};

export function translate(
  locale: Locale,
  key: string,
  vars?: Record<string, string | number>
): string {
  const template = messages[locale][key] || messages.en[key] || key;
  if (!vars) return template;
  return Object.entries(vars).reduce(
    (acc, [k, v]) => acc.replaceAll(`{${k}}`, String(v)),
    template
  );
}
