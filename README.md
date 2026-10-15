# CV assistant

A self-hosted AI assistant that answers recruiters' questions about my background,
running on a home server. Personal project: the assistant can make mistakes.

## Architecture

```
Browser ──► Cloudflare: static site, WAF, rate limiting
                 │
                 └── Cloudflare Tunnel (outbound connection only, no open port)
                          │
                     Home server
                     ├── API: FastAPI, Server-Sent Events, bounded inference queue
                     ├── PostgreSQL + pgvector: knowledge base and interaction log
                     └── Ollama: bge-m3 embeddings, Llama 3.1 8B
```

## How it works

- **RAG**: the knowledge base is split by Markdown section, embedded with bge-m3,
  and retrieved by cosine similarity with pgvector.
- **Relevance threshold**: off-topic questions are answered without calling the LLM.
- **Multilingual** (French, English, Spanish): the question language is detected in code
  and given to the model as an explicit instruction.
- **Streaming**: answers are sent token by token as Server-Sent Events.
- **Evaluation harness**: deterministic decoding, test cases checking retrieved sections,
  expected and forbidden terms and answer language, plus a threshold calibration report.
  Deployment only happens when every evaluation passes.

## Security

- No inbound port: the API is only reachable through an outbound Cloudflare Tunnel,
  and only the `/ask` route is published.
- Network segmentation between containers.
- Hardened API container: non-root user, read-only filesystem, no Linux capabilities,
  memory and CPU limits.
- Input validation, edge rate limiting, strict Content Security Policy,
  model output always rendered as text.

## Run locally

Requirements: Docker, Python 3.13, and an Ollama instance with `bge-m3` and `llama3.1:8b`.
The Compose file expects two external Docker networks, `llm` and `edge`, shared with
the Ollama and Cloudflare Tunnel containers.

```bash
cp .env.example .env              # then set a password
cp -r knowledge.example knowledge
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
docker compose up -d --wait
make ingest
```

Evaluation cases for the real knowledge base are private. Write your own in
`knowledge/evals.toml` (format documented in `evals/run.py`), then run `make check`.

## Licence

MIT