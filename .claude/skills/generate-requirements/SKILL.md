<!-- Radio Calico Skill v1.0.0 -->
Generate or update the requirements documentation for Radio Calico.

## Agent
Delegate this entire skill to the **Documentation Writer** subagent (`documentation-writer`).
The Documentation Writer has specialized knowledge of cross-document consistency, Mermaid diagrams, and all docs generation workflows. It will run all steps in an isolated context window and return only a summary to the main conversation.

### Output file

Create/update `docs/requirements.md` with a structured requirements document.

### Document layout

1. **Title & Metadata** — use this exact header layout (logo right, version table left, vertically centered). Read version from `VERSION` file; set date to today:

   ```html
   <table><tr>
   <td valign="middle">

   # Radio Calico - Requirements Documentation

   | Field | Value |
   | --- | --- |
   | **Project** | Radio Calico |
   | **Version** | 1.0.0 |
   | **Date** | YYYY-MM-DD |
   | **Status** | Draft / Approved / Baseline |

   </td>
   <td valign="middle" width="20%" align="right"><img src="../RadioCalicoLogoTM.png" alt="Radio Calico Logo" width="100%"></td>
   </tr></table>

   ---

   ## Table of Contents
   ...

   ---
   ```

2. **Purpose & Scope**
   - System purpose: live audio streaming web player with user engagement features
   - In scope: streaming, ratings, auth, profiles, feedback, sharing
   - Out of scope: content management, payment, ad serving

3. **Stakeholders**
   - End users (listeners), administrators, developers

4. **Functional Requirements**

   For each requirement, use this format:
   ```
   **FR-XXX**: <Title>
   - Priority: Must / Should / Could
   - Description: <What the system shall do>
   - Acceptance criteria: <Measurable conditions>
   - Source: <Which file/endpoint implements this>
   ```

   Derive requirements from these areas by reading the actual code:

   **Audio Streaming (FR-1xx)**:
   - Read `static/js/player.js` for: HLS playback, quality selection (FLAC/AAC), volume/mute, play/pause
   - Read `static/index.html` for: player bar UI, stream quality display

   **Track Metadata (FR-2xx)**:
   - Read `static/js/player.js` for: metadata fetching, latency compensation, artwork from iTunes, duration display, history accumulation

   **Ratings (FR-3xx)**:
   - Read `api/app.py` endpoints: POST /api/ratings, GET /api/ratings, GET /api/ratings/summary, GET /api/ratings/check
   - IP-based deduplication, thumbs up/down, summary badges

   **Authentication (FR-4xx)**:
   - Read `api/app.py` endpoints: POST /api/register, POST /api/login, POST /api/logout
   - Password requirements (8-128 chars), PBKDF2 hashing, token-based auth, rate limiting

   **User Profile (FR-5xx)**:
   - Read `api/app.py` endpoints: GET /api/profile, PUT /api/profile
   - Nickname, email, genres (16 tags), about text, upsert behavior

   **Feedback (FR-6xx)**:
   - Read `api/app.py` endpoint: POST /api/feedback
   - Message with profile snapshot, social sharing (Twitter, Telegram)

   **Social Sharing (FR-7xx)**:
   - Read `static/js/player.js` for: WhatsApp, X/Twitter, Telegram share intents
   - Spotify, YouTube Music, Amazon Music search links
   - Recently played share with numbered list

   **Theme & Settings (FR-8xx)**:
   - Dark/light theme toggle, stream quality toggle, localStorage persistence

5. **Non-Functional Requirements**

   **NFR-1xx: Performance**:
   - Read `nginx/nginx.conf` for: gzip, caching, WebP images
   - Read `static/js/player.js` for: iTunes cache (24h TTL), metadata debounce (3s)
   - API pagination (limit/offset)

   **NFR-2xx: Security**:
   - Read `api/app.py` for: PBKDF2 260k iterations, timing-safe comparison, parameterized SQL
   - Read `nginx/nginx.conf` for: CSP, X-Frame-Options, CORS, rate limiting
   - 6 security scanning tools

   **NFR-3xx: Reliability**:
   - HLS retry with exponential backoff (max 10 retries)
   - Docker health checks on all containers
   - Graceful error handling (no crashes on API failure)

   **NFR-4xx: Observability**:
   - Structured JSON logging (Python, nginx, JS)
   - X-Request-ID cross-layer correlation

   **NFR-5xx: Maintainability**:
   - 582 tests across 6 suites, 95% Python coverage, 96% JS coverage
   - 4 linters, CI/CD with 13 GitHub Actions jobs
   - 18 Claude Code slash commands + 9 custom agents

   **NFR-6xx: Compatibility**:
   - HLS.js for non-Safari, native HLS for Safari
   - Responsive layout (breakpoint 700px)
   - WebP with PNG fallback

6. **Traceability Matrix**
   - Table mapping each FR/NFR to: implementation file, test file, test IDs

### Steps

1. **Read** all source files to derive requirements from actual behavior
2. **Number** each requirement sequentially (FR-101, FR-102, etc.)
3. **Map** each requirement to its implementation and test
4. **Generate** the full document following the layout above
5. **Report** the total number of requirements generated