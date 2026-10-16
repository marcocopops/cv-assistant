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
  es: {
    "home.pageTitle": "Marc-Antoine Meunier — Proyectos personales",
    "home.tagline": "Ingeniero de software — proyectos personales",
    "home.contact": "Contacto",
    "project.cv.title": "CV Assistant",
    "project.cv.description":
      "Un asistente de IA alojado en mi propio servidor, que responde a preguntas sobre mi trayectoria.",
    "project.try": "Probar",
    "project.source": "Código fuente",
    "chat.pageTitle": "CV Assistant — Marc-Antoine Meunier",
    "chat.back": "← Proyectos",
    "chat.source": "Código fuente",
    "chat.greeting":
      "Hola, soy el asistente de recursos humanos de Marc-Antoine Meunier. Puede preguntarme sobre sus competencias y su trayectoria profesional.",
    "chat.inputLabel": "Su pregunta",
    "chat.placeholder": "Escriba su pregunta…",
    "chat.send": "Enviar",
    "chat.suggestions": "Preguntas sugeridas",
    "chat.q1": "¿Dónde estudió Marc-Antoine?",
    "chat.q2": "¿Qué lenguajes de programación conoce?",
    "chat.q3": "¿Cuál es la capital de Australia?",
    "chat.q4": "¿Cómo se ha construido este asistente?",
    "chat.notice":
      "Proyecto personal: el asistente puede equivocarse. Las preguntas se conservan 90 días para mejorarlo y detectar abusos; no introduzca datos personales.",
    "chat.thinking": "El asistente está pensando…",
    "chat.queued": "Está en la posición {n} de la cola…",
    "chat.busy": "El asistente está muy solicitado. Inténtelo de nuevo en un momento.",
    "chat.error": "Se ha producido un error. Inténtelo de nuevo en un momento.",
    "chat.offline": "El asistente no está disponible en este momento. Inténtelo más tarde.",
    "chat.sources": "Fuentes (base de conocimiento en francés): {list}",
    "chat.noLlm": "No se ha encontrado información relevante: respuesta instantánea, sin llamar al modelo.",
  },
  en: {
    "home.pageTitle": "Marc-Antoine Meunier — Personal projects",
    "home.tagline": "Software engineer — personal projects",
    "home.contact": "Contact",
    "project.cv.title": "CV Assistant",
    "project.cv.description":
      "An AI assistant hosted on my own server, answering questions about my background.",
    "project.try": "Try it",
    "project.source": "Source code",
    "chat.pageTitle": "CV Assistant — Marc-Antoine Meunier",
    "chat.back": "← Projects",
    "chat.source": "Source code",
    "chat.greeting":
      "Hello, I'm Marc-Antoine Meunier's HR assistant. Ask me about his skills and professional background.",
    "chat.inputLabel": "Your question",
    "chat.placeholder": "Ask your question…",
    "chat.send": "Send",
    "chat.suggestions": "Suggested questions",
    "chat.q1": "Where did Marc-Antoine study?",
    "chat.q2": "What programming languages does he know?",
    "chat.q3": "What is the capital of Australia?",
    "chat.q4": "How was this assistant built?",
    "chat.notice":
      "Personal project: the assistant can make mistakes. Questions are kept for 90 days to improve it and detect abuse; please don't enter personal information.",
    "chat.thinking": "The assistant is thinking…",
    "chat.queued": "You are number {n} in the queue…",
    "chat.busy": "The assistant is very busy. Please try again in a moment.",
    "chat.error": "Something went wrong. Please try again in a moment.",
    "chat.offline": "The assistant is offline right now. Please try again later.",
    "chat.sources": "Sources (French knowledge base): {list}",
    "chat.noLlm": "No relevant information found: instant answer, without calling the model.",
  },
};

const AVAILABLE = Object.keys(TRANSLATIONS);
const FALLBACK = "en"; // visitors whose browser prefers none of the supported languages

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