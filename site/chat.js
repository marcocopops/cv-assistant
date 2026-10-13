// Assistant chat widget.
// Answers stream as Server-Sent Events over a POST request. EventSource only
// supports GET, so the stream is read with fetch() and parsed by hand.

const API_URL = document.querySelector('meta[name="assistant-api"]').content;
const LANG = document.documentElement.lang;

const TEXTS = {
  fr: {
    thinking: "L'assistant réfléchit…",
    queued: (n) => `Vous êtes n°${n} dans la file d'attente…`,
    busy: "L'assistant est très sollicité. Réessayez dans un instant.",
    error: "Une erreur est survenue. Réessayez dans un instant.",
    offline: "L'assistant est hors ligne pour le moment. Le CV ci-dessus reste à jour.",
    sources: "Sources :",
  },
  en: {
    thinking: "The assistant is thinking…",
    queued: (n) => `You are number ${n} in the queue…`,
    busy: "The assistant is very busy. Please try again in a moment.",
    error: "Something went wrong. Please try again in a moment.",
    offline: "The assistant is offline for now. The résumé above is up to date.",
    sources: "Sources:",
  },
  es: {
    thinking: "El asistente está pensando…",
    queued: (n) => `Usted es el n.º ${n} en la cola…`,
    busy: "El asistente está muy solicitado. Inténtelo de nuevo en un momento.",
    error: "Se ha producido un error. Inténtelo de nuevo en un momento.",
    offline: "El asistente no está disponible por ahora. El currículum de arriba está actualizado.",
    sources: "Fuentes:",
  },
};
const T = TEXTS[LANG] ?? TEXTS.fr;

const form = document.querySelector("#chat-form");
const input = document.querySelector("#chat-input");
const chatLog = document.querySelector("#chat-log");
const controls = document.querySelectorAll("#assistant button, #chat-input");

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (question.length >= 3) ask(question);
});

for (const button of document.querySelectorAll("[data-question]")) {
  button.addEventListener("click", () => ask(button.dataset.question));
}

function addMessage(classes, text) {
  const el = document.createElement("div");
  el.className = `message ${classes}`;
  el.textContent = text; // textContent, never innerHTML: model output is untrusted
  chatLog.append(el);
  el.scrollIntoView({ block: "nearest", behavior: "smooth" });
  return el;
}

function setBusy(busy) {
  for (const el of controls) el.disabled = busy;
  chatLog.setAttribute("aria-busy", busy); // screen readers wait for the full answer
}

async function ask(question) {
  setBusy(true);
  input.value = "";
  addMessage("user", question);
  const answer = addMessage("assistant pending", T.thinking);

  const fail = (text) => {
    answer.textContent = text;
    answer.className = "message assistant failed";
  };

  try {
    let response;
    try {
      response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, lang: LANG }),
      });
    } catch {
      return fail(T.offline); // network error: API unreachable or rejected by CORS
    }
    if (!response.ok) return fail(T.error);

    let sources = [];
    let started = false;
    for await (const { event, data } of readEvents(response)) {
      switch (event) {
        case "queued":
          answer.textContent = T.queued(data.position);
          break;
        case "meta":
          sources = data.sources.map((s) => s.split(" > ").pop());
          break;
        case "token":
          if (!started) {
            answer.textContent = "";
            answer.classList.remove("pending");
            started = true;
          }
          answer.append(data.text); // appended as a text node, never parsed as HTML
          break;
        case "done":
          if (sources.length) {
            const el = document.createElement("small");
            el.className = "sources";
            el.textContent = `${T.sources} ${sources.join(" · ")}`;
            answer.append(el);
          }
          break;
        case "busy":
          return fail(T.busy);
        case "error":
          return fail(T.error);
      }
    }
    if (!started) fail(T.error); // stream ended without any answer
  } finally {
    setBusy(false);
    input.focus();
  }
}

// Parse a Server-Sent Events stream into { event, data } objects.
async function* readEvents(response) {
  // TextDecoderStream reassembles multi-byte characters (é, ñ) split across network chunks.
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) return;
      buffer += value;
      // Network chunks do not align with events: incomplete events stay in the buffer.
      let end;
      while ((end = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, end);
        buffer = buffer.slice(end + 2);
        let event = "message";
        let data = "";
        for (const line of block.split("\n")) {
          if (line.startsWith("event: ")) event = line.slice(7);
          else if (line.startsWith("data: ")) data += line.slice(6);
        }
        yield { event, data: data ? JSON.parse(data) : {} };
      }
    }
  } finally {
    reader.cancel().catch(() => {}); // close the connection if the caller stops early
  }
}