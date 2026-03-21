"""LLM Service — wraps Ollama (OpenAI-compatible API) for song information.

Provides structured song detail queries (lyrics, facts, merchandise, jokes,
details, everything) by sending prompts to a local Ollama instance running
Llama 3.2.  Falls back gracefully when Ollama is unavailable.

Usage:
    from llm_service import LLMService
    svc = LLMService()
    result = svc.query("lyrics", artist="The Church", track="Under the Milky Way",
                       album="Starfish", artwork_url="https://...")
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger("radiocalico.llm")

# ── Cache directory ──────────────────────────────────────────────────────────
CACHE_DIR = Path(os.environ.get("LLM_CACHE_DIR", "/tmp/radiocalico-llm-cache"))
CACHE_TTL_SECONDS = int(os.environ.get("LLM_CACHE_TTL", 86400))  # 24 h

# ── Prompt templates per query type ──────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a music enthusiast who adapts language to the genre of the music.
Extract all metadata from the song details provided (artist, track, album, artwork URL).
Respond ONLY with well-formatted Markdown.  Do not include any preamble or explanation.\
"""

_QUERY_PROMPTS = {
    "lyrics": (
        'Give me the complete lyrics for "{track}" by {artist}.\n'
        "If you are not confident about the exact lyrics, say so clearly."
    ),
    "details": (
        'Give detailed information about "{track}" by {artist} from the album "{album}".\n'
        "Include: song meaning/story, genre, year, record label, producers, "
        "and a table of the full album tracklist with durations."
    ),
    "facts": (
        'Give interesting facts about "{track}" by {artist} (album: "{album}").\n'
        "Include facts about the song, the album, and the artist(s). "
        "Mention chart positions, awards, covers, or cultural impact if relevant."
    ),
    "merchandise": (
        'Suggest merchandise ideas for fans of "{track}" by {artist} (album: "{album}").\n'
        "Include a Radio Calico Nerd Shirt concept featuring the album cover "
        "and song name.  List other products (vinyl, poster, mug, etc.)."
    ),
    "jokes": (
        'Tell funny jokes about "{track}" by {artist}.\n'
        "Include a joke about a robot listening to this song. "
        "End with a funny closing note in a random language."
    ),
    "everything": (
        'Give me EVERYTHING about "{track}" by {artist} (album: "{album}").\n'
        "Include: song meaning, full lyrics, interesting facts about the song/album/artists, "
        "a table of the album tracklist with durations, merchandise ideas "
        "(including a Radio Calico Nerd Shirt with the album cover), "
        "a robot joke about this song, and a funny closing note in another language."
    ),
}


class LLMService:
    """Wraps Ollama's OpenAI-compatible API for song information queries."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        language: str = "English",
        timeout: float = 120.0,
    ):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")
        self.language = language
        self.timeout = timeout
        self._client = OpenAI(
            base_url=self.base_url,
            api_key="ollama",  # placeholder — Ollama ignores it
            timeout=self.timeout,
        )
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Cache helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(query_type: str, artist: str, track: str) -> str:
        raw = f"{query_type}:{artist}:{track}".lower()
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def _get_cached(self, key: str) -> str | None:
        path = CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("ts", 0) > CACHE_TTL_SECONDS:
                path.unlink(missing_ok=True)
                return None
            return data.get("content")
        except (json.JSONDecodeError, OSError):
            return None

    def _set_cached(self, key: str, content: str) -> None:
        path = CACHE_DIR / f"{key}.json"
        try:
            path.write_text(
                json.dumps({"ts": time.time(), "content": content}),
                encoding="utf-8",
            )
        except OSError:
            pass  # non-critical

    # ── Core query ───────────────────────────────────────────────────────────

    def query(
        self,
        query_type: str,
        artist: str,
        track: str,
        album: str = "",
        artwork_url: str = "",
        language: str | None = None,
    ) -> dict:
        """Query the LLM for song information.

        Returns ``{"ok": True, "content": "markdown..."}`` on success,
        or ``{"ok": False, "error": "message"}`` on failure.
        """
        if query_type not in _QUERY_PROMPTS:
            return {"ok": False, "error": f"Unknown query type: {query_type}"}

        if not artist or not track:
            return {"ok": False, "error": "artist and track are required"}

        # Check cache
        cache_key = self._cache_key(query_type, artist, track)
        cached = self._get_cached(cache_key)
        if cached:
            logger.info("llm_cache_hit", extra={"query_type": query_type, "artist": artist, "track": track})
            return {"ok": True, "content": cached, "cached": True}

        # Build messages
        lang = language or self.language
        system_msg = _SYSTEM_PROMPT + f"\nRespond in {lang}."
        user_msg = _QUERY_PROMPTS[query_type].format(artist=artist, track=track, album=album or "Unknown")
        if artwork_url:
            user_msg += f"\n\nAlbum cover: {artwork_url}"

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            content = response.choices[0].message.content
            self._set_cached(cache_key, content)
            logger.info(
                "llm_query_ok",
                extra={"query_type": query_type, "artist": artist, "track": track, "model": self.model},
            )
            return {"ok": True, "content": content, "cached": False}
        except Exception as exc:
            logger.error(
                "llm_query_error",
                extra={"query_type": query_type, "error": str(exc)},
            )
            return {"ok": False, "error": str(exc)}

    # ── Health check ─────────────────────────────────────────────────────────

    def health(self) -> dict:
        """Check if Ollama is reachable and the model is available."""
        try:
            models = self._client.models.list()
            model_ids = [m.id for m in models.data]
            available = self.model in model_ids
            return {
                "ok": available,
                "ollama": True,
                "model": self.model,
                "model_available": available,
                "models": model_ids,
            }
        except Exception as exc:
            return {
                "ok": False,
                "ollama": False,
                "model": self.model,
                "error": str(exc),
            }
