"""Unit tests for api/llm_service.py — LLM service for song information."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from llm_service import LLMService, _QUERY_PROMPTS, CACHE_DIR, CACHE_TTL_SECONDS


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def svc(tmp_path, monkeypatch):
    """Create an LLMService with a temporary cache directory."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    # Re-import to pick up env change
    import importlib
    import llm_service
    importlib.reload(llm_service)
    return llm_service.LLMService(base_url="http://fake:11434/v1")


def _mock_llm_response(content="# Response"):
    """Helper to create a mock OpenAI chat completion response."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    return mock


# ── Query type validation ────────────────────────────────────────────────────

def test_query_rejects_unknown_type(svc):
    result = svc.query("nonexistent", artist="A", track="T")
    assert result["ok"] is False
    assert "Unknown query type" in result["error"]


def test_query_requires_artist_and_track(svc):
    result = svc.query("lyrics", artist="", track="")
    assert result["ok"] is False
    assert "required" in result["error"]


def test_query_requires_artist(svc):
    result = svc.query("lyrics", artist="", track="Song")
    assert result["ok"] is False


def test_query_requires_track(svc):
    result = svc.query("lyrics", artist="Artist", track="")
    assert result["ok"] is False


def test_query_none_artist_rejected(svc):
    """None artist should be treated as empty."""
    result = svc.query("lyrics", artist=None, track="Song")
    assert result["ok"] is False
    assert "required" in result["error"]


def test_query_none_track_rejected(svc):
    """None track should be treated as empty."""
    result = svc.query("lyrics", artist="Artist", track=None)
    assert result["ok"] is False
    assert "required" in result["error"]


# ── All query types exist ────────────────────────────────────────────────────

@pytest.mark.parametrize("query_type", list(_QUERY_PROMPTS.keys()))
def test_all_query_types_have_prompts(query_type):
    assert query_type in _QUERY_PROMPTS
    assert "{track}" in _QUERY_PROMPTS[query_type]
    assert "{artist}" in _QUERY_PROMPTS[query_type]


# ── All query types succeed with mocked LLM ──────────────────────────────────

@pytest.mark.parametrize("query_type", list(_QUERY_PROMPTS.keys()))
def test_all_query_types_return_content(svc, query_type):
    """Every known query type returns ok=True when LLM responds."""
    mock_resp = _mock_llm_response(f"# {query_type} response")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.query(query_type, artist="Artist", track="Track", album="Album")
    assert result["ok"] is True
    assert query_type in result["content"]
    assert result["cached"] is False


# ── Cache ────────────────────────────────────────────────────────────────────

def test_cache_roundtrip(svc, tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    key = svc._cache_key("lyrics", "Artist", "Track")
    assert svc._get_cached(key) is None
    svc._set_cached(key, "# Lyrics here")
    assert svc._get_cached(key) == "# Lyrics here"


def test_cache_expires(svc, tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LLM_CACHE_DIR", str(cache_dir))
    key = svc._cache_key("lyrics", "A", "T")
    # Write expired cache entry
    path = cache_dir / f"{key}.json"
    path.write_text(json.dumps({"ts": time.time() - 200000, "content": "old"}))
    assert svc._get_cached(key) is None


def test_cache_key_is_deterministic(svc):
    k1 = svc._cache_key("lyrics", "Artist", "Track")
    k2 = svc._cache_key("lyrics", "Artist", "Track")
    assert k1 == k2


def test_cache_key_varies_by_type(svc):
    k1 = svc._cache_key("lyrics", "A", "T")
    k2 = svc._cache_key("facts", "A", "T")
    assert k1 != k2


def test_cache_key_case_insensitive(svc):
    """Cache key is lowercased so 'Artist' == 'artist'."""
    k1 = svc._cache_key("lyrics", "Artist", "Track")
    k2 = svc._cache_key("lyrics", "artist", "track")
    assert k1 == k2


def test_cache_corrupt_json_returns_none(svc, tmp_path, monkeypatch):
    """Corrupted cache file should return None, not raise."""
    import importlib
    import llm_service
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService(base_url="http://fake:11434/v1")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = svc2._cache_key("lyrics", "A", "T")
    path = cache_dir / f"{key}.json"
    path.write_text("NOT VALID JSON {{{{")
    assert svc2._get_cached(key) is None


def test_cache_missing_ts_field_treated_as_expired(svc, tmp_path, monkeypatch):
    """Cache entry with missing 'ts' field should be treated as expired (ts=0)."""
    import importlib
    import llm_service
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService(base_url="http://fake:11434/v1")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = svc2._cache_key("lyrics", "A", "T")
    path = cache_dir / f"{key}.json"
    path.write_text(json.dumps({"content": "no timestamp"}))
    assert svc2._get_cached(key) is None


def test_set_cached_handles_os_error(svc):
    """_set_cached gracefully handles write failures (non-critical)."""
    with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
        # Should not raise — just silently fails
        svc._set_cached("testkey", "content")


def test_cache_hit_returns_cached_flag(svc):
    """Cached responses include cached=True."""
    mock_resp = _mock_llm_response("# Facts")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        svc.query("facts", artist="The Church", track="Under the Milky Way")
    result = svc.query("facts", artist="The Church", track="Under the Milky Way")
    assert result["ok"] is True
    assert result["cached"] is True


# ── LLM call (mocked) ───────────────────────────────────────────────────────

def test_query_success_returns_content(svc):
    mock_response = _mock_llm_response("# Lyrics\nSome lyrics here")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_response):
        result = svc.query("lyrics", artist="The Church", track="Under the Milky Way")
    assert result["ok"] is True
    assert "Lyrics" in result["content"]
    assert result["cached"] is False


def test_query_uses_cache_on_second_call(svc):
    mock_response = _mock_llm_response("# Facts")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_response):
        result1 = svc.query("facts", artist="The Church", track="Under the Milky Way")
    # Second call should use cache (no mock needed)
    result2 = svc.query("facts", artist="The Church", track="Under the Milky Way")
    assert result2["ok"] is True
    assert result2["cached"] is True


def test_query_handles_llm_error(svc):
    with patch.object(svc._client.chat.completions, "create", side_effect=Exception("Connection refused")):
        result = svc.query("lyrics", artist="A", track="T")
    assert result["ok"] is False
    assert "Connection refused" in result["error"]


def test_query_with_artwork_url(svc):
    """artwork_url is appended to the user message."""
    mock_resp = _mock_llm_response("# Details")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.query(
            "details", artist="A", track="T", album="Album",
            artwork_url="https://example.com/art.jpg",
        )
    # Verify artwork URL was included in the user message
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    user_msg = messages[1]["content"]
    assert "https://example.com/art.jpg" in user_msg


def test_query_without_artwork_url(svc):
    """When no artwork_url, the album cover line is not appended."""
    mock_resp = _mock_llm_response("# Details")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.query("details", artist="A", track="T")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    user_msg = messages[1]["content"]
    assert "Album cover:" not in user_msg


def test_query_default_album_unknown(svc):
    """When album is empty, 'Unknown' is used in the prompt."""
    mock_resp = _mock_llm_response("# Facts")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.query("facts", artist="A", track="T", album="")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    user_msg = messages[1]["content"]
    assert "Unknown" in user_msg


def test_query_with_album(svc):
    """When album is provided, it appears in the prompt."""
    mock_resp = _mock_llm_response("# Facts")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.query("facts", artist="A", track="T", album="Starfish")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    user_msg = messages[1]["content"]
    assert "Starfish" in user_msg


def test_query_very_long_content(svc):
    """LLM returning very long content should still work."""
    long_content = "# Lyrics\n" + "La la la\n" * 500
    mock_resp = _mock_llm_response(long_content)
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.query("lyrics", artist="A", track="T")
    assert result["ok"] is True
    assert len(result["content"]) > 1000


# ── Language parameter ───────────────────────────────────────────────────────

def test_query_with_language_param(svc):
    """Explicit language parameter overrides the default."""
    mock_resp = _mock_llm_response("# Letras")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.query("lyrics", artist="A", track="T", language="Portuguese")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    system_msg = messages[0]["content"]
    assert "Portuguese" in system_msg


def test_query_uses_default_language(svc):
    """When no language passed, uses the service default (English)."""
    mock_resp = _mock_llm_response("# Content")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.query("lyrics", artist="A", track="T")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    system_msg = messages[0]["content"]
    assert "English" in system_msg


def test_service_custom_language(tmp_path, monkeypatch):
    """LLMService instantiated with a custom default language."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    import importlib
    import llm_service
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService(base_url="http://fake:11434/v1", language="Spanish")
    mock_resp = _mock_llm_response("# Datos")
    with patch.object(svc2._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc2.query("facts", artist="A", track="T")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    system_msg = messages[0]["content"]
    assert "Spanish" in system_msg


# ── Host/GPU fallback (_ensure_connection) ───────────────────────────────────

def test_ensure_connection_success_on_first_try(svc):
    """Primary URL works — no fallback needed."""
    with patch.object(svc._client.models, "list"):
        svc._ensure_connection()
    assert svc._resolved is True


def test_ensure_connection_skips_if_already_resolved(svc):
    """Once resolved, _ensure_connection is a no-op."""
    svc._resolved = True
    # Should not call models.list at all
    with patch.object(svc._client.models, "list", side_effect=Exception("should not be called")) as m:
        svc._ensure_connection()
    m.assert_not_called()


def test_ensure_connection_fallback_on_primary_failure(tmp_path, monkeypatch):
    """When primary fails and fallback is set, switch to fallback URL."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("OLLAMA_FALLBACK_URL", "http://host.docker.internal:11434/v1")
    import importlib
    import llm_service
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService(base_url="http://fake:11434/v1")
    with patch.object(svc2._client.models, "list", side_effect=Exception("primary down")):
        svc2._ensure_connection()
    assert svc2.base_url == "http://host.docker.internal:11434/v1"
    assert svc2._resolved is True


def test_ensure_connection_no_fallback_still_resolves(svc):
    """When primary fails and no fallback URL, still mark resolved."""
    svc._fallback_url = ""
    with patch.object(svc._client.models, "list", side_effect=Exception("down")):
        svc._ensure_connection()
    assert svc._resolved is True


def test_ensure_connection_fallback_same_as_primary(tmp_path, monkeypatch):
    """Fallback URL same as primary should not trigger switch."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("OLLAMA_FALLBACK_URL", "http://fake:11434/v1")
    import importlib
    import llm_service
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService(base_url="http://fake:11434/v1")
    original_url = svc2.base_url
    with patch.object(svc2._client.models, "list", side_effect=Exception("down")):
        svc2._ensure_connection()
    # Stays resolved, URL unchanged (fallback == primary)
    assert svc2._resolved is True
    assert svc2.base_url == original_url


# ── Quiz: generate_quiz ─────────────────────────────────────────────────────

def test_generate_quiz_success(svc):
    """generate_quiz returns parsed questions list on valid JSON response."""
    quiz_json = json.dumps({
        "questions": [
            {
                "q": "What year was this released?",
                "options": ["A) 1986", "B) 1988", "C) 1990", "D) 1992"],
                "answer": "B",
                "fun_fact": "It was 1988!"
            }
        ]
    })
    mock_resp = _mock_llm_response(quiz_json)
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.generate_quiz(artist="The Church", track="Under the Milky Way", album="Starfish")
    assert result["ok"] is True
    assert len(result["questions"]) == 1
    assert result["questions"][0]["answer"] == "B"


def test_generate_quiz_with_markdown_code_block(svc):
    """generate_quiz extracts JSON from markdown code blocks."""
    raw = '```json\n{"questions": [{"q": "Q?", "options": ["A","B","C","D"], "answer": "A", "fun_fact": "!"}]}\n```'
    mock_resp = _mock_llm_response(raw)
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.generate_quiz(artist="A", track="T")
    assert result["ok"] is True
    assert len(result["questions"]) == 1


def test_generate_quiz_with_plain_code_block(svc):
    """generate_quiz handles code blocks without 'json' prefix."""
    raw = '```\n{"questions": [{"q": "Q?", "options": ["A","B","C","D"], "answer": "C", "fun_fact": "!"}]}\n```'
    mock_resp = _mock_llm_response(raw)
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.generate_quiz(artist="A", track="T")
    assert result["ok"] is True
    assert result["questions"][0]["answer"] == "C"


def test_generate_quiz_invalid_json(svc):
    """generate_quiz returns error on malformed JSON response."""
    mock_resp = _mock_llm_response("This is not JSON at all")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.generate_quiz(artist="A", track="T")
    assert result["ok"] is False
    assert "error" in result


def test_generate_quiz_llm_exception(svc):
    """generate_quiz returns error when LLM is unreachable."""
    with patch.object(svc._client.chat.completions, "create", side_effect=Exception("Timeout")):
        result = svc.generate_quiz(artist="A", track="T")
    assert result["ok"] is False
    assert "Timeout" in result["error"]


def test_generate_quiz_empty_questions(svc):
    """generate_quiz handles response with empty questions list."""
    mock_resp = _mock_llm_response(json.dumps({"questions": []}))
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.generate_quiz(artist="A", track="T")
    assert result["ok"] is True
    assert result["questions"] == []


def test_generate_quiz_missing_questions_key(svc):
    """generate_quiz handles response with missing 'questions' key."""
    mock_resp = _mock_llm_response(json.dumps({"data": "no questions key"}))
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.generate_quiz(artist="A", track="T")
    assert result["ok"] is True
    assert result["questions"] == []


def test_generate_quiz_with_language(svc):
    """generate_quiz passes language to system prompt."""
    mock_resp = _mock_llm_response(json.dumps({"questions": []}))
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.generate_quiz(artist="A", track="T", language="French")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    system_msg = messages[0]["content"]
    assert "French" in system_msg


def test_generate_quiz_default_album_unknown(svc):
    """When album is empty, 'Unknown' is used in the quiz prompt."""
    mock_resp = _mock_llm_response(json.dumps({"questions": []}))
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp) as mock_create:
        svc.generate_quiz(artist="A", track="T", album="")
    call_args = mock_create.call_args
    messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
    user_msg = messages[1]["content"]
    assert "Unknown" in user_msg


# ── Quiz: evaluate_answer ────────────────────────────────────────────────────

def test_evaluate_answer_success(svc):
    """evaluate_answer returns score and reaction on valid JSON."""
    eval_json = json.dumps({
        "score": 5,
        "reaction": "Nailed it!",
        "correct_answer": "B) 1988"
    })
    mock_resp = _mock_llm_response(eval_json)
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.evaluate_answer(
            question="What year?", correct="B", user_answer="B",
            options=["A) 1986", "B) 1988", "C) 1990", "D) 1992"]
        )
    assert result["ok"] is True
    assert result["score"] == 5
    assert "Nailed it!" in result["reaction"]


def test_evaluate_answer_with_code_block(svc):
    """evaluate_answer extracts JSON from markdown code blocks."""
    raw = '```json\n{"score": -3, "reaction": "Ouch!", "correct_answer": "A"}\n```'
    mock_resp = _mock_llm_response(raw)
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.evaluate_answer(
            question="Q?", correct="A", user_answer="D", options=["A","B","C","D"]
        )
    assert result["ok"] is True
    assert result["score"] == -3


def test_evaluate_answer_invalid_json(svc):
    """evaluate_answer returns fallback on malformed JSON."""
    mock_resp = _mock_llm_response("Not JSON")
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.evaluate_answer(
            question="Q?", correct="A", user_answer="B", options=["A","B","C","D"]
        )
    assert result["ok"] is False
    assert result["score"] == 0
    assert "draw" in result["reaction"]


def test_evaluate_answer_llm_exception(svc):
    """evaluate_answer returns fallback on LLM error."""
    with patch.object(svc._client.chat.completions, "create", side_effect=Exception("Timeout")):
        result = svc.evaluate_answer(
            question="Q?", correct="A", user_answer="B", options=["A","B","C","D"]
        )
    assert result["ok"] is False
    assert result["score"] == 0
    assert "error" in result


def test_evaluate_answer_negative_score(svc):
    """evaluate_answer handles negative scores."""
    eval_json = json.dumps({
        "score": -5,
        "reaction": "Hilariously wrong!",
        "correct_answer": "The answer was C"
    })
    mock_resp = _mock_llm_response(eval_json)
    with patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        result = svc.evaluate_answer(
            question="Q?", correct="C", user_answer="A", options=[]
        )
    assert result["ok"] is True
    assert result["score"] == -5


# ── Health check ─────────────────────────────────────────────────────────────

def test_health_ok(svc):
    mock_models = MagicMock()
    mock_models.data = [MagicMock(id="llama3.2"), MagicMock(id="mistral")]
    with patch.object(svc._client.models, "list", return_value=mock_models):
        h = svc.health()
    assert h["ok"] is True
    assert h["ollama"] is True
    assert h["model_available"] is True


def test_health_model_missing(svc):
    mock_models = MagicMock()
    mock_models.data = [MagicMock(id="mistral")]
    with patch.object(svc._client.models, "list", return_value=mock_models):
        h = svc.health()
    assert h["ok"] is False
    assert h["model_available"] is False


def test_health_ollama_down(svc):
    with patch.object(svc._client.models, "list", side_effect=Exception("Connection refused")):
        h = svc.health()
    assert h["ok"] is False
    assert h["ollama"] is False


def test_health_model_with_latest_tag(svc):
    """Model listed as 'llama3.2:latest' should match 'llama3.2'."""
    mock_models = MagicMock()
    mock_models.data = [MagicMock(id="llama3.2:latest")]
    with patch.object(svc._client.models, "list", return_value=mock_models):
        h = svc.health()
    assert h["ok"] is True
    assert h["model_available"] is True


def test_health_returns_model_list(svc):
    """Health response includes the list of available model IDs."""
    mock_models = MagicMock()
    mock_models.data = [MagicMock(id="llama3.2"), MagicMock(id="codellama")]
    with patch.object(svc._client.models, "list", return_value=mock_models):
        h = svc.health()
    assert "llama3.2" in h["models"]
    assert "codellama" in h["models"]
    assert h["model"] == "llama3.2"


def test_health_error_includes_message(svc):
    """Health error response includes the exception message."""
    with patch.object(svc._client.models, "list", side_effect=Exception("host unreachable")):
        h = svc.health()
    assert h["ok"] is False
    assert "host unreachable" in h["error"]


def test_health_no_models(svc):
    """Ollama running but no models pulled."""
    mock_models = MagicMock()
    mock_models.data = []
    with patch.object(svc._client.models, "list", return_value=mock_models):
        h = svc.health()
    assert h["ok"] is False
    assert h["ollama"] is True
    assert h["model_available"] is False
    assert h["models"] == []


# ── Constructor / environment ────────────────────────────────────────────────

def test_default_base_url(tmp_path, monkeypatch):
    """Default base_url from env or localhost."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    import importlib
    import llm_service
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService()
    assert svc2.base_url == "http://localhost:11434/v1"


def test_custom_base_url_from_env(tmp_path, monkeypatch):
    """OLLAMA_BASE_URL env var overrides default."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:11434/v1")
    import importlib
    import llm_service
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService()
    assert svc2.base_url == "http://custom:11434/v1"


def test_custom_model_from_env(tmp_path, monkeypatch):
    """OLLAMA_MODEL env var overrides default model."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    import importlib
    import llm_service
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService()
    assert svc2.model == "mistral"


def test_constructor_explicit_params(tmp_path, monkeypatch):
    """Explicit constructor params take priority over env vars."""
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "cache"))
    import importlib
    import llm_service
    importlib.reload(llm_service)
    svc2 = llm_service.LLMService(
        base_url="http://myhost:1234/v1",
        model="phi3",
        language="German",
        timeout=60.0,
    )
    assert svc2.base_url == "http://myhost:1234/v1"
    assert svc2.model == "phi3"
    assert svc2.language == "German"
    assert svc2.timeout == 60.0


# ── Edge cases ───────────────────────────────────────────────────────────────

def test_query_ensure_connection_called(svc):
    """query() calls _ensure_connection before processing."""
    mock_resp = _mock_llm_response("# Content")
    with patch.object(svc, "_ensure_connection") as mock_ensure, \
         patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        svc.query("lyrics", artist="A", track="T")
    mock_ensure.assert_called_once()


def test_generate_quiz_ensure_connection_called(svc):
    """generate_quiz() calls _ensure_connection."""
    mock_resp = _mock_llm_response(json.dumps({"questions": []}))
    with patch.object(svc, "_ensure_connection") as mock_ensure, \
         patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        svc.generate_quiz(artist="A", track="T")
    mock_ensure.assert_called_once()


def test_evaluate_answer_ensure_connection_called(svc):
    """evaluate_answer() calls _ensure_connection."""
    mock_resp = _mock_llm_response(json.dumps({"score": 3, "reaction": "Ok", "correct_answer": "A"}))
    with patch.object(svc, "_ensure_connection") as mock_ensure, \
         patch.object(svc._client.chat.completions, "create", return_value=mock_resp):
        svc.evaluate_answer("Q?", "A", "A", [])
    mock_ensure.assert_called_once()


def test_health_ensure_connection_called(svc):
    """health() calls _ensure_connection."""
    mock_models = MagicMock()
    mock_models.data = []
    with patch.object(svc, "_ensure_connection") as mock_ensure, \
         patch.object(svc._client.models, "list", return_value=mock_models):
        svc.health()
    mock_ensure.assert_called_once()
