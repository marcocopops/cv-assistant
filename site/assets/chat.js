// Chat page: a typed greeting, then a conversation with the assistant API.
// Answers stream as Server-Sent Events over a POST request. EventSource only
// supports GET, so the stream is read with fetch() and parsed by hand.
import { LANG, t } from "./i18n.js";

const IS_LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);
const API_URL = IS_LOCAL
  ? "http://localhost:8000"
  : document.querySelector('meta[name="assistant-api"]').content;
const SUGGESTION_KEYS = ["chat.q1", "chat.q2", "chat.q3", "chat.q4"];
const REDUCED_MOTION = matchMedia("(prefers-reduced-motion: reduce)").matches;
// On touch screens, focusing the input opens the keyboard, which hides the suggestions.
const FINE_POINTER = matchMedia("(pointer: fine)").matches;

const chatLog = document.querySelector("#chat-log");
const composer = document.querySelector(".composer");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#chat-input");
const suggestions = document.querySelector(".suggestions");
const suggestionList = document.querySelector("#suggestion-list");
const asked = new Set();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function isNearBottom() {
  return chatLog.scrollHeight - chatLog.scrollTop - chatLog.clientHeight < 80;
}

function scrollToEnd() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addMessage(classes, text = "") {
  const el = document.createElement("div");
  el.className = `message ${classes}`;
  el.textContent = text; // never innerHTML: model output is untrusted
  chatLog.append(el);
  scrollToEnd();
  return el;
}

function addNote(message, text) {
  const note = document.createElement("small");
  note.className = "note";
  note.textContent = text;
  message.append(note);
  scrollToEnd();
}

function setBusy(busy) {
  for (const el of composer.querySelectorAll("input, button")) el.disabled = busy;
  chatLog.setAttribute("aria-busy", busy); // screen readers wait for the complete message
}

function renderSuggestions() {
  const remaining = SUGGESTION_KEYS.filter((key) => !asked.has(key));
  suggestionList.replaceChildren(...remaining.map((key) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = t(key);
    button.addEventListener("click", () => {
      asked.add(key);
      renderSuggestions();
      ask(t(key));
    });
    return button;
  }));
  suggestions.hidden = remaining.length === 0;
}

// The greeting is canned, but typed word by word like a generated answer.
async function typeGreeting() {
  chatLog.setAttribute("aria-busy", "true");
  const bubble = addMessage("assistant");
  for (const [i, word] of t("chat.greeting").split(" ").entries()) {
    bubble.append(i ? ` ${word}` : word);
    if (!REDUCED_MOTION) await sleep(40 + Math.random() * 60);
  }
  chatLog.setAttribute("aria-busy", "false");
}

async function ask(question) {
  setBusy(true);
  input.value = "";
  addMessage("user", question);
  const bubble = addMessage("assistant pending", t("chat.thinking"));

  const fail = (key) => {
    bubble.textContent = t(key);
    bubble.className = "message assistant failed";
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
      return fail("chat.offline"); // network error: API unreachable or rejected by CORS
    }
    if (!response.ok) return fail("chat.error");

    let sources = [];
    let started = false;
    for await (const { event, data } of readEvents(response)) {
      switch (event) {
        case "queued":
          bubble.textContent = t("chat.queued", { n: data.position });
          break;
        case "meta":
          sources = data.sources.map((s) => s.split(" > ").pop());
          break;
        case "token": {
          const follow = isNearBottom(); // do not pull a visitor who scrolled up back down
          if (!started) {
            bubble.textContent = "";
            bubble.classList.remove("pending");
            started = true;
          }
          bubble.append(data.text); // appended as a text node, never parsed as HTML
          if (follow) scrollToEnd();
          break;
        }
        case "done":
          addNote(bubble, data.llm ? t("chat.sources", { list: sources.join(" · ") }) : t("chat.noLlm"));
          break;
        case "busy":
          return fail("chat.busy");
        case "error":
          return fail("chat.error");
      }
    }
    if (!started) fail("chat.error"); // stream ended without any answer
  } finally {
    setBusy(false);
    if (FINE_POINTER) input.focus();
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

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (question.length >= 3) ask(question);
});

renderSuggestions();
await typeGreeting();
composer.hidden = false;
if (FINE_POINTER) input.focus();