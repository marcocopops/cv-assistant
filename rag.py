"""Pipeline RAG minimal : indexation et recherche dans la base de connaissances."""
import sys
from pathlib import Path

import httpx
import numpy as np
import psycopg
from pgvector.psycopg import register_vector

OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


def embed(texts: list[str]) -> np.ndarray:
    """Transforme une liste de textes en vecteurs via Ollama."""
    resp = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
        timeout=300,
    )
    resp.raise_for_status()
    return np.array(resp.json()["embeddings"])


def split_markdown(path: Path) -> list[dict]:
    """Découpe un fichier Markdown : une section par titre '## '."""
    doc_title, sections = path.stem, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            doc_title = line[2:].strip()
        elif line.startswith("## "):
            sections.append({"heading": line[3:].strip(), "lines": []})
        elif sections:
            sections[-1]["lines"].append(line)

    chunks = []
    for s in sections:
        body = "\n".join(s["lines"]).strip()
        if body:
            chunks.append({
                "source": path.name,
                "heading": s["heading"],
                "content": f"{doc_title} > {s['heading']}\n\n{body}",
            })
    return chunks


def ingest() -> None:
    chunks = [c for f in sorted(KNOWLEDGE_DIR.glob("*.md")) for c in split_markdown(f)]
    if not chunks:
        sys.exit("Aucune section trouvée dans knowledge/.")
    vectors = embed([c["content"] for c in chunks])

    with psycopg.connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id        bigserial PRIMARY KEY,
                source    text NOT NULL,
                heading   text NOT NULL,
                content   text NOT NULL,
                embedding vector({EMBED_DIM}) NOT NULL
            )""")
        conn.execute("TRUNCATE chunks")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (source, heading, content, embedding) "
                "VALUES (%s, %s, %s, %s)",
                [(c["source"], c["heading"], c["content"], v)
                 for c, v in zip(chunks, vectors)],
            )
    print(f"{len(chunks)} sections indexées.")


def search(question: str, k: int = 3) -> None:
    q = embed([question])[0]
    with psycopg.connect() as conn:
        register_vector(conn)
        rows = conn.execute(
            "SELECT source, heading, 1 - (embedding <=> %s) AS score "
            "FROM chunks ORDER BY embedding <=> %s LIMIT %s",
            (q, q, k),
        ).fetchall()
    for source, heading, score in rows:
        print(f"{score:.3f}  {source} > {heading}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "ingest":
        ingest()
    elif len(sys.argv) >= 3 and sys.argv[1] == "search":
        search(" ".join(sys.argv[2:]))
    else:
        sys.exit('Usage : python rag.py ingest | python rag.py search "question"')
