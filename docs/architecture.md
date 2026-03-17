# Radio Calico - Architecture Diagrams

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Request Flow](#2-request-flow)
3. [Data Flow — Playback & Metadata](#3-data-flow--playback--metadata)
4. [Data Flow — User Interactions](#4-data-flow--user-interactions)
5. [Event-Driven Architecture](#5-event-driven-architecture)
6. [CI/CD Pipeline](#6-cicd-pipeline)
7. [Database Schema](#7-database-schema)
8. [Authentication Flow](#8-authentication-flow)
9. [Claude Code Agents](#9-claude-code-agents)

---

## 1. System Architecture

High-level overview of all components and how they connect. In production, nginx serves static files directly and proxies `/api/` requests to gunicorn/Flask. The browser also communicates directly with CloudFront for HLS streaming and metadata, with iTunes for artwork/duration, and with Google Fonts for typography.

```mermaid
graph TD
    Browser["Browser<br/>(HLS.js + player.js)"]

    subgraph CloudFront["AWS CloudFront CDN"]
        HLS["HLS Stream<br/>live.m3u8<br/>(FLAC + AAC)"]
        Meta["Metadata JSON<br/>metadatav2.json"]
    end

    subgraph Docker["Docker Production Stack"]
        nginx["nginx:alpine<br/>:80"]
        gunicorn["gunicorn + Flask<br/>:5000 (internal)"]
        MySQL["MySQL 8.0<br/>:3306 (internal)"]
    end

    iTunes["iTunes Search API<br/>Artwork + Duration"]
    GoogleFonts["Google Fonts<br/>Montserrat + Open Sans"]

    Browser -- "HLS stream (FLAC/AAC)" --> HLS
    Browser -- "GET metadatav2.json" --> Meta
    Browser -- "Static files (HTML/CSS/JS)" --> nginx
    Browser -- "/api/* requests" --> nginx
    Browser -- "Song search (artwork, duration)" --> iTunes
    Browser -- "Font loading" --> GoogleFonts

    nginx -- "Serves static files" --> nginx
    nginx -- "proxy_pass /api/" --> gunicorn
    gunicorn -- "PyMySQL queries" --> MySQL

    style Browser fill:#D8F2D5,stroke:#1F4E23,color:#231F20
    style nginx fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style gunicorn fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style MySQL fill:#EFA63C,stroke:#231F20,color:#231F20
    style HLS fill:#f5f5f5,stroke:#38A29D,color:#231F20
    style Meta fill:#f5f5f5,stroke:#38A29D,color:#231F20
    style iTunes fill:#f5f5f5,stroke:#999,color:#231F20
    style GoogleFonts fill:#f5f5f5,stroke:#999,color:#231F20
```

---

## 2. Request Flow

Sequence diagram showing the four main request types: static file serving, API calls through the nginx reverse proxy, HLS streaming from CloudFront, and artwork lookups from iTunes.

```mermaid
sequenceDiagram
    participant B as Browser
    participant N as nginx
    participant G as gunicorn/Flask
    participant DB as MySQL
    participant CF as CloudFront
    participant IT as iTunes API

    Note over B,N: Static File Request
    B->>N: GET /index.html
    N-->>B: 200 index.html (from /usr/share/nginx/html)

    Note over B,N: Cached Static Asset
    B->>N: GET /css/player.css
    N-->>B: 200 player.css (Cache-Control: 7d, immutable)

    Note over B,DB: API Request (e.g., submit rating)
    B->>N: POST /api/ratings {station, score}
    N->>G: proxy_pass + X-Forwarded-For + X-Request-ID
    G->>DB: INSERT INTO ratings (station, score, ip)
    DB-->>G: OK / IntegrityError (duplicate)
    G-->>N: 201 {"status":"ok"} / 409 {"error":"already rated"}
    N-->>B: Response + X-Request-ID header

    Note over B,CF: HLS Audio Streaming
    B->>CF: GET /hls/live.m3u8
    CF-->>B: HLS master playlist (FLAC level 0, AAC level 1)
    B->>CF: GET /hls/segment_NNN.ts
    CF-->>B: Audio segment (decoded by HLS.js or native)

    Note over B,CF: Metadata Fetch (on FRAG_CHANGED)
    B->>CF: GET /metadatav2.json
    CF-->>B: {current_artist, current_title, prev_artist_1..5, ...}

    Note over B,IT: Artwork + Duration Lookup
    B->>IT: GET /search?term=Artist+Title&entity=song&limit=1
    IT-->>B: {artworkUrl100, trackTimeMillis, collectionName}
```

---

## 3. Data Flow — Playback & Metadata

How track metadata flows from CloudFront through the player to the UI, including latency compensation, iTunes artwork caching, and history accumulation.

```mermaid
graph TD
    Load["Page Load"] --> FM["fetchMetadata()"]
    FM --> CF["CloudFront<br/>metadatav2.json"]
    CF --> Delay["Latency delay<br/>(hls.latency or 6s)"]
    Delay --> UT["updateTrack(artist, title, album)"]

    UT --> DOM["Update DOM<br/>(artist, title, album)"]
    UT --> Timer["songStartTime<br/>= Date.now()"]
    UT --> FA["fetchArtwork()"]
    UT --> RUI["updateRatingUI()"]
    UT --> PH["pushHistory()"]

    FA --> Cache["fetchItunesCached()<br/>(localStorage 24h TTL)"]
    Cache --> iTunes["iTunes Search API<br/>(artwork + duration)"]

    Play["User clicks Play"] --> HLS["HLS.js loads stream"]
    HLS --> Audio["Audio plays"]
    HLS --> FC["FRAG_CHANGED event"]
    FC --> TMF["triggerMetadataFetch()<br/>(3s debounce)"]
    TMF --> FM

    style Load fill:#D8F2D5,stroke:#1F4E23
    style Play fill:#D8F2D5,stroke:#1F4E23
    style UT fill:#38A29D,stroke:#1F4E23,color:#FFF
    style Cache fill:#EFA63C,stroke:#231F20
```

---

## 4. Data Flow — User Interactions

How user actions (rating, sharing, auth, profile, feedback, theme, quality) flow through the system from UI click to API/state change.

```mermaid
graph TD
    subgraph Rating
        RClick["Click thumbs up/down"] --> SR["submitRating(score)"]
        SR --> PostRate["POST /api/ratings"]
        PostRate --> FTR["fetchTrackRatings()"]
        FTR --> Counts["Update like/dislike counts"]
    end

    subgraph Sharing
        SClick["Click share button"] --> GST["getShareText() /<br/>getRecentlyPlayedText()"]
        GST --> WO["window.open(URL)"]
    end

    subgraph Auth
        Login["Submit login form"] --> PostLogin["POST /api/login"]
        PostLogin --> Token["Store token in localStorage"]
        Token --> Profile["showProfileView() → loadProfile()"]
        Logout["Click logout"] --> PostLogout["POST /api/logout"]
        PostLogout --> Clear["Clear localStorage"]
        Clear --> AuthView["showAuthView()"]
    end

    subgraph Settings
        Theme["Toggle theme radio"] --> AT["applyTheme()"]
        AT --> DT["data-theme attribute"]
        AT --> LS["localStorage rc-theme"]
        Quality["Toggle quality radio"] --> ASQ["applyStreamQuality()"]
        ASQ --> Init["initHls() + localStorage"]
    end

    style RClick fill:#D8F2D5,stroke:#1F4E23
    style SClick fill:#D8F2D5,stroke:#1F4E23
    style Login fill:#D8F2D5,stroke:#1F4E23
    style Logout fill:#D8F2D5,stroke:#1F4E23
    style Theme fill:#D8F2D5,stroke:#1F4E23
    style Quality fill:#D8F2D5,stroke:#1F4E23
```

---

## 5. Event-Driven Architecture

All HLS.js events, audio element events, and DOM event handlers that drive the player's behavior.

```mermaid
graph LR
    subgraph "HLS.js Events"
        MP["MANIFEST_PARSED"] --> EnablePlay["Enable play button<br/>+ set quality level"]
        FC["FRAG_CHANGED"] --> TMF["triggerMetadataFetch()"]
        FPM["FRAG_PARSING_METADATA"] --> ID3["parseID3Frames()<br/>→ handleMetadataFields()"]
        LL["LEVEL_LOADED"] --> SrcQ["Update source quality display"]
        ERR["ERROR (fatal)"] --> Retry["Exponential backoff retry<br/>(max 10, 4s→60s)"]
    end

    subgraph "Audio Events"
        Playing["playing"] --> PauseIcon["showPlayIcon('pause')"]
        Waiting["waiting"] --> SpinIcon["showPlayIcon('spinner')"]
        TimeUp["timeupdate (~4Hz)"] --> BarTime["Update elapsed / total"]
    end

    subgraph "DOM Click Handlers"
        PlayBtn["play-btn"] --> Toggle["togglePlay()"]
        MuteBtn["mute-btn"] --> Mute["Toggle mute/unmute"]
        RateBtn["rate-up / rate-down"] --> Submit["submitRating(1/0)"]
        MenuBtn["menu-btn"] --> Open["openDrawer()"]
        CloseBtn["drawer-close"] --> Close["closeDrawer()"]
        SettingsBtn["settings-btn"] --> Drop["Toggle dropdown"]
    end

    style MP fill:#38A29D,stroke:#1F4E23,color:#FFF
    style FC fill:#38A29D,stroke:#1F4E23,color:#FFF
    style ERR fill:#EFA63C,stroke:#231F20
    style PlayBtn fill:#D8F2D5,stroke:#1F4E23
    style RateBtn fill:#D8F2D5,stroke:#1F4E23
```

---

## 6. CI/CD Pipeline

GitHub Actions workflow (13 jobs) triggered on push/PR to `main`. Lint runs first, then test jobs in parallel. Security scans run independently. E2E, browser, and ZAP run after test jobs complete.

```mermaid
graph LR
    Push["Push / PR<br/>to main"] --> lint

    subgraph Linting
        lint["lint<br/>ruff + ESLint<br/>+ Stylelint + HTMLHint"]
    end

    lint --> python-tests["python-tests<br/>pytest + coverage<br/>(95% threshold)"]
    lint --> integration-tests["integration-tests<br/>pytest<br/>test_integration.py"]
    lint --> js-tests["js-tests<br/>Jest + coverage<br/>(90% line threshold)"]
    lint --> skills-tests["skills-tests<br/>pytest<br/>18 slash commands"]

    python-tests --> e2e-tests["e2e-tests<br/>Docker prod stack<br/>+ pytest"]
    js-tests --> e2e-tests
    integration-tests --> e2e-tests

    python-tests --> browser-tests["browser-tests<br/>Selenium<br/>headless Chrome"]
    js-tests --> browser-tests
    integration-tests --> browser-tests

    python-tests --> zap["zap<br/>OWASP ZAP<br/>DAST baseline"]
    js-tests --> zap

    subgraph "Security Scans (no dependencies)"
        bandit["bandit<br/>Python SAST"]
        safety["safety<br/>Python deps"]
        npm-audit["npm-audit<br/>JS deps"]
        hadolint["hadolint<br/>Dockerfile lint"]
        trivy["trivy<br/>Docker image<br/>vuln scan"]
    end

    Push --> bandit
    Push --> safety
    Push --> npm-audit
    Push --> hadolint
    Push --> trivy

    style lint fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style python-tests fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style integration-tests fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style js-tests fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style skills-tests fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style e2e-tests fill:#EFA63C,stroke:#231F20,color:#231F20
    style browser-tests fill:#EFA63C,stroke:#231F20,color:#231F20
    style zap fill:#EFA63C,stroke:#231F20,color:#231F20
    style bandit fill:#D8F2D5,stroke:#1F4E23,color:#231F20
    style safety fill:#D8F2D5,stroke:#1F4E23,color:#231F20
    style npm-audit fill:#D8F2D5,stroke:#1F4E23,color:#231F20
    style hadolint fill:#D8F2D5,stroke:#1F4E23,color:#231F20
    style trivy fill:#D8F2D5,stroke:#1F4E23,color:#231F20
```

---

## 7. Database Schema

Entity-relationship diagram of the four MySQL tables. The `profiles` table has a foreign key to `users` (one-to-one). The `feedback` table stores a snapshot of the user's profile at submission time (denormalized). The `ratings` table is independent, keyed by station + IP.

```mermaid
erDiagram
    users {
        INT id PK "AUTO_INCREMENT"
        VARCHAR(50) username UK "NOT NULL, UNIQUE"
        VARCHAR(64) password_hash "NOT NULL"
        VARCHAR(32) salt "NOT NULL"
        VARCHAR(64) token "NULL (set on login)"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }

    profiles {
        INT id PK "AUTO_INCREMENT"
        INT user_id FK "NOT NULL, UNIQUE"
        VARCHAR(100) nickname "DEFAULT ''"
        VARCHAR(255) email "DEFAULT ''"
        VARCHAR(500) genres "DEFAULT ''"
        TEXT about "NULL"
        TIMESTAMP updated_at "ON UPDATE CURRENT_TIMESTAMP"
    }

    feedback {
        INT id PK "AUTO_INCREMENT"
        VARCHAR(255) email "DEFAULT ''"
        TEXT message "NOT NULL"
        VARCHAR(45) ip "DEFAULT ''"
        VARCHAR(50) username "DEFAULT ''"
        VARCHAR(100) nickname "DEFAULT ''"
        VARCHAR(500) genres "DEFAULT ''"
        TEXT about "NULL"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }

    ratings {
        INT id PK "AUTO_INCREMENT"
        VARCHAR(255) station "NOT NULL"
        TINYINT score "NOT NULL (0 or 1)"
        VARCHAR(45) ip "NOT NULL"
        TIMESTAMP created_at "DEFAULT CURRENT_TIMESTAMP"
    }

    users ||--o| profiles : "has (ON DELETE CASCADE)"
    users ||--o{ feedback : "submits (denormalized snapshot)"
```

---

## 8. Authentication Flow

Complete lifecycle from registration through login, authenticated operations (profile and feedback), and logout. Tokens are generated server-side with `secrets.token_hex(32)` and stored in both the database and the client's `localStorage`.

```mermaid
sequenceDiagram
    participant B as Browser (player.js)
    participant F as Flask API
    participant DB as MySQL

    Note over B,DB: Registration
    B->>F: POST /api/register {username, password}
    F->>F: Validate (8-128 chars, username <= 50)
    F->>F: hash_password(password) -> salt + PBKDF2 hash
    F->>DB: INSERT INTO users (username, password_hash, salt)
    alt Username taken
        DB-->>F: IntegrityError
        F-->>B: 409 {"error": "Username already taken"}
    else Success
        DB-->>F: OK
        F-->>B: 201 {"status": "ok"}
    end

    Note over B,DB: Login
    B->>F: POST /api/login {username, password}
    F->>DB: SELECT id, password_hash, salt FROM users WHERE username = ?
    DB-->>F: User row
    F->>F: verify_password(password, salt, hash)<br/>hmac.compare_digest (timing-safe)
    alt Invalid credentials
        F-->>B: 401 {"error": "Invalid username or password"}
    else Valid
        F->>F: token = secrets.token_hex(32)
        F->>DB: UPDATE users SET token = ? WHERE id = ?
        DB-->>F: OK
        F-->>B: 200 {"token": "abc...", "username": "user1"}
        B->>B: localStorage.setItem("rc-token", token)<br/>localStorage.setItem("rc-user", username)
    end

    Note over B,DB: Authenticated Request (Get Profile)
    B->>F: GET /api/profile<br/>Authorization: Bearer <token>
    F->>F: require_auth() -> extract token
    F->>DB: SELECT id, username FROM users WHERE token = ?
    DB-->>F: User row
    F->>DB: SELECT nickname, email, genres, about FROM profiles WHERE user_id = ?
    DB-->>F: Profile row
    F-->>B: 200 {nickname, email, genres, about}

    Note over B,DB: Authenticated Request (Submit Feedback)
    B->>F: POST /api/feedback {message}<br/>Authorization: Bearer <token>
    F->>F: require_auth() -> validate token
    F->>DB: SELECT nickname, email, genres, about FROM profiles WHERE user_id = ?
    DB-->>F: Profile snapshot
    F->>DB: INSERT INTO feedback (email, message, ip, username, nickname, genres, about)
    DB-->>F: OK
    F-->>B: 201 {"status": "ok"}

    Note over B,DB: Logout
    B->>F: POST /api/logout<br/>Authorization: Bearer <token>
    F->>F: require_auth() -> validate token
    F->>DB: UPDATE users SET token = NULL WHERE id = ?
    DB-->>F: OK
    F-->>B: 200 {"status": "ok"}
    B->>B: localStorage.removeItem("rc-token")<br/>localStorage.removeItem("rc-user")
```

---

## 9. Claude Code Agents

Nine task-specific AI agents in `.claude/agents/`, each with specialized knowledge and workflows for Radio Calico development. Agents complement the 18 slash commands by providing persistent, context-aware personalities for recurring development concerns.

```mermaid
graph TD
    Dev["Developer<br/>(Claude Code CLI)"]

    subgraph Agents[".claude/agents/"]
        QA["QA Engineer<br/>qa-engineer.md"]
        DBA["DBA<br/>dba.md"]
        FE["Frontend Reviewer<br/>frontend-reviewer.md"]
        DO["DevOps<br/>devops.md"]
        API["API Designer<br/>api-designer.md"]
        RM["Release Manager<br/>release-manager.md"]
        SA["Security Auditor<br/>security-auditor.md"]
        PA["Performance Analyst<br/>performance-analyst.md"]
        DW["Documentation Writer<br/>documentation-writer.md"]
    end

    subgraph Codebase["Project Files"]
        Tests["Tests<br/>582 across 6 suites"]
        Schema["Database<br/>db/init.sql (4 tables)"]
        Static["Frontend<br/>static/ (JS + CSS + HTML)"]
        Docker["Infrastructure<br/>Docker + nginx + CI"]
        Flask["API<br/>api/app.py (Flask)"]
        Git["Git + GitHub<br/>PRs, CI, Releases"]
        Security["Security<br/>6 scanning tools"]
        Perf["Caching + CDN<br/>Optimization"]
        Docs["Documentation<br/>docs/ (5 documents)"]
    end

    Dev --> QA
    Dev --> DBA
    Dev --> FE
    Dev --> DO
    Dev --> API
    Dev --> RM
    Dev --> SA
    Dev --> PA
    Dev --> DW

    QA --> Tests
    DBA --> Schema
    FE --> Static
    DO --> Docker
    API --> Flask
    RM --> Git
    SA --> Security
    PA --> Perf
    DW --> Docs

    style Dev fill:#D8F2D5,stroke:#1F4E23,color:#231F20
    style QA fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style DBA fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style FE fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style DO fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style API fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style RM fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style SA fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style PA fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style DW fill:#38A29D,stroke:#1F4E23,color:#FFFFFF
    style Tests fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style Schema fill:#EFA63C,stroke:#231F20,color:#231F20
    style Static fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style Docker fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style Flask fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style Git fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style Security fill:#1F4E23,stroke:#231F20,color:#FFFFFF
    style Perf fill:#EFA63C,stroke:#231F20,color:#231F20
    style Docs fill:#1F4E23,stroke:#231F20,color:#FFFFFF
```
