# LLM Integration

## Architecture

- **Backend**: `api/llm_service.py` — `LLMService` class wrapping OpenAI SDK (compatible with Ollama)
- **Model**: Llama 3.2 via Ollama
- **Host GPU fallback**: `OLLAMA_BASE_URL` (host Metal GPU) → `OLLAMA_FALLBACK_URL` (Docker CPU)
- **Endpoint**: `POST /api/song-info` — `{ query_type, artist, track, album?, artwork_url?, language? }` → `{ ok, content }`
- **Health**: `GET /api/song-info/health` — check Ollama + model availability

## Query Types

| Type | Purpose | max_tokens |
|------|---------|------------|
| `lyrics` | Song lyrics or lyric summary | 1000 |
| `details` | Song background, recording details | 500 |
| `facts` | Fun facts about the song/artist | 500 |
| `merchandise` | Where to buy merch, albums, tickets | 500 |
| `jokes` | Music-related jokes about the song/artist | 500 |
| `everything` | Combined: lyrics + details + facts | 1500 |
| `quiz` | 5 trivia questions about the song/artist | 800 |

## Response Cache

- **TTL**: 24 hours
- **Key**: `(query_type, artist, track, language)`
- **Storage**: In-memory dict with timestamp, stored as JSON
- Prevents redundant LLM calls for the same song/query/language combination

## System Prompts

- Each query type has a tailored system prompt in `LLMService`
- All prompts MUST include: "NEVER translate song titles, album names, or artist names — keep them in their original language"
- Language parameter appended: "Respond in {language}"
- `max_tokens` limits per query type keep responses concise

## Quiz

- 5 multiple-choice questions per quiz
- Scoring: -5 to +5 (correct = +1, wrong = -1)
- Sarcastic/witty tone in responses
- Chat-style UI in frontend (`quiz-chat` container)
- Endpoints: `POST /api/quiz/start`, `POST /api/quiz/answer`

## Docker Integration

- Ollama runs as a Docker service in `docker-compose.yml`
- Healthcheck: `ollama list` (verifies Ollama is running and responsive)
- `start_period: 30s` — allows time for model loading
- Model auto-pull on first request if not present
- **CI skips Ollama**: `docker compose --profile prod up --build -d db app nginx` (no `ollama` service)

## GPU Fallback Strategy

- **Primary** (`OLLAMA_BASE_URL`): `http://host.docker.internal:11434` — host macOS Metal GPU (fast)
- **Fallback** (`OLLAMA_FALLBACK_URL`): `http://ollama:11434` — Docker CPU container (5-10x slower on macOS)
- `LLMService` tries primary first, falls back on connection error
- Docker Ollama is CPU-only on macOS (no GPU passthrough) — significantly slower

## Rate Limiting

- `POST /api/song-info`: 10 requests/minute
- `POST /api/quiz/*`: 10 requests/minute
- Rate limiting via `flask-limiter`

## Key Files

- `api/llm_service.py` — `LLMService` class, system prompts, cache, GPU fallback
- `api/app.py` — `/api/song-info`, `/api/quiz/*` route handlers
- `static/js/player.js` — `handleRetroButton()`, `fetchSongInfo()`, quiz UI
- `docker-compose.yml` — Ollama service definition
- `tests/test_llm_service.py` — LLM unit tests (mocked OpenAI SDK)