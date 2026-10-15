"""Runtime configuration, read from environment variables."""
import os
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
EMBED_DIM = 1024  # must match EMBED_MODEL's output size
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.1:8b")

KNOWLEDGE_DIR = Path(os.environ.get("KNOWLEDGE_DIR", Path(__file__).parent.parent / "knowledge"))

TOP_K = 3
SCORE_THRESHOLD = float(os.environ.get("SCORE_THRESHOLD", "0.40"))  # calibrated on knowledge/evals.toml
MAX_WAITING = int(os.environ.get("MAX_WAITING", "5"))
ALLOWED_ORIGINS = [o for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o]
TRUSTED_PROXY = os.environ.get("TRUSTED_PROXY", "")  # cloudflared's address on the edge network