"""Unit tests for api/llm_service.py — LLM service for song information."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from llm_service import LLMService, _QUERY_PROMPTS, CACHE_DIR


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


# ── All query types exist ────────────────────────────────────────────────────

@pytest.mark.parametrize("query_type", list(_QUERY_PROMPTS.keys()))
def test_all_query_types_have_prompts(query_type):
    assert query_type in _QUERY_PROMPTS
    assert "{track}" in _QUERY_PROMPTS[query_type]
    assert "{artist}" in _QUERY_PROMPTS[query_type]


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


# ── LLM call (mocked) ───────────────────────────────────────────────────────

def test_query_success_returns_content(svc):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "# Lyrics\nSome lyrics here"

    with patch.object(svc._client.chat.completions, "create", return_value=mock_response):
        result = svc.query("lyrics", artist="The Church", track="Under the Milky Way")

    assert result["ok"] is True
    assert "Lyrics" in result["content"]
    assert result["cached"] is False


def test_query_uses_cache_on_second_call(svc):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "# Facts"

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