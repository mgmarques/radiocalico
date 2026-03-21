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

# ── LLM generation parameters ────────────────────────────────────────────────
_MAX_TOKENS = 800  # keep responses concise and fast
_TEMPERATURE = 0.5  # lower = faster + more focused
_QUIZ_MAX_TOKENS = 600  # quizzes need less text
_EVAL_MAX_TOKENS = 150  # evaluations are short

# ── Prompt templates per query type ──────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a concise music expert. Respond ONLY in Markdown. No preamble. Be brief and informative.
IMPORTANT: NEVER translate song titles, album names, or artist names. Always keep them in their original language, even when responding in another language.\
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
        self._fallback_url = os.environ.get("OLLAMA_FALLBACK_URL", "")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")
        self.language = language
        self.timeout = timeout
        self._client = self._make_client(self.base_url)
        self._resolved = False  # True once we've confirmed which URL works
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _make_client(self, url: str) -> OpenAI:
        api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
        return OpenAI(base_url=url, api_key=api_key, timeout=self.timeout)

    def _ensure_connection(self) -> None:
        """On first call, probe the primary URL. If it fails, switch to fallback."""
        if self._resolved:
            return
        try:
            self._client.models.list()
            logger.info("ollama_connected", extra={"url": self.base_url})
            self._resolved = True
        except Exception:
            if self._fallback_url and self._fallback_url != self.base_url:
                logger.warning(
                    "ollama_primary_failed_trying_fallback",
                    extra={"primary": self.base_url, "fallback": self._fallback_url},
                )
                self.base_url = self._fallback_url
                self._client = self._make_client(self.base_url)
                self._resolved = True
            else:
                self._resolved = True  # no fallback, just let it fail normally

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
        self._ensure_connection()
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
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
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

    # ── Quiz ─────────────────────────────────────────────────────────────────

    _QUIZ_SYSTEM = """\
You are a sarcastic but lovable music quiz master for Radio Calico.
You are good-humored and can be sarcastic, but NEVER rude or mean.
You ask trivia questions about songs, albums, and artists.

RULES:
- Generate exactly 5 multiple-choice questions (A/B/C/D) about the song, artist, and album.
- Return ONLY valid JSON — no markdown, no explanation.
- Format: {{"questions": [{{"q": "question text", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "A", "fun_fact": "short fun fact about the answer"}}]}}
- Make questions progressively harder.
- Mix topics: lyrics, album year, band members, genre, chart position, cultural trivia.
- NEVER translate song titles, album names, or artist names — always keep them in their original language.\
"""

    _EVAL_SYSTEM = """\
You are a sarcastic but lovable quiz evaluator for Radio Calico.
You score how close a user's answer is to the correct answer.

RULES:
- Return ONLY valid JSON.
- Score from -5 to 5: 5 = perfect, 3-4 = close, 1-2 = partially right, 0 = irrelevant, -1 to -5 = hilariously wrong.
- Be funny in your reaction. Sarcastic but never rude.
- Format: {{"score": N, "reaction": "your funny reaction", "correct_answer": "the right answer explanation"}}\
"""

    def generate_quiz(self, artist: str, track: str, album: str = "", language: str = "English") -> dict:
        """Generate 5 quiz questions about a song. Returns JSON with questions list."""
        self._ensure_connection()
        try:
            system = self._QUIZ_SYSTEM + f"\nRespond in {language}."
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": (
                            f"Generate a 5-question music trivia quiz about "
                            f'"{track}" by {artist} (album: "{album or "Unknown"}").'
                        ),
                    },
                ],
                max_tokens=_QUIZ_MAX_TOKENS,
                temperature=0.7,
            )
            raw = response.choices[0].message.content
            # Extract JSON from response (handle markdown code blocks)
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return {"ok": True, "questions": data.get("questions", [])}
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("quiz_generate_error", extra={"error": str(exc)})
            return {"ok": False, "error": str(exc)}

    def evaluate_answer(self, question: str, correct: str, user_answer: str, options: list) -> dict:
        """Evaluate a user's quiz answer. Returns score and reaction."""
        self._ensure_connection()
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._EVAL_SYSTEM},
                    {
                        "role": "user",
                        "content": (f"Q: {question}\nCorrect: {correct}\nUser: {user_answer}\nScore it."),
                    },
                ],
                max_tokens=_EVAL_MAX_TOKENS,
                temperature=0.5,
            )
            raw = response.choices[0].message.content
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return {"ok": True, **data}
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("quiz_eval_error", extra={"error": str(exc)})
            return {
                "ok": False,
                "score": 0,
                "reaction": "Hmm, I crashed trying to judge you. Let's call it a draw.",
                "error": str(exc),
            }

    # ── Health check ─────────────────────────────────────────────────────────

    def health(self) -> dict:
        """Check if Ollama is reachable and the model is available."""
        self._ensure_connection()
        try:
            models = self._client.models.list()
            model_ids = [m.id for m in models.data]
            available = self.model in model_ids or f"{self.model}:latest" in model_ids
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
