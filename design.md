# Radio Calico - Design Document

## 1. Overview

Radio Calico is a web-based live audio streaming player featuring real-time metadata display, album artwork fetching, user ratings, and track history. It combines a vanilla JavaScript frontend with a Python Flask backend API that serves both the static frontend and the ratings REST API from a single port (5000).

**Key value proposition**: Ad-free, data-free, subscription-free lossless audio streaming (24-bit / 48 kHz).

---

## 2. System Architecture

### 2.1 High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          CONTENT LAYER                                 │
│                                                                        │
│   ┌───────────────┐     ┌──────────────────┐     ┌──────────────────┐  │
│   │ Audio Source  │────▶│ HLS Encoder      │────▶│ AWS CloudFront   │  │
│   │ (Radio Feed)  │     │ (+ ID3 metadata) │     │ CDN              │  │
│   └───────────────┘     └──────────────────┘     └────────┬─────────┘  │
│                                                           ▼            │
|                                                  ┌───────────────┐     |
│                                                  │metadatav2.json│     │
│                                                  │(track info)   │     │
│                                                  └────────┬──────┘     │
└───────────────────────────────────────────────────────────┼────────────┘
                                                            │
                                    HLS manifest + TS segments + JSON metadata (HTTPS)
                                                            │
┌───────────────────────────────────────────────────────────┼────────-───┐
│                      PRESENTATION LAYER                   │            │
│                                                           ▼            │
│   ┌──────────────────────────────────────────────────────────────┐     │
│   │                    Web Browser                               │     │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │     │
│   │  │ HLS.js      │  │ player.js   │  │ index.html +        │   │     │
│   │  │ (streaming) │─▶│ (logic)     │─▶│ player.css (UI)     │   │     │
│   │  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘   │     │
│   │         │                │                                   │     │
│   │         │ ID3 frames     │ artwork query    │ metadata fetch │     │
│   │         ▼                ▼                   ▼               │     │
│   │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐      │     │
│   │  │ Metadata    │  │ iTunes API  │  │ metadatav2.json  │      │     │
│   │  │ Parser      │  │ (artwork +  │  │ (CloudFront,     │      │     │
│   │  │ (fallback)  │  │  duration)  │  │  primary source) │      │     │
│   │  └─────────────┘  └─────────────┘  └──────────────────┘      │     │
│   └──────────────────────────────────────────────────────────────┘     │
│                            │                                           │
└────────────────────────────┼───────────────────────────────────────────┘
                             │ POST /api/ratings
                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                                  │
│                                                                       │
│   ┌──────────────────────┐      ┌─────────────────────-─┐             │
│   │  Flask API           │      │  MySQL Database       │             │
│   │  (api/app.py)        │─────▶│  (radiocalico)        │             │
│   │  Port 5000           │      │  Port 3306            │             │
│   └──────────────────────┘      └──────────────────-────┘             │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND                              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ index.html                                           │   │
│  │ ┌──────────┐ ┌──────────────┐ ┌───────────────────┐  │   │
│  │ │ Navbar   │ │ Now Playing  │ │ Previous Tracks   │  │   │
│  │ │          │ │ ┌──────────┐ │ │                   │  │   │
│  │ │ Logo +   │ │ │ Artwork  │ │ │ Track history     │  │   │
│  │ │ Wordmark │ │ │ (480px)  │ │ │ (last 8 songs)    │  │   │
│  │ │          │ │ ├──────────┤ │ │                   │  │   │
│  │ │          │ │ │ Metadata │ │ │                   │  │   │
│  │ │          │ │ │ Rating   │ │ │                   │  │   │
│  │ │          │ │ │ Controls │ │ │                   │  │   │
│  │ │          │ │ └──────────┘ │ │                   │  │   │
│  │ └──────────┘ └──────────────┘ └───────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ player.js    │  │ player.css   │  │ HLS.js (CDN)     │   │
│  │              │  │              │  │                  │   │
│  │ • HLS init   │  │ • Layout     │  │ • Stream decode  │   │
│  │ • ID3 parse  │  │ • Colors     │  │ • Adaptive rate  │   │
│  │ • Playback   │  │ • Typography │  │ • ID3 extraction │   │
│  │ • Artwork    │  │ • Responsive │  │ • Error recovery │   │
│  │ • Ratings    │  │ • Animation  │  │                  │   │
│  │ • History    │  │              │  │                  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       BACKEND                               │
│                                                             │
│  ┌──────────────────────────────────────────────-┐          │
│  │ Flask API (api/app.py) — serves static + API  │          │
│  │                                               │          │
│  │  GET  /              → index.html             │          │
│  │  GET  /api/ratings   → All ratings            │          │
│  │  GET  /api/ratings/summary → Likes/dislikes   │          │
│  │  GET  /api/ratings/check   → IP rated check   │          │
│  │  POST /api/ratings   → Insert rating          │          │
│  │                         (409 on duplicate)    │          │
│  │                                               │          │
│  │  Dependencies: flask, flask-cors, pymysql     │          │
│  └─────────────────────┬────────────────────────┘           │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────-─┐          │
│  │ MySQL 5.7 (radiocalico database)              │          │
│  │                                               │          │
│  │  ratings table                                │          │
│  │  ├─ id         INT AUTO_INCREMENT PRIMARY KEY │          │
│  │  ├─ station    VARCHAR(255) (artist - title)  │          │
│  │  ├─ score      TINYINT     (0 = down, 1 = up) │          │
│  │  ├─ ip         VARCHAR(45) (voter IP address) │          │
│  │  ├─ created_at TIMESTAMP   (auto)             │          │
│  │  └─ UNIQUE KEY (station, ip) — dedup votes    │          │
│  └───────────────────────────────────────────-───┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow Diagrams

### 3.1 Audio Playback & Metadata Flow

```text
Page Load (before play)
       │
       ▼
fetchMetadata() ─────────────▶ CloudFront /metadatav2.json
       │                              │
       │                    ┌─────────┴──────────────────┐
       │                    │ { artist, title, album,    │
       │                    │   prev_artist_1..5,        │
       │                    │   prev_title_1..5,         │
       │                    │   sample_rate, bit_depth } │
       │                    └─────────┬──────────────────┘
       │                              │
       │                              ▼
       │                      updateTrack(artist, title, album)
       │                         │     │     │
       │           ┌─────────────┘     │     └──────────────┐
       │           ▼                   ▼                     ▼
       │    DOM updated         songStartTime          fetchArtwork()
       │    (artist, title,     = Date.now()                │
       │     album)             (wall-clock start)          ▼
       │                                            ┌──────────────────┐
       │                                            │ iTunes Search API│
       │                                            │ ?term=...        │
       │                                            └────────┬─────────┘
       │                                                     │
       │                                                     ▼
       │                                            artworkUrl (600x600)
       │                                            trackTimeMillis (duration)
       │                                                     │
       │                                                     ▼
       │                                            <img> rendered in
       │                                            .artwork container
       │
User clicks Play
       │
       ▼
┌──────────────┐    HTTPS     ┌──────────────┐
│ HLS.js       │◀────────────▶│ CloudFront   │
│ loadSource() │  M3U8 + TS   │ CDN          │
└──────┬───────┘              └──────────────┘
       │
       ├─── Audio decoded ──────▶ <audio> element ──▶ speakers
       │
       ├─── FRAG_CHANGED event ─▶ triggerMetadataFetch()
       │    (song change detect)   (3s debounce)
       │                                │
       │                                ▼
       │                         fetchMetadata() ──▶ (same flow as above)
       │
       ├─── ID3 metadata ──────▶ parseID3Frames() (fallback, not used yet)
       │
       └─── Text Track cues ──▶ onCueChange() ──▶ handleMetadataFields()
            (Safari fallback)                     (same updateTrack flow)
```

### 3.2 Rating Submission Flow

```
Track changes → updateRatingUI()
       │
       ├─── GET /api/ratings/check?station=... ──▶ Check if IP already rated
       │         │
       │         ├─ rated: true  → disable buttons, show "You rated this track"
       │         └─ rated: false → enable buttons
       │
       ├─── GET /api/ratings/summary ──▶ Fetch aggregate counts
       │         │
       │         └─ Display: 👍 N  👎 N
       │
User clicks 👍 or 👎
       │
       ▼
submitRating(score)
       │
       ▼
┌──────────────────────────────────────┐
│ POST /api/ratings                    │
│ Content-Type: application/json       │
│                                      │
│ {                                    │
│   "station": "Artist - Track Title", │
│   "score": 1                         │
│ }                                    │
│ (IP extracted from X-Forwarded-For   │
│  or remote_addr by Flask)            │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────-─┐
│ Flask API                      │
│ ├─ Validate fields             │
│ ├─ Extract client IP           │
│ ├─ INSERT INTO ratings         │
│ │   (station, score, ip)       │
│ ├─ UNIQUE(station,ip) enforced │
│ ├─ 201 → { status: "ok" }      │
│ └─ 409 → { error: "already     │
│            rated" }            │
└───────────────┬───────────────-┘
                │
                ▼
┌──────────────────────────────-─┐
│ Frontend                       │
│ ├─ Disable both rate buttons   │
│ ├─ Show "Thanks!" or "Noted!"  │
│ ├─ Refresh aggregate counts    │
│ └─ Reset on next track change  │
└──────────────────────────────-─┘
```

### 3.3 Metadata Extraction Paths

```text
                    ┌──────--───────────────────────────┐
                    │     PRIMARY: CloudFront JSON      │
                    │                                   │
                    │  FRAG_CHANGED event (HLS.js)      │
                    │         │                         │
                    │         ▼                         │
                    │  triggerMetadataFetch() (3s deb.) │
                    │         │                         │
                    │         ▼                         │
                    │  GET /metadatav2.json             │
                    │  { artist, title, album,          │
                    │    prev_artist_1..5,              │
                    │    prev_title_1..5 }              │
                    └──────────┬───--───────────────────┘
                               │
                               ▼
                        updateTrack()
                               │
              ┌────────────────┼──────-──────────┐
              ▼                ▼                 ▼
       fetchArtwork()   updateRatingUI()   pushHistory()
       (iTunes API)     (check + counts)   (accumulate)

        ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                    FALLBACK: ID3 Tags
                    (not currently in stream)

              ┌────────────┬────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────────┐
        │ Path 1   │ │ Path 2   │ │ Path 3       │
        │ HLS.js   │ │ HLS.js   │ │ Safari       │
        │ Text     │ │ Raw ID3  │ │ Native HLS   │
        │ Tracks   │ │ Parsing  │ │ Text Tracks  │
        └────┬─────┘ └────┬─────┘ └──────┬───────┘
             │            │               │
             ▼            ▼               ▼
        onCueChange  parseID3Frames  onCueChange
             │            │               │
             └────────────┼───────────────┘
                          ▼
                 handleMetadataFields()
                          │
                          ▼
                   updateTrack()
```

---

## 4. State Management

### 4.1 Frontend State Model

```text
┌─────────────────────────────────────────────────┐
│               Application State                 │
│                                                 │
│  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ Playback State      │  │ UI State         │  │
│  │                     │  │                  │  │
│  │ playing: boolean    │  │ DOM elements     │  │
│  │ muted: boolean      │  │ (cached refs)    │  │
│  │ hls: Hls | null     │  │                  │  │
│  │ audio.volume: float │  │ Icon visibility  │  │
│  │                     │  │ (play/pause/     │  │
│  │                     │  │  spinner)        │  │
│  └─────────────────────┘  └──────────────────┘  │
│                                                 │
│  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ Track State         │  │ Rating State     │  │
│  │                     │  │                  │  │
│  │ currentTrack: str   │  │ .rated CSS class │  │
│  │ trackDuration: sec  │  │ rateFb.text      │  │
│  │ songStartTime: ms   │  │ rateUpCount      │  │
│  │ (wall-clock start)  │  │ rateDownCount    │  │
│  │ artistEl.text       │  │ lastSummary: {}  │  │
│  │ trackEl.text        │  │                  │  │
│  │ albumEl.text        │  │ (resets on new   │  │
│  │ artworkEl.innerHTML │  │  track, checked  │  │
│  │                     │  │  by IP via API)  │  │
│  │ history[]: array    │  │                  │  │
│  │ (max 20 entries)    │  │                  │  │
│  └─────────────────────┘  └──────────────────┘  │
│                                                 │
│  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ Filter State        │  │ Metadata State   │  │
│  │                     │  │                  │  │
│  │ prevFilter: string  │  │ lastMetadataFetch│  │
│  │ ('all'|'up'|'down') │  │ (debounce timer) │  │
│  │ historyLimit: int   │  │ DEBOUNCE = 3000ms│  │
│  │ (5, 10, 15, or 20)  │  │                  │  │
│  └─────────────────────┘  └──────────────────┘  │
│                                                 │
│  Persistence: NONE (all state lost on reload)   │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 4.2 State Transitions

```text
                    ┌────────────────┐
                    │  IDLE          │
                    │  (page load)   │
                    └───────┬────────┘
                            │ HLS manifest parsed
                            ▼
                    ┌───────────────┐
           ┌──────▶│  READY         │◀──────┐
           │       │  (play enabled)│       │
           │       └───────┬────────┘       │
           │               │ click play     │
           │               ▼                │
           │       ┌────────────────┐       │
           │       │  LOADING       │       │
           │       │  (spinner)     │       │
           │       └───────┬────────┘       │
           │               │ audio playing  │
           │               ▼                │
           │       ┌────────────────┐       │
           │       │  PLAYING       │───────┘
           │       │  (pause icon)  │ click pause
           │       └───────┬────────┘
           │               │ fatal error
           │               ▼
           │       ┌────────────────┐
           └───────│  ERROR         │
            4s     │  (auto-retry)  │
            retry  └────────────────┘
```

---

## 5. File Structure

```
radiocalico/
├── api/
│   ├── app.py                  # Flask backend (ratings API + static serving)
│   ├── requirements.txt        # Python dependencies (unpinned)
│   └── venv/                   # Python virtual environment
├── static/
│   ├── index.html              # Main entry point (SPA, ~98 lines)
│   ├── logo.png                # Brand logo (40x40 in navbar, also favicon)
│   ├── css/
│   │   └── player.css          # All styles (~372 lines)
│   └── js/
│       └── player.js           # All client logic (~482 lines)
├── RadioCalicoLayout.png       # UI mockup / reference design
├── RadioCalicoLogoTM.png       # Full logo asset
├── RadioCalico_Style_Guide.txt # Brand & UI style guide
├── stream_URL.txt              # HLS stream endpoint reference
├── CLAUDE.md                   # Claude Code project guidelines
└── design.md                   # This document
```

---

## 6. API Contract

**IMPORTANT**: All API routes use the `/api` prefix. The frontend must always call `/api/ratings/...`.

### `GET /api/ratings`

| Field        | Value          |
| ------------ | -------------- |
| **URL**      | `/api/ratings` |
| **Method**   | GET            |
| **Auth**     | None           |
| **Response** | `200 OK`       |

```json
[
  {
    "id": 1,
    "station": "Shandi Sinnamon - He's A Dream",
    "score": 1,
    "ip": "127.0.0.1",
    "created_at": "2026-03-08T14:30:00"
  }
]
```

### `GET /api/ratings/summary`

Returns aggregate likes/dislikes per station (used for rating badges).

| Field        | Value                  |
| ------------ | ---------------------- |
| **URL**      | `/api/ratings/summary` |
| **Method**   | GET                    |
| **Auth**     | None                   |
| **Response** | `200 OK`               |

```json
{
  "Shandi Sinnamon - He's A Dream": { "likes": 3, "dislikes": 1 },
  "Shania Twain - Swingin' With My Eyes Closed": { "likes": 5, "dislikes": 0 }
}
```

### `GET /api/ratings/check`

Checks if the current user (by IP) has already rated a station.

| Field        | Value                             |
| ------------ | --------------------------------- |
| **URL**      | `/api/ratings/check?station=...`  |
| **Method**   | GET                               |
| **Auth**     | None (IP-based)                   |
| **Response** | `200 OK`                          |

```json
{ "rated": true, "score": 1 }
// or
{ "rated": false }
```

### `POST /api/ratings`

| Field | Value |
|-------|-------|
| **URL** | `/api/ratings` |
| **Method** | POST |
| **Auth** | None (IP extracted from request) |
| **Content-Type** | `application/json` |

**Request body:**

```json
{
  "station": "Artist - Track Title",
  "score": 1
}
```

**Responses:**

| Status           | Body                                                              |
| ---------------- | ----------------------------------------------------------------- |
| `201 Created`    | `{ "status": "ok" }`                                             |
| `400 Bad Request`| `{ "error": "station and score required" }`                      |
| `409 Conflict`   | `{ "error": "already rated" }` (IP already voted for this station) |

---

## 7. Technology Stack

| Layer               | Technology         | Version         | Purpose                              |
| ------------------- | ------------------ | --------------- | ------------------------------------ |
| **CDN**             | AWS CloudFront     | —               | Audio stream delivery                |
| **Streaming**       | HLS (M3U8 + TS)    | —               | Adaptive bitrate streaming           |
| **Frontend**        | Vanilla JavaScript | ES2020+         | Player logic, metadata, UI           |
| **Streaming Lib**   | HLS.js             | v1.x (CDN)      | HLS decoding in non-Safari browsers  |
| **Metadata Source** | CloudFront JSON    | —               | Track info (metadatav2.json)         |
| **Metadata API**    | iTunes Search API  | —               | Album artwork + track duration       |
| **Fonts**           | Google Fonts       | —               | Montserrat, Open Sans                |
| **Backend**         | Python Flask       | 3.1.x           | REST API for ratings                 |
| **CORS**            | flask-cors         | —               | Cross-origin request handling        |
| **Database**        | MySQL              | 5.7 (Homebrew)  | Ratings storage (IP-deduped)         |
| **DB Driver**       | PyMySQL            | —               | Python-MySQL connector               |

---

## 8. Design Tokens (from Style Guide)

### Colors

| Token        | Hex       | Usage                                         |
| ------------ | --------- | --------------------------------------------- |
| `--mint`     | `#D8F2D5` | Backgrounds, accents, previous tracks section |
| `--forest`   | `#1F4E23` | Primary buttons, headings                     |
| `--teal`     | `#38A29D` | Navbar background, hover states               |
| `--orange`   | `#EFA63C` | Call-to-action accents                        |
| `--charcoal` | `#231F20` | Body text, player bar, icon outlines          |
| `--cream`    | `#F5EADA` | Secondary backgrounds                         |
| `--white`    | `#FFFFFF` | Text on dark, backgrounds                     |

### Typography

| Style        | Font       | Weight | Size             |
| ------------ | ---------- | ------ | ---------------- |
| H1 (Artist)  | Montserrat | 700    | 3rem / 48px      |
| H2 (Track)   | Montserrat | 600    | 2.25rem / 36px   |
| H3 (Section) | Montserrat | 500    | 1.5rem / 24px    |
| Body         | Open Sans  | 400    | 1rem / 16px      |
| Small        | Open Sans  | 400    | 0.875rem / 14px  |

### Layout

| Property          | Value                           |
| ----------------- | ------------------------------- |
| Max content width | 1200px                          |
| Grid              | 2-column (1-column below 700px) |
| Gutters           | 24px                            |
| Vertical rhythm   | multiples of 16px               |
| Baseline grid     | 8px                             |

---

## 9. Security Assessment

### Current Vulnerabilities

- **CRITICAL** — Hardcoded DB credentials (`api/app.py:8-14`). Use environment variables + `.env` file.
- **CRITICAL** — No authentication on API (`api/app.py`). Add rate limiting; consider API keys.
- **HIGH** — Debug mode enabled (`api/app.py:102`). Use `FLASK_ENV` variable.
- **HIGH** — CORS unrestricted (`api/app.py:8`). Whitelist allowed origins.
- **MEDIUM** — No input validation (`POST /api/ratings`). Validate `score` is 0 or 1; limit `station` length.
- **MEDIUM** — No SRI on CDN scripts (`index.html:95`). Add `integrity` + `crossorigin` attributes.
- **LOW** — iTunes API exposes queries (`player.js:48`). Proxy through backend or cache.

### Recommended Security Architecture

```text
┌────────────┐     ┌───────────────┐     ┌──────────────┐
│ Browser    │────▶│ Rate Limiter  │────▶│ Flask API    │
│            │     │ (nginx/Flask- │     │ (no debug)   │
│            │     │  Limiter)     │     │              │
└────────────┘     └───────────────┘     └──────┬───────┘
                                                │
                                         .env credentials
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │ MySQL        │
                                         │ (non-root    │
                                         │  user)       │
                                         └──────────────┘
```

---

## 10. Known Gaps & Roadmap

### Phase 1 — Foundation

**Completed:**

- [x] CloudFront JSON metadata integration (primary metadata source)
- [x] IP-based rating deduplication (unique constraint on station + ip)
- [x] Rating summary and check endpoints (`/api/ratings/summary`, `/api/ratings/check`)
- [x] Flask serves both static files and API (single port 5000)
- [x] Event-driven metadata fetching (HLS.js `FRAG_CHANGED` with 3s debounce)
- [x] Wall-clock elapsed time display with iTunes duration
- [x] History accumulation beyond 5 tracks (up to 20)
- [x] Recently Played filters (All/Liked/Disliked) and limit dropdown (5/10/15/20)
- [x] Album names from iTunes API in Recently Played
- [x] Favicon (`logo.png`)

**Remaining:**

- [ ] Move DB credentials to environment variables
- [ ] Disable Flask debug mode in production
- [ ] Restrict CORS origins
- [ ] Add input validation on ratings endpoint
- [ ] Pin dependency versions in `requirements.txt`
- [ ] Add database schema migration script

### Phase 2 — Reliability

- [ ] Add connection pooling (SQLAlchemy or similar)
- [ ] Add pagination to `GET /ratings`
- [ ] Add health check endpoint (`GET /health`)
- [ ] Add error logging (Python `logging` module)
- [ ] Add frontend error reporting
- [ ] Cache artwork in localStorage
- [ ] Persist volume preference in localStorage

### Phase 3 — Production Readiness

- [ ] Add Dockerfile and docker-compose.yml
- [ ] Add CI/CD pipeline (GitHub Actions)
- [ ] Add unit and integration tests
- [ ] Add SRI hashes for CDN scripts
- [ ] Add rate limiting on ratings endpoint
- [ ] Add monitoring and alerting (uptime, errors)
- [ ] Add database backups and retention policy

### Phase 4 — Enhancements

- [ ] PWA manifest + service worker (offline shell)
- [ ] Dark mode theme toggle
- [ ] Accessibility audit (ARIA labels, focus management, contrast)
- [ ] "Now playing" API endpoint (server-side metadata source)
- [ ] Admin dashboard for viewing ratings and analytics
- [ ] Multiple stream quality options
- [ ] Social sharing features

---

## 11. Deployment Model (Proposed)

```text
┌─────────────────────────────────────────────────────────────┐
│                    Production Architecture                  │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │ CloudFront  │    │ S3 / Static  │    │ CloudFront     │  │
│  │ (audio      │    │ Host         │    │ (audio stream) │  │
│  │  stream)    │    │ (frontend)   │    │                │  │
│  └──────┬──────┘    └──────┬───────┘    └────────────────┘  │
│         │                  │                                │
│         │    ┌─────────────┘                                │
│         │    │                                              │
│         ▼    ▼                                              │
│  ┌────────────────┐                                         │
│  │   Browser      │                                         │
│  │   (end user)   │                                         │
│  └───────┬────────┘                                         │
│          │                                                  │
│          │ /api/*                                           │
│          ▼                                                  │
│  ┌────────────────┐    ┌────────────────┐                   │
│  │ API Gateway /  │───▶│ Flask API      │                   │
│  │ Load Balancer  │    │ (container)    │                   │
│  └────────────────┘    └───────┬────────┘                   │
│                                │                            │
│                                ▼                            │
│                        ┌────────────────┐                   │
│                        │ RDS MySQL      │                   │
│                        │ (managed)      │                   │
│                        └────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

<!-- Generated 2026-03-08, updated 2026-03-09 — Radio Calico Design Document v1.1 -->
