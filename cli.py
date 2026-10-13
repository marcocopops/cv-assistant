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


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "ingest":
        asyncio.run(run_ingest())
    elif len(sys.argv) >= 3 and sys.argv[1] == "search":
        asyncio.run(run_search(" ".join(sys.argv[2:])))
    elif len(sys.argv) >= 3 and sys.argv[1] == "ask":
        asyncio.run(run_ask(" ".join(sys.argv[2:])))
    else:
        sys.exit('Usage: python cli.py ingest | search "question" | ask "question"')


if __name__ == "__main__":
    main()
