// Translations and language selection, shared by every page.
// Elements carry data-i18n="key" (text) or data-i18n-placeholder="key": all texts live here.

const TRANSLATIONS = {
  fr: {
    "home.pageTitle": "Marc-Antoine Meunier — Projets personnels",
    "home.tagline": "Ingénieur logiciel — projets personnels",
    "home.contact": "Contact",
    "project.cv.title": "CV Assistant",
    "project.cv.description":
      "Un assistant IA hébergé sur mon propre serveur, qui répond aux questions sur mon parcours.",
    "project.try": "Essayer",
    "project.source": "Code source",
    "chat.pageTitle": "CV Assistant — Marc-Antoine Meunier",
    "chat.back": "← Projets",
    "chat.source": "Code source",
    "chat.greeting":
      "Bonjour, je suis l'assistant RH de Marc-Antoine Meunier. Posez-moi des questions sur ses compétences et son parcours professionnel.",
    "chat.inputLabel": "Votre question",
    "chat.placeholder": "Posez votre question…",
    "chat.send": "Envoyer",
    "chat.suggestions": "Questions suggérées",
    "chat.q1": "Où Marc-Antoine a-t-il fait ses études ?",
    "chat.q2": "Quels langages de programmation connaît-il ?",
    "chat.q3": "Quelle est la capitale de l'Australie ?",
    "chat.q4": "Comment est construit cet assistant ?",
    "chat.notice":
      "Projet personnel : l'assistant peut se tromper. Les questions sont conservées 90 jours pour l'améliorer et détecter les abus ; n'y saisissez pas d'informations personnelles.",
    "chat.thinking": "L'assistant réfléchit…",
    "chat.queued": "Vous êtes n°{n} dans la file d'attente…",
    "chat.busy": "L'assistant est très sollicité. Réessayez dans un instant.",
    "chat.error": "Une erreur est survenue. Réessayez dans un instant.",
    "chat.offline": "L'assistant est hors ligne pour le moment. Réessayez plus tard.",
    "chat.sources": "Sources : {list}",
    "chat.noLlm": "Aucune information pertinente trouvée : réponse instantanée, sans appel au modèle.",
  },
};

const AVAILABLE = Object.keys(TRANSLATIONS);
const FALLBACK = "fr"; // switch to "en" once the English translation exists

function storedLanguage() {
  try { return localStorage.getItem("lang"); } catch { return null; }
}

function storeLanguage(lang) {
  try { localStorage.setItem("lang", lang); } catch { /* storage unavailable: not remembered */ }
}

// Order: explicit ?lang= parameter, remembered choice, browser preferences, fallback.
function pickLanguage() {
  const requested = new URLSearchParams(location.search).get("lang");
  if (AVAILABLE.includes(requested)) {
    storeLanguage(requested);
    return requested;
  }
  const stored = storedLanguage();
  if (AVAILABLE.includes(stored)) return stored;
  for (const tag of navigator.languages ?? []) {
    const base = tag.slice(0, 2).toLowerCase();
    if (AVAILABLE.includes(base)) return base;
  }
  return FALLBACK;
}

export const LANG = pickLanguage();

export function t(key, params = {}) {
  const text = TRANSLATIONS[LANG][key] ?? TRANSLATIONS[FALLBACK][key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? ""));
}

function applyTranslations() {
  document.documentElement.lang = LANG;
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-placeholder]")) {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  }
}

function renderLanguageSwitcher() {
  if (AVAILABLE.length < 2) return; // nothing to choose yet
  for (const nav of document.querySelectorAll(".lang-switch")) {
    for (const lang of AVAILABLE) {
      const link = document.createElement("a");
      link.href = `?lang=${lang}`;
      link.textContent = lang.toUpperCase();
      if (lang === LANG) link.setAttribute("aria-current", "true");
      nav.append(link);
    }
  }
}

applyTranslations();
renderLanguageSwitcher();