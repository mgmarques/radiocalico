<table><tr>
<td valign="middle">

# Radio Calico - Architecture Diagrams

| Field | Value |
| --- | --- |
| **Project** | Radio Calico |
| **Version** | 2.0.0 |
| **Date** | 2026-03-21 |
| **Diagrams** | 10 |
| **Status** | Living document |

</td>
<td valign="middle" width="20%" align="right"><img src="../RadioCalicoLogoTM.png" alt="Radio Calico Logo" width="100%"></td>
</tr></table>

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Request Flow](#2-request-flow)
3. [Data Flow — Playback & Metadata](#3-data-flow--playback--metadata)
4. [Data Flow — User Interactions](#4-data-flow--user-interactions)
5. [Event-Driven Architecture](#5-event-driven-architecture)
6. [CI/CD Pipeline](#6-cicd-pipeline)
7. [Database Schema](#7-database-schema)
8. [Authentication Flow](#8-authentication-flow)
9. [Claude Code — Skill to Agent Delegation](#9-claude-code--skill-to-agent-delegation)
10. [Claude Code — Full Agent & Skill Hierarchy](#10-claude-code--full-agent--skill-hierarchy)

---

## 1. System Architecture

High-level overview of all components and their relationships.

```mermaid
graph TD
    Browser["🌐 Client Browser\n(player.js · HLS.js · CSS)"]

    subgraph CDN["☁️ CloudFront CDN"]
        HLS["HLS Stream\nlive.m3u8\n(FLAC / AAC)"]
        Meta["metadatav2.json\n(current + 5 prev tracks)"]
    end

    subgraph Docker["🐳 Docker (prod: :5050 | dev: :5050)"]
        nginx["nginx\n(reverse proxy + static files)"]
        gunicorn["gunicorn\n(4 workers · Flask API :5000)"]
        mysql["MySQL 8.0\n(ratings · users · profiles · feedback)"]
        ollama["Ollama\n(Llama 3.2 · song info · quiz · chat · ticker)"]
    end

    subgraph External["🔌 External APIs"]
        iTunes["iTunes Search API\n(artwork · duration)"]
        Fonts["Google Fonts\n(Montserrat · Open Sans)"]
    end

    Browser -->|"HLS segments"| HLS
    Browser -->|"metadata poll\n(FRAG_CHANGED)"| Meta
    Browser -->|"artwork search\n(localStorage 24h TTL)"| iTunes
    Browser -->|"fonts"| Fonts
    Browser -->|"static files\n(HTML · JS · CSS · images)"| nginx
    Browser -->|"API calls\n(/api/*)"| nginx
    nginx -->|"proxy_pass /api/"| gunicorn
    gunicorn -->|"PyMySQL queries\n(parameterized)"| mysql
    gunicorn -->|"OpenAI SDK · SSE streaming\n(song info · quiz · chat · ticker · taste)"| ollama
```

---

## 2. Request Flow

Sequence of HTTP requests for each major interaction type.

```mermaid
sequenceDiagram
    participant C as Client Browser
    participant N as nginx :5050
    participant G as gunicorn :5000
    participant DB as MySQL
    participant CF as CloudFront CDN
    participant IT as iTunes API

    rect rgb(230, 245, 230)
        Note over C,N: Static File Request
        C->>N: GET /index.html (or /static/js/player.js)
        N->>C: 200 + static file (7d cache for assets)
    end

    rect rgb(230, 235, 250)
        Note over C,G: API Request (e.g. POST /api/ratings)
        C->>N: POST /api/ratings {station, score}
        N->>G: proxy_pass + X-Forwarded-For
        G->>DB: INSERT ratings (parameterized %s)
        DB-->>G: OK / 409 Duplicate
        G-->>N: 201 / 409 JSON
        N-->>C: response + X-Request-ID
    end

    rect rgb(250, 240, 220)
        Note over C,CF: HLS Streaming
        C->>CF: GET /hls/live.m3u8
        CF-->>C: master playlist (FLAC + AAC levels)
        C->>CF: GET /hls/live*.ts (HLS segments, continuous)
        CF-->>C: audio segments
    end

    rect rgb(250, 230, 230)
        Note over C,IT: Metadata + Artwork
        C->>CF: GET /metadatav2.json
        CF-->>C: {current_artist, current_title, prev_artist_1…5}
        C->>C: check localStorage (24h TTL)
        C->>IT: GET /search?term=Artist+Title&entity=song
        IT-->>C: {artworkUrl100, trackTimeMillis, collectionName}
        C->>C: cache artwork URL in localStorage
    end
```

---

## 3. Data Flow — Playback & Metadata

How metadata is fetched, delayed, and applied to update the UI.

```mermaid
graph TD
    PageLoad["Page Load"]
    FetchMeta["fetchMetadata()"]
    FRAG["HLS.js: FRAG_CHANGED event"]
    TriggerDebounce["triggerMetadataFetch()\n(3s debounce via METADATA_DEBOUNCE_MS)"]
    CFJson["GET CloudFront\nmetadatav2.json"]
    PendingKey["pendingTrackKey check\n(skip if same track)"]
    LatencyDelay["setTimeout(\nhls.latency || 6s\n)"]
    UpdateTrack["updateTrack(artist, title, album)"]

    FetchArtwork["fetchArtwork()"]
    FetchCached["fetchItunesCached()\ncheck localStorage"]
    LocalStorage["localStorage\n(24h TTL per track)"]
    iTunesAPI["iTunes Search API\n(artwork · duration · album)"]

    UpdateRating["updateRatingUI()"]
    CheckRated["GET /api/ratings/check\n?station=Artist-Title"]
    FetchRatings["GET /api/ratings/summary"]

    PushHistory["pushHistory()\n(dedup · max 20 entries)"]
    RenderHistory["renderHistory()\n(sliced to historyLimit: 5/10/15/20)"]
    ElapsedTimer["timeupdate event\nDate.now() - songStartTime\n(not audio.currentTime)"]

    PageLoad -->|"initial boot"| FetchMeta
    FRAG --> TriggerDebounce
    TriggerDebounce --> FetchMeta
    FetchMeta --> CFJson
    CFJson --> PendingKey
    PendingKey -->|"new track"| LatencyDelay
    LatencyDelay --> UpdateTrack

    UpdateTrack --> FetchArtwork
    FetchArtwork --> FetchCached
    FetchCached -->|"cache hit"| UpdateTrack
    FetchCached -->|"cache miss"| iTunesAPI
    iTunesAPI --> LocalStorage
    LocalStorage --> UpdateTrack

    UpdateTrack --> UpdateRating
    UpdateRating --> CheckRated
    UpdateRating --> FetchRatings

    UpdateTrack --> PushHistory
    PushHistory --> RenderHistory
    UpdateTrack --> ElapsedTimer
```

---

## 4. Data Flow — User Interactions

How user actions flow through the frontend and backend.

```mermaid
graph TD
    subgraph Ratings["👍 Ratings"]
        ThumbClick["click 👍 / 👎"]
        SubmitRating["submitRating()\nPOST /api/ratings"]
        FetchTrackRatings["fetchTrackRatings()\nGET /api/ratings/summary"]
        ThumbClick --> SubmitRating --> FetchTrackRatings
    end

    subgraph Share["📤 Share & Search"]
        ShareNow["click share (Now Playing)\ngetShareText()"]
        ShareRecent["click share (Recently Played)\ngetRecentlyPlayedText()"]
        WindowOpen["window.open(..., 'noopener')\nWhatsApp · X · Telegram · Spotify · YT Music · Amazon"]
        ShareNow --> WindowOpen
        ShareRecent --> WindowOpen
    end

    subgraph Auth["🔐 Auth"]
        RegisterForm["register form\nPOST /api/register"]
        LoginForm["login form\nPOST /api/login"]
        Token["token → localStorage\n(rc-token · rc-user)"]
        LogoutBtn["logout\nPOST /api/logout"]
        RegisterForm --> Token
        LoginForm --> Token
        Token --> LogoutBtn
    end

    subgraph Profile["👤 Profile"]
        ProfileForm["profile form\nPUT /api/profile\n(nickname · email · genres · about)"]
        ProfileConfirm["confirmation message"]
        ProfileForm --> ProfileConfirm
    end

    subgraph Feedback["💬 Feedback"]
        FeedbackForm["feedback form\nPOST /api/feedback\n(message + profile snapshot)"]
        FeedbackConfirm["confirmation message"]
        FeedbackForm --> FeedbackConfirm
    end

    subgraph Preferences["⚙️ Settings"]
        ThemeToggle["theme radio button\napplyTheme()\ndata-theme attr + localStorage rc-theme"]
        QualityToggle["quality radio button\napplyStreamQuality()\ninitHls() + localStorage rc-stream-quality"]
        LangToggle["language radio button\napplyLanguage()\nlocalStorage rc-lang"]
        ThemeToggle -->|"light / dark"| HTMLAttr["html[data-theme]"]
        QualityToggle -->|"FLAC level 0 / AAC level 1"| HLSLevel["hls.currentLevel\nhls.loadLevel"]
        LangToggle -->|"en / pt-BR / es"| i18n["translate data-i18n elements\nre-fetch active AI content"]
    end

    subgraph SongInfo["🎵 Song Info (LLM · SSE Streaming)"]
        RetroBtn["retro radio buttons\n(Lyrics · Details · Facts\nMerchandise · Jokes · Everything)"]
        InfoPanel["streaming info panel\nPOST /api/song-info/stream\n(SSE · typewriter cursor)"]
        InfoShare["share AI content\nWhatsApp · X · Telegram"]
        FollowupChat["follow-up chat\nPOST /api/chat (SSE)\nmulti-turn conversation"]
        RetroBtn --> InfoPanel --> InfoShare
        InfoPanel --> FollowupChat
    end

    subgraph QuizGame["🎮 Quiz"]
        QuizBtn["Quiz button\nPOST /api/quiz/start"]
        QuizChat["chat-style 5 questions\nPOST /api/quiz/answer"]
        QuizScore["score summary\n(-5 to +5 per question)"]
        QuizBtn --> QuizChat --> QuizScore
    end

    subgraph Ticker["📰 Auto-Scrolling Ticker"]
        TickerDefault["30 default messages\n(game quotes · geek humor · merch)"]
        TickerAI["AI-generated per track\nPOST /api/song-info (ticker)\n(mood · news · character quotes)"]
        TickerDefault --> TickerAI
    end

    subgraph TasteProfile["🎭 Music Taste Profile"]
        TasteBtn["POST /api/taste-profile\n(liked + disliked songs)"]
        TasteResult["personality analysis\nmusic DNA · recommendation"]
        TasteBtn --> TasteResult
    end
```

---

## 5. Event-Driven Architecture

How HLS.js and DOM events drive the player state machine.

```mermaid
graph LR
    subgraph HLSEvents["HLS.js Events"]
        MP["MANIFEST_PARSED"]
        FC["FRAG_CHANGED"]
        FPM["FRAG_PARSING_METADATA"]
        LL["LEVEL_LOADED"]
        ERR["ERROR (fatal)"]
    end

    subgraph AudioEvents["Audio Element Events"]
        Playing["playing"]
        Waiting["waiting"]
        TU["timeupdate"]
    end

    subgraph DOMEvents["DOM Click Events"]
        Play["play / pause button"]
        Mute["mute button"]
        Rate["👍 / 👎 buttons"]
        Share["share buttons"]
        Filter["filter / dropdown"]
        Settings["settings gear"]
        Drawer["hamburger menu"]
    end

    subgraph Actions["Player Actions"]
        EnablePlay["enable play button\nset quality level\n(hls.currentLevel)"]
        TriggerMeta["triggerMetadataFetch()\n3s debounce"]
        ParseID3["parseID3Frames()\nhandleMetadataFields()"]
        UpdateQualityBadge["update source quality badge\n(FLAC / AAC)"]
        ExponentialRetry["exponential backoff retry\n(max 10 attempts)"]
        ShowPause["showPlayIcon('pause')"]
        ShowSpinner["showPlayIcon('spinner')"]
        UpdateElapsed["update elapsed / total time\nDate.now() - songStartTime"]
        TogglePlay["togglePlay()"]
        ToggleMute["toggleMute()"]
        SubmitRatingAction["submitRating()"]
        OpenShare["window.open(..., 'noopener')"]
        FilterHistory["filterHistory() / renderHistory()"]
        OpenSettings["toggle settings dropdown"]
        OpenDrawer["toggle side drawer"]
    end

    MP --> EnablePlay
    FC --> TriggerMeta
    FPM --> ParseID3
    LL --> UpdateQualityBadge
    ERR --> ExponentialRetry

    Playing --> ShowPause
    Waiting --> ShowSpinner
    TU --> UpdateElapsed

    Play --> TogglePlay
    Mute --> ToggleMute
    Rate --> SubmitRatingAction
    Share --> OpenShare
    Filter --> FilterHistory
    Settings --> OpenSettings
    Drawer --> OpenDrawer
```

---

## 6. CI/CD Pipeline

GitHub Actions jobs and their dependencies.

```mermaid
graph LR
    subgraph Lint["🔍 Lint"]
        lint["lint\nRuff · ESLint\nStylelint · HTMLHint"]
    end

    subgraph Tests["🧪 Tests (need: lint)"]
        python["python-tests\n81 unit · ≥95% coverage"]
        integration["integration-tests\n19 API chain tests"]
        js["js-tests\n238 Jest · ≥95% stmts"]
        skills["skills-tests\n351 commands + agents"]
    end

    subgraph E2E["🌐 E2E (need: python + js + integration)"]
        e2e["e2e-tests\n24 HTTP · nginx→gunicorn→MySQL"]
        browser["browser-tests\n47 Selenium headless Chrome"]
    end

    subgraph DAST["🛡️ DAST (need: python + js)"]
        zap["zap\nOWASP ZAP baseline"]
    end

    subgraph Security["🔒 Security (parallel, no deps)"]
        bandit["bandit\nPython SAST"]
        safety["safety\nPython CVEs"]
        npm_audit["npm-audit\nJS CVEs"]
        hadolint["hadolint\nDockerfile"]
        trivy["trivy\nDocker image\nHIGH/CRITICAL"]
    end

    subgraph VVPlan["📋 V&V Plan (PR only · all 6 suites)"]
        vv["update-vv-plan\nbuilds Docker prod\nruns all suites\n[skip ci] commit"]
    end

    lint --> python
    lint --> integration
    lint --> js
    lint --> skills
    python --> e2e
    js --> e2e
    integration --> e2e
    python --> browser
    js --> browser
    integration --> browser
    python --> zap
    js --> zap
    python -.->|"PR to main only"| vv
    js -.->|"PR to main only"| vv
    integration -.->|"PR to main only"| vv
    skills -.->|"PR to main only"| vv
```

---

## 7. Database Schema

Entity-relationship diagram for all 8 tables (4 app + 4 SBOM).

```mermaid
erDiagram
    RATINGS {
        int id PK
        varchar station
        tinyint score
        varchar ip
        timestamp created_at
    }

    USERS {
        int id PK
        varchar username
        varchar password_hash
        varchar salt
        varchar token
        timestamp created_at
    }

    PROFILES {
        int id PK
        int user_id FK
        varchar nickname
        varchar email
        varchar genres
        text about
        timestamp updated_at
    }

    FEEDBACK {
        int id PK
        varchar email
        text message
        varchar ip
        varchar username
        varchar nickname
        varchar genres
        text about
        timestamp created_at
    }

    SBOM_SCANS {
        int id PK
        varchar project
        date scan_date
        int total_packages
        int total_vulns
        timestamp created_at
    }

    SBOM_PACKAGES {
        int id PK
        int scan_id FK
        enum ecosystem
        varchar name
        varchar version
        varchar license
        varchar latest_version
    }

    SBOM_VULNERABILITIES {
        int id PK
        int scan_id FK
        varchar package_name
        enum ecosystem
        varchar vuln_id
        varchar severity
        decimal cvss_score
        varchar cvss_vector
        date published_date
        date modified_date
        varchar fix_version
        varchar reference_url
        varchar description
    }

    SBOM_IMPACT_ANALYSIS {
        int id PK
        int scan_id FK
        varchar vuln_id
        varchar package_name
        varchar rating
        text analysis
    }

    USERS ||--o| PROFILES : "has one"
    USERS ||--o{ FEEDBACK : "submits"
    SBOM_SCANS ||--o{ SBOM_PACKAGES : "contains"
    SBOM_SCANS ||--o{ SBOM_VULNERABILITIES : "reports"
    SBOM_SCANS ||--o{ SBOM_IMPACT_ANALYSIS : "analyzes"
```

Notes:

- `ratings.score`: `1` = thumbs up, `0` = thumbs down
- `UNIQUE(station, ip)` on ratings prevents duplicate votes per track per IP
- `profiles.user_id` is UNIQUE — one profile per user, CASCADE delete on user removal
- `feedback` stores a full profile snapshot at submission time (denormalized by design)
- IP addresses are stored server-side only and never exposed in API responses (S-8)

---

## 8. Authentication Flow

Full lifecycle from registration to logout.

```mermaid
sequenceDiagram
    participant C as Client Browser
    participant A as Flask API
    participant DB as MySQL

    rect rgb(230, 245, 230)
        Note over C,DB: Registration
        C->>A: POST /api/register {username, password}
        A->>A: rate limit check (5/min)
        A->>A: hash_password() PBKDF2 260k iterations + random salt
        A->>DB: INSERT users (username, password_hash, salt)
        DB-->>A: OK / 409 username taken
        A-->>C: 201 {message} / 409 error
    end

    rect rgb(230, 235, 250)
        Note over C,DB: Login
        C->>A: POST /api/login {username, password}
        A->>A: rate limit check (5/min)
        A->>DB: SELECT user WHERE username=?
        DB-->>A: user row (hash, salt)
        A->>A: verify_password() hmac.compare_digest()
        A->>A: token = secrets.token_hex(32)
        A->>DB: UPDATE users SET token=?
        DB-->>A: OK
        A-->>C: 200 {token, username}
        C->>C: localStorage rc-token, rc-user
    end

    rect rgb(250, 240, 220)
        Note over C,DB: Authenticated Requests (Profile / Feedback)
        C->>A: GET/PUT /api/profile\nAuthorization: Bearer <token>
        A->>A: require_auth() → get_user_from_token()
        A->>DB: SELECT user WHERE token=?
        DB-->>A: user row
        A->>DB: SELECT/UPSERT profiles WHERE user_id=?
        DB-->>A: profile data
        A-->>C: 200 {profile} / 200 {message}
    end

    rect rgb(250, 230, 230)
        Note over C,DB: Logout
        C->>A: POST /api/logout\nAuthorization: Bearer <token>
        A->>DB: UPDATE users SET token=NULL
        DB-->>A: OK
        A-->>C: 200 {message}
        C->>C: remove rc-token, rc-user from localStorage
    end
```

---

## 9. Claude Code — Skill to Agent Delegation

9 of the 19 slash commands delegate their execution to a specialized subagent. The subagent runs in an isolated context window, keeping verbose output (test logs, scan results, doc generation) out of the main conversation. Only a concise summary returns.

```mermaid
graph LR
    subgraph Skills[".claude/commands/ (slash commands)"]
        RC["/run-ci"]
        TB["/test-browser"]
        SA["/security-audit"]
        GS["/generate-sbom"]
        DV["/docker-verify"]
        GD["/generate-diagrams"]
        GT["/generate-tech-spec"]
        GR["/generate-requirements"]
        GV["/generate-vv-plan"]
    end

    subgraph Agents[".claude/agents/ (subagents)"]
        QA["QA Engineer\n(qa-engineer)"]
        SEC["Security Auditor\n(security-auditor)"]
        OPS["DevOps\n(devops)"]
        DOC["Documentation Writer\n(documentation-writer)"]
        VV["V&V Plan Updater\n(vv-plan-updater)"]
    end

    RC -->|"delegate"| QA
    TB -->|"delegate"| QA
    SA -->|"delegate"| SEC
    GS -->|"delegate"| SEC
    DV -->|"delegate"| OPS
    GD -->|"delegate"| DOC
    GT -->|"delegate"| DOC
    GR -->|"delegate"| DOC
    GV -->|"delegate"| VV
```

---

## 10. Claude Code — Full Agent & Skill Hierarchy

All 19 slash commands and all 10 custom agents in one view. Each agent shows its file name and keyword triggers used for auto-routing. Direct skills route through the default agent; heavy skills delegate to a specialized subagent (isolated context window — only a summary returns to the main thread). Conversational agents are invoked via `@agent` mention or keyword auto-routing.

```mermaid
graph LR
    User(["👤 User"])

    subgraph Direct["📋 Direct Skills (10) — .claude/commands/"]
        S1["/start"]
        S2["/check-stream"]
        S3["/troubleshoot"]
        S4["/test-ratings"]
        S5["/create-pr"]
        S6["/add-endpoint"]
        S7["/add-share-button"]
        S8["/add-dark-style"]
        S9["/update-claude-md"]
        S10["/update-readme-diagrams"]
    end

    subgraph Delegated["⚡ Delegated Skills (9) — isolated context window"]
        D1["/run-ci"]
        D2["/test-browser"]
        D3["/security-audit"]
        D4["/generate-sbom"]
        D5["/docker-verify"]
        D6["/generate-diagrams"]
        D7["/generate-tech-spec"]
        D8["/generate-requirements"]
        D9["/generate-vv-plan"]
    end

    Main["⚙️ Default Agent\nmain thread"]

    subgraph SubAgents["🤖 Delegation-Target Subagents (5) — .claude/agents/"]
        QA["🧪 QA Engineer\nqa-engineer.md\ntest failing · coverage · jest error"]
        SEC["🔒 Security Auditor\nsecurity-auditor.md\nCVE · vulnerability · OWASP"]
        OPS["⚙️ DevOps\ndevops.md\n502 · docker-compose · pipeline"]
        DOC["📝 Documentation Writer\ndocumentation-writer.md\ndiagram · spec · requirements"]
        VV["✅ V&V Plan Updater\nvv-plan-updater.md\nupdate V&V · TC missing · coverage gap"]
    end

    subgraph ConvAgents["💬 Conversational Agents (5) — @mention or auto-route"]
        DBA["🗄️ DBA\ndba.md\nschema · migration · query · index"]
        FR["🎨 Frontend Reviewer\nfrontend-reviewer.md\nXSS · CSS · responsive · a11y"]
        API["🔌 API Designer\napi-designer.md\nendpoint · REST · rate limit · auth"]
        RM["📦 Release Manager\nrelease-manager.md\nready to merge · changelog · semver"]
        PA["⚡ Performance Analyst\nperformance-analyst.md\nslow · caching · CDN · debounce"]
    end

    subgraph Tools["🛠️ Tools"]
        T["Bash · Read · Write · Edit\nGlob · Grep · WebSearch · WebFetch · Agent"]
    end

    User -->|"/command"| Direct
    User -->|"/command (heavy)"| Delegated
    User -->|"@agent or keyword"| ConvAgents
    Direct --> Main
    Main --> Tools
    D1 & D2 -->|"delegate"| QA
    D3 & D4 -->|"delegate"| SEC
    D5 -->|"delegate"| OPS
    D6 & D7 & D8 -->|"delegate"| DOC
    D9 -->|"delegate"| VV
    QA & SEC & OPS & DOC & VV -.->|"summary only"| Main
    SubAgents --> Tools
    ConvAgents --> Tools
```
