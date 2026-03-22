# API Endpoints & URLs

## External

- **HLS Stream**: `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8`
- **Metadata JSON**: `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json` (root, NOT `/hls/`)
- **iTunes Search**: `https://itunes.apple.com/search?term=...&entity=song&limit=1`

## Local API (Flask :5000, Docker :5050)

**IMPORTANT**: All API routes use the `/api` prefix.

**Ratings** (no auth):

- `GET /api/ratings` — paginated list (`?limit=100&offset=0`, max 500). No IPs exposed.
- `GET /api/ratings/summary` — likes/dislikes by station
- `GET /api/ratings/check?station=...` — check if current IP rated
- `POST /api/ratings` — submit `{ station, score }` (score 0 or 1, 409 on duplicate)

**Auth**:

- `POST /api/register` — `{ username, password }` (8-128 chars, rate-limited 5/min)
- `POST /api/login` — `{ username, password }` → `{ token, username }` (rate-limited 5/min)
- `POST /api/logout` — invalidate token (requires Bearer token)

**Profile** (requires Bearer token):

- `GET /api/profile` — get profile (nickname, email, genres, about)
- `PUT /api/profile` — update profile

**Feedback** (requires Bearer token):

- `POST /api/feedback` — submit `{ message }` (stores with profile snapshot)

**Song Info** (LLM, rate-limited 10/min):

- `POST /api/song-info` — `{ query_type, artist, track, album?, artwork_url?, language? }` → `{ ok, content }` (Markdown)
- `GET /api/song-info/health` — check Ollama + model availability

**Quiz** (LLM, rate-limited 10/min):

- `POST /api/quiz/start` — `{ artist, track, album?, language? }` → `{ ok, session_id, question, question_number, total_questions }`
- `POST /api/quiz/answer` — `{ session_id, answer }` → `{ ok, score, feedback, question?, summary? }`

**Health** (nginx only): `GET /health` → `200 "ok"`