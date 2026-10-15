"""Command-line interface: index the knowledge base and query it from a terminal."""
import asyncio
import sys

import httpx

from app import core


async def run_ingest() -> None:
    async with httpx.AsyncClient(timeout=300) as client:
        count = await core.ingest(client)
    print(f"{count} sections indexed.")


async def run_search(question: str) -> None:
    async with core.make_pool() as pool, httpx.AsyncClient(timeout=300) as client:
        for c in await core.retrieve(pool, client, question):
            print(f"{c.score:.3f}  {c.source} > {c.heading}")


async def run_ask(question: str) -> None:
    meta = {}
    async with core.make_pool() as pool, httpx.AsyncClient(timeout=300) as client:
        async for event, data in core.answer(pool, client, question):
            if event == "meta":
                meta = data
            elif event == "token":
                print(data["text"], end="", flush=True)
            elif event == "done":
                print(f"\n\n[lang: {meta['lang']} | sources: {', '.join(meta['sources']) or '-'}]")
                if data["llm"]:
                    print(f"[load {data['load_s']} s | "
                          f"prompt {data['prompt_tokens']} tokens in {data['prompt_s']} s | "
                          f"answer {data['answer_tokens']} tokens at {data['tokens_per_s']} tok/s]")


async def run_history(limit: int) -> None:
    async with core.make_pool() as pool, pool.connection() as conn:
        cur = await conn.execute(
            "SELECT created_at, client_ip, country, status, used_llm, top_score, question, answer "
            "FROM interactions ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        rows = await cur.fetchall()
    for created, ip, country, status, used_llm, score, question, answer in reversed(rows):
        llm = "LLM" if used_llm else "no LLM"
        score_text = f"{score:.3f}" if score is not None else "-"
        print(f"{created.astimezone():%Y-%m-%d %H:%M}  {ip}  {country or '-'}  {status}  {llm}  score {score_text}")
        print(f"  Q: {question}")
        print("  A: " + answer.replace("\n", "\n     ") + "\n")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "ingest":
        asyncio.run(run_ingest())
    elif len(sys.argv) >= 3 and sys.argv[1] == "search":
        asyncio.run(run_search(" ".join(sys.argv[2:])))
    elif len(sys.argv) >= 3 and sys.argv[1] == "ask":
        asyncio.run(run_ask(" ".join(sys.argv[2:])))
    elif len(sys.argv) >= 2 and sys.argv[1] == "history":
        asyncio.run(run_history(int(sys.argv[2]) if len(sys.argv) >= 3 else 20))
    else:
        sys.exit('Usage: python cli.py ingest | search "question" | ask "question" | history "limit"')


if __name__ == "__main__":
    main()
