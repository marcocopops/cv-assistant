"""HTTP API: streams answers to the browser as Server-Sent Events."""
import asyncio
import contextlib
import json
import logging
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import config, core

log = logging.getLogger("cv_assistant")


class QueueFull(Exception):
    """Raised when too many requests are already waiting."""


class InferenceQueue:
    """Run one generation at a time and cap the number of waiting requests."""

    def __init__(self, max_waiting: int) -> None:
        self._slot = asyncio.Semaphore(1)
        self._max_waiting = max_waiting
        self.waiting = 0

    @property
    def busy(self) -> bool:
        return self._slot.locked()

    @property
    def full(self) -> bool:
        return self.waiting >= self._max_waiting

    @contextlib.asynccontextmanager
    async def turn(self):
        # Check and increment with no await in between: atomic under asyncio.
        if self.full:
            raise QueueFull
        self.waiting += 1
        try:
            await self._slot.acquire()
        finally:
            self.waiting -= 1
        try:
            yield
        finally:
            self._slot.release()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Create shared resources at startup and close them cleanly at shutdown."""
    timeout = httpx.Timeout(300, connect=5)
    async with core.make_pool() as pool, httpx.AsyncClient(timeout=timeout) as client:
        app.state.pool = pool
        app.state.client = client
        app.state.queue = InferenceQueue(config.MAX_WAITING)
        yield


app = FastAPI(title="CV assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    lang: Literal["fr", "en", "es"] = "fr"  # language selected on the website, used as fallback


def sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/ask")
async def ask(req: AskRequest, request: Request) -> StreamingResponse:
    state = request.app.state
    queue: InferenceQueue = state.queue

    async def events():
        try:
            if queue.busy and not queue.full:
                yield sse("queued", {"position": queue.waiting + 1})
            async with queue.turn():
                async for event, data in core.answer(state.pool, state.client, req.question, req.lang):
                    yield sse(event, data)
        except QueueFull:
            yield sse("busy", {"message": "The assistant is busy. Please try again in a moment."})
        except Exception:
            # Full details in the server logs, a generic message for the visitor.
            log.exception("Answer generation failed")
            yield sse("error", {"message": "The assistant is temporarily unavailable."})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Prevent caches and proxies from buffering the stream.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
async def health(request: Request) -> dict:
    """Readiness check: both the database and Ollama must respond."""
    try:
        async with request.app.state.pool.connection(timeout=3) as conn:
            await conn.execute("SELECT 1")
        resp = await request.app.state.client.get(f"{config.OLLAMA_URL}/api/version", timeout=3)
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dependency unavailable: {type(exc).__name__}")
    return {"status": "ok"}
