<table><tr>
<td valign="middle">

# Radio Calico - Requirements Documentation

| Field | Value |
| --- | --- |
| **Project** | Radio Calico |
| **Version** | 1.0.0 |
| **Date** | 2026-03-17 |
| **Status** | Approved |

</td>
<td valign="middle" width="20%" align="right"><img src="../RadioCalicoLogoTM.png" alt="Radio Calico Logo" width="100%"></td>
</tr></table>

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Stakeholders](#2-stakeholders)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [Traceability Matrix](#5-traceability-matrix)

---

## 1. Purpose & Scope

Radio Calico is a live audio streaming web player that delivers lossless and high-fidelity audio via HLS from AWS CloudFront. It provides a browser-based interface for listeners to play/pause a live stream, view track metadata with album artwork, rate tracks, manage user profiles, submit feedback, and share music on social platforms.

**In scope:** Audio playback (FLAC/AAC), metadata display, ratings, user accounts, profiles, feedback, social sharing, theme settings, Docker deployment, CI/CD pipeline, security hardening.

**Out of scope:** Mobile native apps, offline playback, playlist management, payment processing, ad insertion, server-side stream encoding.

---

## 2. Stakeholders

| Role                | Responsibility                                                    |
|---------------------|-------------------------------------------------------------------|
| Listeners           | Play the live stream, rate tracks, share music, submit feedback   |
| Registered Users    | All listener actions plus profile management and feedback via API |
| Station Operator    | Manages stream encoding, CloudFront distribution, metadata feed   |
| Developer / DevOps  | Maintains codebase, CI/CD pipeline, Docker deployment             |

---

## 3. Functional Requirements

### FR-1xx: Audio Streaming

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-101  | Play/Pause Toggle              | Must     | The user can toggle playback of the live HLS audio stream with a single play/pause button. A spinner icon is shown while buffering, a pause icon when playing, and a play icon when paused. | Clicking the play button starts audio; clicking again pauses it. Icon reflects the current state (play/pause/spinner). | `static/js/player.js` — `togglePlay()`, `showPlayIcon()` |
| FR-102  | FLAC Lossless Streaming        | Must     | The player supports FLAC Hi-Res lossless audio (48 kHz) as the default stream quality via HLS. | When quality is set to FLAC, the HLS level is forced to the FLAC variant (codec containing "flac"). | `static/js/player.js` — `initHls()`, MANIFEST_PARSED handler |
| FR-103  | AAC Hi-Fi Streaming            | Must     | The player supports AAC Hi-Fi (211 kbps) as an alternative stream quality. | When quality is set to AAC, the HLS level is forced to the AAC variant (codec containing "mp4a"). | `static/js/player.js` — `initHls()`, MANIFEST_PARSED handler |
| FR-104  | Quality Switch                 | Must     | The user can switch between FLAC and AAC quality without losing playback state. The HLS player reinitializes with the selected codec and resumes playback if previously playing. | Changing the stream quality radio button reinitializes HLS with the new level and resumes playback. Choice is persisted to `localStorage` key `rc-stream-quality`. | `static/js/player.js` — `applyStreamQuality()` |
| FR-105  | Volume Control                 | Must     | A slider control adjusts the audio volume from 0 to 1 in real time. Adjusting volume above 0 automatically unmutes if muted. | Moving the volume slider changes `audio.volume`. If muted and volume > 0, mute is toggled off. | `static/js/player.js` — `volumeEl` input handler |
| FR-106  | Mute Toggle                    | Must     | A mute button toggles audio mute on/off. The icon toggles between volume and mute states. | Clicking the mute button toggles `audio.muted`. Icon switches between volume and mute SVGs. | `static/js/player.js` — `muteBtn` click handler |
| FR-107  | HLS Fatal Error Retry          | Must     | When a fatal HLS error occurs, the player automatically retries with exponential backoff starting at 4 seconds, doubling up to 60 seconds, for a maximum of 10 attempts. | On fatal HLS error, retry count increments, delay doubles (capped at 60s), and `initHls()` is called again. After 10 retries, no further attempts are made. | `static/js/player.js` — `HLS_RETRY_BASE_MS`, `HLS_RETRY_MAX_MS`, `HLS_MAX_RETRIES`, ERROR handler |
| FR-108  | Safari Native HLS Fallback     | Must     | On browsers that do not support HLS.js but support native HLS (Safari), the player sets the audio source directly and enables playback. | If `Hls.isSupported()` is false but `audio.canPlayType('application/vnd.apple.mpegurl')` is true, `audio.src` is set to `STREAM_URL` and play button is enabled on `loadedmetadata`. | `static/js/player.js` — boot section |
| FR-109  | Elapsed Time Display           | Must     | The player displays elapsed time using wall-clock measurement (`Date.now() - songStartTime`) and total duration from iTunes, formatted as `elapsed / total` or `elapsed / Live`. | The `timeupdate` event updates `barTime.textContent` with `formatTime(elapsed) / formatTime(total)` or `formatTime(elapsed) / Live`. | `static/js/player.js` — `timeupdate` handler, `formatTime()` |

### FR-2xx: Track Metadata

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-201  | Current Track Display          | Must     | The player displays the current artist, title, and album name in the Now Playing area. | `artistEl`, `trackEl`, `albumEl` are updated with metadata from CloudFront JSON. Default display is "Radio Calico / Live Stream". | `static/js/player.js` — `updateTrack()` |
| FR-202  | Metadata from CloudFront JSON  | Must     | Track metadata is fetched from a CloudFront JSON endpoint (`metadatav2.json`), not from ID3 tags. The endpoint provides current track plus 5 previous tracks. | `fetchMetadata()` fetches from `METADATA_URL` with `cache: 'no-store'` and extracts `artist`, `title`, `album`, and `prev_artist_1..5` / `prev_title_1..5`. | `static/js/player.js` — `fetchMetadata()` |
| FR-203  | Metadata Latency Compensation  | Must     | Metadata display is delayed by HLS stream latency (fallback 6s, max 15s) so the UI updates when the listener actually hears the new song, not when CloudFront publishes it. | `fetchMetadata()` uses `setTimeout` with `hls.latency` (or `LATENCY_FALLBACK_SEC`) before calling `updateTrack()`. `pendingTrackKey` prevents duplicate timers for the same track. | `static/js/player.js` — `fetchMetadata()`, `pendingTrackUpdate`, `pendingTrackKey` |
| FR-204  | Metadata Fetch on Fragment Change | Must  | Metadata fetching is triggered by HLS.js `FRAG_CHANGED` events (not a fixed timer), debounced to a minimum 3-second interval. | `FRAG_CHANGED` calls `triggerMetadataFetch()` which checks `METADATA_DEBOUNCE_MS` (3000ms) elapsed since last fetch. | `static/js/player.js` — `triggerMetadataFetch()`, `METADATA_DEBOUNCE_MS` |
| FR-205  | Album Artwork from iTunes      | Must     | Album artwork is fetched from the iTunes Search API using artist + title as the search query. Images are displayed at 600x600 resolution; a placeholder ("music note") is shown on failure. | `fetchArtwork()` calls iTunes API, extracts `artworkUrl100`, replaces size with `600x600`, and sets `artworkEl.innerHTML`. On failure, a `div.artwork-placeholder` with "music note" is shown. | `static/js/player.js` — `fetchArtwork()`, `ARTWORK_SIZE` |
| FR-206  | Track Duration from iTunes     | Should   | Track duration is obtained from the iTunes API `trackTimeMillis` field and used for the elapsed/total time display. | `fetchArtwork()` sets `trackDuration = result.trackTimeMillis / 1000`. If no result, `trackDuration = null` and "Live" is shown. | `static/js/player.js` — `fetchArtwork()`, `timeupdate` handler |
| FR-207  | Recently Played History        | Must     | The player accumulates up to 20 previously played tracks, merging fresh entries from CloudFront JSON with older client-side history. Displayed as a scrollable list with album names and rating badges. | `pushHistory()` unshifts entries, caps at `MAX_HISTORY` (20). `fetchMetadata()` merges fresh (5) + kept entries. `renderHistory()` renders the list with rating summary badges. | `static/js/player.js` — `pushHistory()`, `renderHistory()`, `fetchMetadata()` |
| FR-208  | History Filtering              | Should   | Users can filter the Recently Played list by All, Liked, or Disliked tracks using filter buttons. | `.prev-filter` buttons set `prevFilter` to `all`, `up`, or `down`. `getFilteredHistory()` filters by `lastSummary` likes/dislikes. Filter change triggers `fetchMetadata()` to refresh. | `static/js/player.js` — `getFilteredHistory()`, filter button handlers |
| FR-209  | History Limit Dropdown         | Should   | A dropdown allows users to choose how many recently played tracks to display (5, 10, 15, or 20). | `#prev-limit` change handler sets `historyLimit` and calls `fetchMetadata()`. `getFilteredHistory()` slices to `historyLimit`. | `static/js/player.js` — `#prev-limit` handler |
| FR-210  | Album Name Backfill from iTunes | Could   | History entries missing album names have them fetched asynchronously from the iTunes API. | `fetchMetadata()` iterates history entries with empty album, calls `fetchItunesCached()`, sets `collectionName`, and re-renders. | `static/js/player.js` — `fetchMetadata()` album backfill loop |
| FR-211  | ID3 Metadata Fallback          | Could    | An ID3v2 parser is implemented as a fallback for extracting TPE1 (artist), TIT2 (title), and TALB (album) from raw HLS fragment metadata. | `parseID3Frames()` decodes ID3v2 tags with UTF-8/UTF-16/ISO-8859-1 support. `FRAG_PARSING_METADATA` handler calls it. Currently unused because the stream does not embed ID3 tags. | `static/js/player.js` — `parseID3Frames()`, `handleMetadataFields()` |
| FR-212  | Source Quality Display         | Could    | The current audio source quality (codec, bitrate, sample rate, bit depth) is displayed in the UI. | `LEVEL_LOADED` handler and `fetchMetadata()` update `#source-quality` text with codec/bitrate/sample_rate/bit_depth info. | `static/js/player.js` — `LEVEL_LOADED` handler, `fetchMetadata()` |
| FR-213  | Initial Metadata Fetch         | Must     | One metadata fetch occurs at boot so the UI shows the current track before the user presses play. | `fetchMetadata()` is called once at the bottom of the boot section. | `static/js/player.js` — boot section |

### FR-3xx: Ratings

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-301  | Submit Rating (Thumbs Up/Down) | Must     | Users can rate the currently playing track with a thumbs up (score=1) or thumbs down (score=0) via the API. | `POST /api/ratings` with `{station, score}` inserts a row. Returns 201 on success. Score must be 0 or 1; other values return 400. | `api/app.py` — `post_rating()`, `static/js/player.js` — `submitRating()` |
| FR-302  | IP-Based Deduplication         | Must     | Each IP address can only rate a given track once. Duplicate attempts return HTTP 409. | `ratings` table has `UNIQUE KEY (station, ip)`. `IntegrityError` on duplicate returns `{"error": "already rated"}` with status 409. | `api/app.py` — `post_rating()`, `db/init.sql` |
| FR-303  | Check If Rated                 | Must     | The frontend checks whether the current user (by IP) has already rated the displayed track, and disables rating buttons accordingly. | `GET /api/ratings/check?station=...` returns `{rated: true/false, score}`. Frontend calls `checkIfRated()` on track change and toggles `.rated` class on buttons. | `api/app.py` — `check_rating()`, `static/js/player.js` — `checkIfRated()`, `updateRatingUI()` |
| FR-304  | Ratings Summary                | Must     | An endpoint returns aggregated likes and dislikes per track (station), used for rating badges in the Recently Played list. | `GET /api/ratings/summary` returns `{station: {likes, dislikes}}`. `renderHistory()` fetches this and renders badges. | `api/app.py` — `get_ratings_summary()`, `static/js/player.js` — `renderHistory()` |
| FR-305  | List All Ratings               | Should   | An endpoint returns all individual ratings with pagination support (default 100, max 500). IP addresses are not exposed. | `GET /api/ratings?limit=N&offset=N` returns `[{id, station, score, created_at}]` ordered by most recent. `Cache-Control: public, max-age=30`. | `api/app.py` — `get_ratings()` |
| FR-306  | Rating Count Badges            | Must     | The Now Playing area shows live like/dislike counts for the current track, updated after each rating submission. | `fetchTrackRatings()` fetches `/api/ratings/summary` and updates `rateUpCount` / `rateDownCount` text content. Called by `updateRatingUI()` and after `submitRating()`. | `static/js/player.js` — `fetchTrackRatings()`, `updateRatingUI()` |

### FR-4xx: Authentication

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-401  | User Registration              | Must     | Users can create an account with a username (max 50 chars) and password (8-128 chars). Rate-limited to 5 requests/minute. | `POST /api/register` with `{username, password}`. Returns 201 on success, 400 for validation errors, 409 if username taken, 429 if rate limited. | `api/app.py` — `register()` |
| FR-402  | User Login                     | Must     | Users can authenticate with username and password to receive a bearer token. Rate-limited to 5 requests/minute. | `POST /api/login` with `{username, password}`. Returns `{token, username}` on success (200), 401 on invalid credentials, 429 if rate limited. Token is a 64-char hex string (`secrets.token_hex(32)`). | `api/app.py` — `login()` |
| FR-403  | User Logout                    | Must     | Authenticated users can invalidate their token, ending the session. | `POST /api/logout` with `Authorization: Bearer <token>`. Sets `token = NULL` in the database. Returns 200 on success, 401 if unauthenticated. | `api/app.py` — `logout()` |
| FR-404  | Token-Based Authentication     | Must     | Protected endpoints require an `Authorization: Bearer <token>` header. Invalid or missing tokens return 401. | `require_auth()` extracts the bearer token, looks up the user via `get_user_from_token()`, and returns `None` on failure. | `api/app.py` — `require_auth()`, `get_user_from_token()` |
| FR-405  | Client-Side Session Persistence | Must    | Auth token and username are stored in `localStorage` (`rc-token`, `rc-user`) and restored on page load. | On login, `localStorage.setItem('rc-token', token)`. On logout, `localStorage.removeItem('rc-token')`. On boot, if both exist, `showProfileView()` is called. | `static/js/player.js` — login/logout/boot handlers |
| FR-406  | Password Validation            | Must     | Passwords must be between 8 and 128 characters. Violations return 400 with a descriptive error message. | `register()` checks `len(password) < 8` and `len(password) > 128`, returning appropriate error messages. | `api/app.py` — `register()` |

### FR-5xx: User Profile

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-501  | View Profile                   | Must     | Authenticated users can retrieve their profile (nickname, email, genres, about). | `GET /api/profile` with bearer token. Returns profile fields or empty strings if no profile exists. Status 200. | `api/app.py` — `get_profile()` |
| FR-502  | Update Profile (Upsert)        | Must     | Authenticated users can create or update their profile. If no profile exists, one is created (upsert). Field lengths are enforced server-side. | `PUT /api/profile` with `{nickname, email, genres, about}`. Server truncates: nickname 100, email 255, genres 500, about 1000 chars. Creates profile if none exists (INSERT), updates if exists (UPDATE). | `api/app.py` — `update_profile()` |
| FR-503  | Genre Selection                | Should   | The profile form offers 16 music genre checkboxes. Selected genres are stored as a comma-separated string. | Profile form contains `#genre-grid` with checkboxes. `loadProfile()` parses comma-separated genres and checks matching boxes. Save collects checked values and joins with commas. | `static/js/player.js` — `loadProfile()`, profile form submit handler |
| FR-504  | Profile Form in Drawer         | Must     | The profile section is displayed in the side drawer when the user is logged in, replacing the login/register form. | `showProfileView()` hides `drawerAuth`, shows `drawerProfile` and `drawerFeedback`. Displays "Logged in as {username}" and calls `loadProfile()`. | `static/js/player.js` — `showProfileView()`, `showAuthView()` |

### FR-6xx: Feedback

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-601  | Submit Feedback Message         | Must     | Authenticated users can submit a feedback message. The feedback record stores a snapshot of the user's profile data at submission time. | `POST /api/feedback` with `{message}` and bearer token. Stores message + email, nickname, genres, about, username, and IP. Returns 201. Returns 401 if not authenticated, 400 if empty message. | `api/app.py` — `post_feedback()` |
| FR-602  | Feedback via X/Twitter          | Should   | Users can send feedback through X/Twitter with a pre-filled tweet mentioning @RadioCalico. | `#feedback-twitter` click handler opens `https://x.com/intent/tweet?text=...` with the feedback message prefixed by "Hey @RadioCalico,". | `static/js/player.js` — `#feedback-twitter` handler |
| FR-603  | Feedback via Telegram           | Should   | Users can send feedback through Telegram with a pre-filled share message. | `#feedback-telegram` click handler opens `https://t.me/share/url?text=...` with the feedback message prefixed by "Radio Calico feedback:". | `static/js/player.js` — `#feedback-telegram` handler |

### FR-7xx: Social Sharing

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-701  | Share Now Playing on WhatsApp   | Must     | Users can share the currently playing track on WhatsApp with formatted text including artist, title, album, and artwork URL. | `#share-whatsapp` opens `https://wa.me/?text=...` with `getShareText()` output. Text format: `Listening to "Title" by Artist (Album) on Radio Calico!\n\nAlbum cover: {300x300 URL}`. | `static/js/player.js` — `getShareText()`, `#share-whatsapp` handler |
| FR-702  | Share Now Playing on X/Twitter  | Must     | Users can share the currently playing track on X/Twitter via tweet intent. | `#share-twitter` opens `https://x.com/intent/tweet?text=...` with `getShareText()` output. | `static/js/player.js` — `#share-twitter` handler |
| FR-703  | Share Now Playing on Telegram   | Must     | Users can share the currently playing track on Telegram. | `#share-telegram` opens `https://t.me/share/url?text=...` with `getShareText()` output. | `static/js/player.js` — `#share-telegram` handler |
| FR-704  | Search on Spotify               | Should   | Users can search for the current track on Spotify. | `#share-spotify` opens `https://open.spotify.com/search/{artist} {title}` in a new tab. | `static/js/player.js` — `#share-spotify` handler |
| FR-705  | Search on YouTube Music         | Should   | Users can search for the current track on YouTube Music. | `#share-ytmusic` opens `https://music.youtube.com/search?q={artist} {title}` in a new tab. | `static/js/player.js` — `#share-ytmusic` handler |
| FR-706  | Search on Amazon Music          | Should   | Users can search for the current track on Amazon Music (digital music filter). | `#share-amazon` opens `https://www.amazon.com/s?k={artist} {title}&i=digital-music` in a new tab. | `static/js/player.js` — `#share-amazon` handler |
| FR-707  | Share Recently Played on WhatsApp | Should | Users can share a numbered list of recently played tracks (respecting filter/limit) on WhatsApp with plain-text rating counts. | `#prev-share-whatsapp` opens WhatsApp with `getRecentlyPlayedText()` output. Format: `"N. Title by Artist (Album) [N likes / N unlikes]"`. No-op if empty. | `static/js/player.js` — `getRecentlyPlayedText()`, `#prev-share-whatsapp` handler |
| FR-708  | Share Recently Played on X/Twitter | Should | Users can share a numbered list of recently played tracks on X/Twitter. | `#prev-share-twitter` opens X tweet intent with `getRecentlyPlayedText()` output. No-op if empty. | `static/js/player.js` — `#prev-share-twitter` handler |
| FR-709  | Artwork URL in Share Text       | Should   | The Now Playing share text includes the 300x300 album artwork URL at the bottom for preview on social platforms. | `getShareText()` appends `\n\nAlbum cover: {URL}` using `getArtworkUrl()` which replaces `600x600` with `300x300` in the iTunes image URL. | `static/js/player.js` — `getArtworkUrl()`, `getShareText()` |
| FR-710  | Plain Text Ratings in Share     | Must     | Shared messages use plain text `[N likes / N unlikes]` for rating counts (no emoji) to avoid URL encoding corruption on some platforms. | `getRecentlyPlayedText()` uses `[${r.likes} likes / ${r.dislikes} unlikes]`. No emoji characters in URL-encoded text. | `static/js/player.js` — `getRecentlyPlayedText()` |

### FR-8xx: Theme & Settings

| ID      | Title                          | Priority | Description | Acceptance Criteria | Source |
|---------|--------------------------------|----------|-------------|---------------------|--------|
| FR-801  | Dark/Light Theme Toggle         | Must     | Users can switch between dark and light themes via radio buttons in a settings dropdown. Default is dark. | `applyTheme()` sets `data-theme` attribute on `<html>`, persists to `localStorage` key `rc-theme`, and checks the matching radio button. CSS uses `[data-theme="dark"]` selectors to override custom properties. | `static/js/player.js` — `applyTheme()`, `static/css/player.css` |
| FR-802  | Theme Persistence               | Must     | The selected theme is persisted across page loads via `localStorage`. | On boot, `savedTheme = localStorage.getItem('rc-theme') || 'dark'` and `applyTheme(savedTheme)` is called. | `static/js/player.js` — boot section |
| FR-803  | Stream Quality Settings         | Must     | The settings dropdown includes FLAC/AAC radio buttons for stream quality selection. The current quality label is displayed in the UI. | `updateStreamQualityDisplay()` sets `#stream-quality` text to `Stream quality: {label}`. Radio buttons trigger `applyStreamQuality()`. | `static/js/player.js` — `updateStreamQualityDisplay()`, quality radio handlers |
| FR-804  | Settings Gear Dropdown          | Must     | A gear icon in the navbar opens a dropdown with theme and quality settings. Clicking outside closes it. | `#settings-btn` click toggles `.open` on `#settings-dropdown`. Document click handler removes `.open` if target is outside dropdown. | `static/js/player.js` — settings button/dropdown handlers |
| FR-805  | Hamburger Menu & Side Drawer    | Must     | A hamburger icon in the navbar opens a slide-out drawer from the left. An overlay dims the background. Clicking the overlay or X button closes the drawer. | `openDrawer()` adds `.open` class to drawer and overlay. `closeDrawer()` removes it. Handlers on `#menu-btn`, `#drawer-close`, and `#drawer-overlay`. | `static/js/player.js` — `openDrawer()`, `closeDrawer()` |
| FR-806  | HTML Escaping                   | Must     | All user-supplied or metadata text inserted into the DOM via `innerHTML` is escaped to prevent XSS. | `escHtml()` replaces `&`, `<`, `>`, `"`, `'` with HTML entities. Used in `renderHistory()`, `fetchArtwork()`, and share text rendering. | `static/js/player.js` — `escHtml()` |

---

## 4. Non-Functional Requirements

### NFR-1xx: Performance

| ID       | Title                          | Priority | Description | Acceptance Criteria | Source |
|----------|--------------------------------|----------|-------------|---------------------|--------|
| NFR-101  | Gzip Compression               | Must     | Nginx compresses text responses (HTML, CSS, JS, JSON, SVG) with gzip for files larger than 256 bytes. | `gzip on; gzip_types text/plain text/css application/json application/javascript text/javascript text/xml image/svg+xml; gzip_min_length 256;` is configured. | `nginx/nginx.conf` |
| NFR-102  | Static Asset Caching            | Should   | Static assets (CSS, JS, images, fonts) are cached aggressively by the browser with a 7-day expiry and `immutable` directive. | Nginx location block for `\.(css|js|png|jpg|jpeg|gif|ico|svg|webp|woff2?)$` sets `expires 7d` and `Cache-Control: public, immutable`. | `nginx/nginx.conf` |
| NFR-103  | DNS Prefetch                    | Should   | DNS resolution for external services (iTunes API, CloudFront CDN, jsDelivr CDN) is initiated early via `<link rel="dns-prefetch">` hints. | `index.html` contains `dns-prefetch` links for `itunes.apple.com`, `d3d4yli4hf5bmh.cloudfront.net`, and `cdn.jsdelivr.net`. | `static/index.html` |
| NFR-104  | Font Preconnect                 | Should   | Connections to Google Fonts are established early via `<link rel="preconnect">` for both `fonts.googleapis.com` and `fonts.gstatic.com`. | `index.html` contains `preconnect` links for Google Fonts domains. | `static/index.html` |
| NFR-105  | iTunes API Client-Side Cache    | Should   | iTunes API responses are cached in `localStorage` with a 24-hour TTL to reduce redundant API calls. | `fetchItunesCached()` stores `{data, ts}` under `rc-itunes-{query}` key. Cached results are returned if within `ITUNES_CACHE_TTL_MS` (24h). | `static/js/player.js` — `fetchItunesCached()` |
| NFR-106  | Ratings API Pagination          | Should   | The ratings listing endpoint supports `limit` and `offset` query parameters with sensible defaults (100) and maximums (500). | `GET /api/ratings?limit=N&offset=N`. Limit capped at 500, offset minimum 0. Default limit is 100. | `api/app.py` — `get_ratings()` |
| NFR-107  | WebP Image Format               | Should   | The logo and favicon use WebP format with PNG fallback via `<source srcset>` and `<picture>` elements for smaller file sizes. | `index.html` uses `<source srcset="/logo.webp" type="image/webp">` and `<link rel="icon" href="/favicon.webp" type="image/webp">`. | `static/index.html` |
| NFR-108  | Ratings Response Caching        | Could    | The ratings list endpoint returns a `Cache-Control: public, max-age=30` header to allow brief client and CDN caching. | `get_ratings()` sets `response.headers["Cache-Control"] = "public, max-age=30"`. | `api/app.py` — `get_ratings()` |
| NFR-109  | Metadata Fetch Debouncing       | Must     | Metadata fetches are debounced to a minimum 3-second interval to avoid excessive requests during rapid fragment changes. | `triggerMetadataFetch()` checks `Date.now() - lastMetadataFetch < METADATA_DEBOUNCE_MS` (3000ms) and skips if too recent. | `static/js/player.js` — `triggerMetadataFetch()` |

### NFR-2xx: Security

| ID       | Title                          | Priority | Description | Acceptance Criteria | Source |
|----------|--------------------------------|----------|-------------|---------------------|--------|
| NFR-201  | Password Hashing (PBKDF2)      | Must     | Passwords are hashed with PBKDF2-HMAC-SHA256 using 260,000 iterations and a random 16-byte salt. | `hash_password()` uses `hashlib.pbkdf2_hmac("sha256", ..., 260000)` with `secrets.token_hex(16)` salt. | `api/app.py` — `hash_password()` |
| NFR-202  | Timing-Safe Password Comparison | Must     | Password verification uses constant-time comparison to prevent timing attacks. | `verify_password()` uses `hmac.compare_digest(check, hashed)`. | `api/app.py` — `verify_password()` |
| NFR-203  | Content Security Policy (CSP)   | Must     | Nginx enforces a strict CSP header that restricts script sources, style sources, image sources, media sources, and connection targets to known origins. | CSP header includes: `default-src 'self'`, `script-src 'self' https://cdn.jsdelivr.net`, `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`, `img-src 'self' https://is1-ssl.mzstatic.com data:`, `media-src 'self' https://d3d4yli4hf5bmh.cloudfront.net blob:`, `connect-src 'self' https://d3d4yli4hf5bmh.cloudfront.net https://itunes.apple.com`, `frame-ancestors 'self'`, `form-action 'self'`, `base-uri 'self'`. | `nginx/nginx.conf` |
| NFR-204  | Security Response Headers       | Must     | Nginx adds security headers to all responses: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `Cross-Origin-Resource-Policy: same-origin`. | All six security headers are present in every response via `add_header ... always`. | `nginx/nginx.conf` |
| NFR-205  | Rate Limiting                   | Must     | Registration and login endpoints are rate-limited to 5 requests per minute per IP address using in-memory storage. | `@limiter.limit("5/minute")` decorator on `register()` and `login()`. `Limiter` uses `storage_uri="memory://"`. Returns 429 when exceeded. | `api/app.py` — `register()`, `login()`, `limiter` |
| NFR-206  | Parameterized SQL Queries       | Must     | All database queries use parameterized placeholders (`%s`) to prevent SQL injection. | Every `cursor.execute()` call uses `%s` placeholders with a parameters tuple. No string interpolation in SQL. | `api/app.py` — all query calls |
| NFR-207  | CORS Configuration              | Must     | CORS is configured via the `CORS_ORIGIN` environment variable, defaulting to the local development origin. | `CORS(app, origins=[os.environ.get("CORS_ORIGIN", "http://127.0.0.1:5000")])`. | `api/app.py` |
| NFR-208  | Server Version Hiding           | Should   | Nginx hides its version number from response headers. | `server_tokens off;` in nginx.conf. | `nginx/nginx.conf` |
| NFR-209  | Non-Root Container User         | Must     | The Docker container runs as a non-root `appuser` for both dev and prod targets. | Dockerfile creates `appuser` group and user, sets `chown`, and `USER appuser` before CMD. | `Dockerfile` |
| NFR-210  | IP Address Privacy              | Should   | The ratings listing endpoint does not expose IP addresses in responses. | `get_ratings()` SELECT only returns `id, station, score, created_at` -- no `ip` column. | `api/app.py` — `get_ratings()` |
| NFR-211  | Security Scanning Tools         | Must     | The CI pipeline includes 6 security scanning tools: Bandit (Python SAST), Safety (Python dependencies), npm audit (JS dependencies), Hadolint (Dockerfile linting), Trivy (Docker image vulnerabilities), and OWASP ZAP (DAST). | Makefile targets: `bandit`, `safety`, `audit-npm`, `hadolint`, `trivy`, `zap`. `make security` runs Bandit + Safety + npm audit. `make security-all` runs all 6. | `Makefile` |
| NFR-212  | X-Forwarded-For IP Extraction   | Should   | The backend correctly extracts the client IP from the `X-Forwarded-For` header when behind a reverse proxy, taking only the first IP in the chain. | `ip = request.headers.get("X-Forwarded-For", request.remote_addr) or ""` followed by `ip.split(",")[0].strip()`. Used in ratings, feedback, and logging. | `api/app.py` — `post_rating()`, `check_rating()`, `post_feedback()`, `after_request_logging()` |
| NFR-213  | Permissions Policy              | Should   | Nginx disables access to sensitive browser APIs (camera, microphone, geolocation, payment) via the Permissions-Policy header. | `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`. | `nginx/nginx.conf` |

### NFR-3xx: Reliability

| ID       | Title                          | Priority | Description | Acceptance Criteria | Source |
|----------|--------------------------------|----------|-------------|---------------------|--------|
| NFR-301  | HLS Exponential Backoff Retry  | Must     | Fatal HLS errors trigger automatic reconnection with exponential backoff (4s base, 60s max, 10 max retries). | `hlsRetryCount` increments on each fatal error. Delay = `min(4000 * 2^(count-1), 60000)`. `initHls()` is called after delay. Stops after 10 retries. | `static/js/player.js` — ERROR handler |
| NFR-302  | Docker Health Checks           | Must     | All Docker services (db, app, nginx, app-dev) have health checks to ensure container orchestration only routes traffic to healthy instances. | MySQL: `mysqladmin ping`. App (prod): Python urllib to `/api/ratings/summary`. Nginx: `wget --spider http://localhost/health`. App-dev: `curl -f http://localhost:5000/`. All with interval, timeout, and retries configured. | `docker-compose.yml` |
| NFR-303  | Nginx Health Endpoint          | Must     | Nginx exposes a `/health` endpoint returning 200 "ok" for load balancer and orchestration health checks. Access logs are suppressed for this path. | `location /health { access_log off; return 200 "ok"; add_header Content-Type text/plain; }`. | `nginx/nginx.conf` |
| NFR-304  | Proxy Timeouts                 | Should   | Nginx configures explicit timeouts for proxied API requests to prevent hung connections. | `proxy_connect_timeout 10s; proxy_read_timeout 30s; proxy_send_timeout 30s;` in the `/api/` location block. | `nginx/nginx.conf` |
| NFR-305  | Service Restart Policy          | Should   | Docker services are configured with `restart: unless-stopped` to recover from transient failures. | All services in `docker-compose.yml` have `restart: unless-stopped`. | `docker-compose.yml` |
| NFR-306  | Graceful Degradation on API Failure | Should | Frontend gracefully handles API failures (ratings, metadata, profile) by logging warnings and showing fallback UI text instead of crashing. | All `fetch()` calls are wrapped in try/catch with `log.warn()` and user-friendly fallback messages (e.g., "Could not connect", fallback to cached `lastSummary`). | `static/js/player.js` — all async functions |

### NFR-4xx: Observability

| ID       | Title                          | Priority | Description | Acceptance Criteria | Source |
|----------|--------------------------------|----------|-------------|---------------------|--------|
| NFR-401  | Structured JSON Logging (Backend) | Must  | The Flask backend emits structured JSON logs with timestamp, level, logger name, and message for all requests. | `python-jsonlogger` `JsonFormatter` formats logs as JSON with `timestamp`, `level`, `logger`, `message` fields. `werkzeug` default logs are suppressed. | `api/app.py` — logging setup |
| NFR-402  | X-Request-ID Propagation       | Must     | Every request is tagged with an `X-Request-ID` (from the incoming header or auto-generated) that is returned in the response and included in log entries. | `before_request_logging()` sets `g.request_id` from header or `uuid.uuid4().hex[:12]`. `after_request_logging()` adds it to the response header and log data. Nginx sets `X-Request-ID $request_id` on proxied requests. | `api/app.py` — `before_request_logging()`, `after_request_logging()`, `nginx/nginx.conf` |
| NFR-403  | Request Duration Logging       | Should   | Each request log entry includes the processing duration in milliseconds. | `g.start_time = time.time()` in `before_request`. `duration_ms = round((time.time() - g.start_time) * 1000, 1)` in `after_request`. | `api/app.py` — `before_request_logging()`, `after_request_logging()` |
| NFR-404  | Log Level by Status Code       | Should   | Requests are logged at different levels based on response status: INFO for 2xx/3xx, WARNING for 4xx, ERROR for 5xx. | `after_request_logging()` uses `logger.error` for 500+, `logger.warning` for 400+, `logger.info` otherwise. | `api/app.py` — `after_request_logging()` |
| NFR-405  | Structured JSON Logging (Nginx) | Should  | Nginx access logs use a structured JSON format matching the backend log schema. | `log_format json_log` outputs JSON with `timestamp`, `level`, `logger`, `message`, `method`, `path`, `status`, `duration_ms`, `bytes`, `ip`, `user_agent`, `upstream_time`, `request_id`. | `nginx/nginx.conf` — `log_format json_log` |
| NFR-406  | Structured Logging (Frontend)   | Should  | The frontend emits structured JSON log entries to the browser console with timestamp, level, logger name, and context. | `log._emit()` builds a JSON object with `timestamp`, `level`, `logger: 'player'`, `message`, and spread `context`. Uses `console.error`/`console.warn`/`console.log` by level. | `static/js/player.js` — `log` object |

### NFR-5xx: Maintainability

| ID       | Title                          | Priority | Description | Acceptance Criteria | Source |
|----------|--------------------------------|----------|-------------|---------------------|--------|
| NFR-501  | Unit Test Coverage             | Must     | The project maintains comprehensive test suites: 61 Python unit tests (98%+ coverage) and 162 JavaScript unit tests. | `make test-py` runs 61 tests. `make test-js` runs 162 tests. `make coverage` fails if Python coverage drops below 98%. | `api/test_app.py`, `static/js/player.test.js`, `Makefile` |
| NFR-502  | Integration & E2E Tests        | Should   | Integration tests (19 in `api/test_integration.py`), end-to-end tests (19 in `tests/test_e2e.py`), and slash command validation tests (58 in `tests/test_skills.py`) complement unit tests. | `make test-integration`, `make test-e2e`, `make test-skills` targets run the respective suites. Total: 319 tests across all suites. | `api/test_integration.py`, `tests/test_e2e.py`, `tests/test_skills.py`, `Makefile` |
| NFR-503  | Linters                        | Must     | Four linters enforce code quality: Ruff (Python lint + format), ESLint (JavaScript), Stylelint (CSS), HTMLHint (HTML). | `make lint` runs all four. `make lint-py`, `make lint-js`, `make lint-css`, `make lint-html` run individually. `make ci` includes linting. | `Makefile` |
| NFR-504  | CI/CD Pipeline                 | Must     | A full CI pipeline runs linting, test coverage, and security scanning in a single command. | `make ci` runs `lint`, `coverage`, `coverage-js`, and `security` targets in sequence. Exits non-zero on any failure. | `Makefile` |
| NFR-505  | Slash Commands                 | Should   | 17 Claude Code slash commands provide automated workflows for common development tasks (start, test, deploy, troubleshoot, generate docs, etc.). | 17 `.md` files in `.claude/commands/` directory, validated by `tests/test_skills.py`. | `.claude/commands/*.md` |
| NFR-506  | Docker Multi-Stage Build       | Should   | The Dockerfile uses multi-stage builds (base, prod, dev) to minimize production image size and separate dev dependencies. | `FROM base AS prod` excludes dev dependencies and test files. `FROM base AS dev` includes pytest, Node.js, npm, and test configs. | `Dockerfile` |
| NFR-507  | Environment Variable Config    | Must     | All deployment-sensitive configuration (DB credentials, CORS origin, Flask debug mode, host) is loaded from environment variables with sensible defaults. | `os.environ.get()` for `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `CORS_ORIGIN`, `FLASK_DEBUG`, `FLASK_HOST`. `.env.example` template provided. Docker Compose uses `env_file: .env`. | `api/app.py`, `docker-compose.yml` |

### NFR-6xx: Compatibility

| ID       | Title                          | Priority | Description | Acceptance Criteria | Source |
|----------|--------------------------------|----------|-------------|---------------------|--------|
| NFR-601  | HLS.js for Non-Safari Browsers | Must     | HLS playback uses the HLS.js library for browsers that do not support native HLS (Chrome, Firefox, Edge). | `if (Hls.isSupported()) { initHls(); }` initializes HLS.js with `lowLatencyMode: true` and `enableID3MetadataCues: true`. | `static/js/player.js` — boot section |
| NFR-602  | Safari Native HLS Support      | Must     | Safari uses its native HLS implementation when HLS.js is not supported, with metadata delivered via text tracks. | `else if (audio.canPlayType('application/vnd.apple.mpegurl'))` branch sets `audio.src` directly. `setupMetadataTextTracks()` handles timed metadata cues. | `static/js/player.js` — boot section, `setupMetadataTextTracks()` |
| NFR-603  | Responsive Layout (700px)      | Must     | The UI switches to a single-column layout below the 700px breakpoint. Max content width is 1200px with 24px gutters. | CSS breakpoint at 700px (documented in style guide). `html { zoom: 0.85 }` for global 85% scale. | `static/css/player.css`, `RadioCalico_Style_Guide.txt` |
| NFR-604  | WebP with PNG Fallback          | Should   | Images use WebP format with PNG fallback via `<picture>` / `<source>` elements for browsers without WebP support. | `<source srcset="/logo.webp" type="image/webp">` with `<img src="/logo.png">` fallback in `index.html`. | `static/index.html` |
| NFR-605  | Async Image Decoding            | Could    | Artwork images use `decoding="async"` to avoid blocking the main thread during image decode. | `fetchArtwork()` sets `decoding="async"` on the artwork `<img>` tag. | `static/js/player.js` — `fetchArtwork()` |
| NFR-606  | Social Link Security            | Must     | All external links opened via `window.open` use `noopener` to prevent the opened page from accessing the opener context. | Every `window.open()` call includes `'noopener'` as the third argument. | `static/js/player.js` — all share/search handlers |

---

## 5. Traceability Matrix

| Requirement | Implementation File | Test File |
|-------------|-------------------|-----------|
| FR-101 Play/Pause Toggle | `static/js/player.js` | `static/js/player.test.js` |
| FR-102 FLAC Lossless Streaming | `static/js/player.js` | `static/js/player.test.js` |
| FR-103 AAC Hi-Fi Streaming | `static/js/player.js` | `static/js/player.test.js` |
| FR-104 Quality Switch | `static/js/player.js` | `static/js/player.test.js` |
| FR-105 Volume Control | `static/js/player.js` | `static/js/player.test.js` |
| FR-106 Mute Toggle | `static/js/player.js` | `static/js/player.test.js` |
| FR-107 HLS Fatal Error Retry | `static/js/player.js` | `static/js/player.test.js` |
| FR-108 Safari Native HLS Fallback | `static/js/player.js` | `static/js/player.test.js` |
| FR-109 Elapsed Time Display | `static/js/player.js` | `static/js/player.test.js` |
| FR-201 Current Track Display | `static/js/player.js` | `static/js/player.test.js` |
| FR-202 Metadata from CloudFront JSON | `static/js/player.js` | `static/js/player.test.js` |
| FR-203 Metadata Latency Compensation | `static/js/player.js` | `static/js/player.test.js` |
| FR-204 Metadata Fetch on Fragment Change | `static/js/player.js` | `static/js/player.test.js` |
| FR-205 Album Artwork from iTunes | `static/js/player.js` | `static/js/player.test.js` |
| FR-206 Track Duration from iTunes | `static/js/player.js` | `static/js/player.test.js` |
| FR-207 Recently Played History | `static/js/player.js` | `static/js/player.test.js` |
| FR-208 History Filtering | `static/js/player.js` | `static/js/player.test.js` |
| FR-209 History Limit Dropdown | `static/js/player.js` | `static/js/player.test.js` |
| FR-210 Album Name Backfill from iTunes | `static/js/player.js` | `static/js/player.test.js` |
| FR-211 ID3 Metadata Fallback | `static/js/player.js` | `static/js/player.test.js` |
| FR-212 Source Quality Display | `static/js/player.js` | `static/js/player.test.js` |
| FR-213 Initial Metadata Fetch | `static/js/player.js` | `static/js/player.test.js` |
| FR-301 Submit Rating | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-302 IP-Based Deduplication | `api/app.py`, `db/init.sql` | `api/test_app.py` |
| FR-303 Check If Rated | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-304 Ratings Summary | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-305 List All Ratings | `api/app.py` | `api/test_app.py` |
| FR-306 Rating Count Badges | `static/js/player.js` | `static/js/player.test.js` |
| FR-401 User Registration | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-402 User Login | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-403 User Logout | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-404 Token-Based Authentication | `api/app.py` | `api/test_app.py` |
| FR-405 Client-Side Session Persistence | `static/js/player.js` | `static/js/player.test.js` |
| FR-406 Password Validation | `api/app.py` | `api/test_app.py` |
| FR-501 View Profile | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-502 Update Profile (Upsert) | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-503 Genre Selection | `static/js/player.js` | `static/js/player.test.js` |
| FR-504 Profile Form in Drawer | `static/js/player.js` | `static/js/player.test.js` |
| FR-601 Submit Feedback Message | `api/app.py`, `static/js/player.js` | `api/test_app.py`, `static/js/player.test.js` |
| FR-602 Feedback via X/Twitter | `static/js/player.js` | `static/js/player.test.js` |
| FR-603 Feedback via Telegram | `static/js/player.js` | `static/js/player.test.js` |
| FR-701 Share Now Playing on WhatsApp | `static/js/player.js` | `static/js/player.test.js` |
| FR-702 Share Now Playing on X/Twitter | `static/js/player.js` | `static/js/player.test.js` |
| FR-703 Share Now Playing on Telegram | `static/js/player.js` | `static/js/player.test.js` |
| FR-704 Search on Spotify | `static/js/player.js` | `static/js/player.test.js` |
| FR-705 Search on YouTube Music | `static/js/player.js` | `static/js/player.test.js` |
| FR-706 Search on Amazon Music | `static/js/player.js` | `static/js/player.test.js` |
| FR-707 Share Recently Played on WhatsApp | `static/js/player.js` | `static/js/player.test.js` |
| FR-708 Share Recently Played on X/Twitter | `static/js/player.js` | `static/js/player.test.js` |
| FR-709 Artwork URL in Share Text | `static/js/player.js` | `static/js/player.test.js` |
| FR-710 Plain Text Ratings in Share | `static/js/player.js` | `static/js/player.test.js` |
| FR-801 Dark/Light Theme Toggle | `static/js/player.js`, `static/css/player.css` | `static/js/player.test.js` |
| FR-802 Theme Persistence | `static/js/player.js` | `static/js/player.test.js` |
| FR-803 Stream Quality Settings | `static/js/player.js` | `static/js/player.test.js` |
| FR-804 Settings Gear Dropdown | `static/js/player.js` | `static/js/player.test.js` |
| FR-805 Hamburger Menu & Side Drawer | `static/js/player.js` | `static/js/player.test.js` |
| FR-806 HTML Escaping | `static/js/player.js` | `static/js/player.test.js` |
| NFR-101 Gzip Compression | `nginx/nginx.conf` | `tests/test_e2e.py` |
| NFR-102 Static Asset Caching | `nginx/nginx.conf` | `tests/test_e2e.py` |
| NFR-103 DNS Prefetch | `static/index.html` | -- |
| NFR-104 Font Preconnect | `static/index.html` | -- |
| NFR-105 iTunes API Client-Side Cache | `static/js/player.js` | `static/js/player.test.js` |
| NFR-106 Ratings API Pagination | `api/app.py` | `api/test_app.py` |
| NFR-107 WebP Image Format | `static/index.html` | -- |
| NFR-108 Ratings Response Caching | `api/app.py` | `api/test_app.py` |
| NFR-109 Metadata Fetch Debouncing | `static/js/player.js` | `static/js/player.test.js` |
| NFR-201 Password Hashing (PBKDF2) | `api/app.py` | `api/test_app.py` |
| NFR-202 Timing-Safe Password Comparison | `api/app.py` | `api/test_app.py` |
| NFR-203 Content Security Policy | `nginx/nginx.conf` | `tests/test_e2e.py` |
| NFR-204 Security Response Headers | `nginx/nginx.conf` | `tests/test_e2e.py` |
| NFR-205 Rate Limiting | `api/app.py` | `api/test_app.py` |
| NFR-206 Parameterized SQL Queries | `api/app.py` | `api/test_app.py` |
| NFR-207 CORS Configuration | `api/app.py` | `api/test_app.py` |
| NFR-208 Server Version Hiding | `nginx/nginx.conf` | `tests/test_e2e.py` |
| NFR-209 Non-Root Container User | `Dockerfile` | -- |
| NFR-210 IP Address Privacy | `api/app.py` | `api/test_app.py` |
| NFR-211 Security Scanning Tools | `Makefile` | `tests/test_skills.py` |
| NFR-212 X-Forwarded-For IP Extraction | `api/app.py`, `nginx/nginx.conf` | `api/test_app.py` |
| NFR-213 Permissions Policy | `nginx/nginx.conf` | `tests/test_e2e.py` |
| NFR-301 HLS Exponential Backoff Retry | `static/js/player.js` | `static/js/player.test.js` |
| NFR-302 Docker Health Checks | `docker-compose.yml` | `tests/test_e2e.py` |
| NFR-303 Nginx Health Endpoint | `nginx/nginx.conf` | `tests/test_e2e.py` |
| NFR-304 Proxy Timeouts | `nginx/nginx.conf` | -- |
| NFR-305 Service Restart Policy | `docker-compose.yml` | -- |
| NFR-306 Graceful Degradation on API Failure | `static/js/player.js` | `static/js/player.test.js` |
| NFR-401 Structured JSON Logging (Backend) | `api/app.py` | `api/test_app.py` |
| NFR-402 X-Request-ID Propagation | `api/app.py`, `nginx/nginx.conf` | `api/test_app.py`, `tests/test_e2e.py` |
| NFR-403 Request Duration Logging | `api/app.py` | `api/test_app.py` |
| NFR-404 Log Level by Status Code | `api/app.py` | `api/test_app.py` |
| NFR-405 Structured JSON Logging (Nginx) | `nginx/nginx.conf` | -- |
| NFR-406 Structured Logging (Frontend) | `static/js/player.js` | `static/js/player.test.js` |
| NFR-501 Unit Test Coverage | `api/test_app.py`, `static/js/player.test.js` | -- |
| NFR-502 Integration & E2E Tests | `api/test_integration.py`, `tests/test_e2e.py`, `tests/test_skills.py` | -- |
| NFR-503 Linters | `Makefile` | `tests/test_skills.py` |
| NFR-504 CI/CD Pipeline | `Makefile` | -- |
| NFR-505 Slash Commands | `.claude/commands/*.md` | `tests/test_skills.py` |
| NFR-506 Docker Multi-Stage Build | `Dockerfile` | -- |
| NFR-507 Environment Variable Config | `api/app.py`, `docker-compose.yml`, `api/.env.example` | `api/test_app.py` |
| NFR-601 HLS.js for Non-Safari Browsers | `static/js/player.js` | `static/js/player.test.js` |
| NFR-602 Safari Native HLS Support | `static/js/player.js` | `static/js/player.test.js` |
| NFR-603 Responsive Layout (700px) | `static/css/player.css` | -- |
| NFR-604 WebP with PNG Fallback | `static/index.html` | -- |
| NFR-605 Async Image Decoding | `static/js/player.js` | `static/js/player.test.js` |
| NFR-606 Social Link Security | `static/js/player.js` | `static/js/player.test.js` |
