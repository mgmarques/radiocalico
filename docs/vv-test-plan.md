<table><tr>
<td valign="middle">

# Radio Calico - Verification & Validation Test Plan

| Field | Value |
| --- | --- |
| **Project** | Radio Calico |
| **Version** | 1.0.0 |
| **Date** | 2026-03-17 |
| **Status** | Draft |
| **Author** | QA Team |

</td>
<td valign="middle" width="20%" align="right"><img src="../RadioCalicoLogoTM.png" alt="Radio Calico Logo" width="100%"></td>
</tr></table>

---

## Table of Contents

1. [Test Plan Overview](#1-test-plan-overview)
2. [Test Cases - Audio Streaming](#2-test-cases---audio-streaming)
3. [Test Cases - Track Metadata](#3-test-cases---track-metadata)
4. [Test Cases - Ratings](#4-test-cases---ratings)
5. [Test Cases - Authentication](#5-test-cases---authentication)
6. [Test Cases - User Profile](#6-test-cases---user-profile)
7. [Test Cases - Feedback](#7-test-cases---feedback)
8. [Test Cases - Social Sharing](#8-test-cases---social-sharing)
9. [Test Cases - Theme & Settings](#9-test-cases---theme--settings)
10. [Test Cases - Non-Functional](#10-test-cases---non-functional)
11. [Automated Test Coverage Matrix](#11-automated-test-coverage-matrix)
12. [Manual Test Procedures](#12-manual-test-procedures)
13. [Test Execution Summary](#13-test-execution-summary)

---

## 1. Test Plan Overview

### 1.1 Objectives

This Verification & Validation (V&V) test plan ensures that Radio Calico meets all functional and non-functional requirements documented in `docs/requirements.md`. The plan covers audio streaming, metadata display, ratings, authentication, user profiles, feedback, social sharing, theme/settings, and non-functional qualities (performance, security, observability).

### 1.2 Test Levels

| Level              | Scope                                                          | Automation |
|--------------------|----------------------------------------------------------------|------------|
| **Unit Tests**     | Individual functions and API endpoints in isolation             | Fully automated (pytest, Jest) |
| **Integration Tests** | Multi-step workflows across multiple API endpoints          | Fully automated (pytest) |
| **End-to-End Tests** | Full nginx + gunicorn + MySQL stack via HTTP                 | Fully automated (pytest + requests) |
| **Browser Tests**  | Real browser interactions: UI, themes, drawers, auth, playback  | Fully automated (Selenium + headless Chrome) |
| **Manual Tests**   | Audio quality verification, subjective UX assessment            | Manual execution with documented procedures |

### 1.3 Tools

| Tool           | Purpose                                      |
|----------------|----------------------------------------------|
| pytest         | Python unit and integration tests             |
| pytest-cov     | Python code coverage (95%+ threshold)         |
| Jest + jsdom   | JavaScript unit tests (DOM simulation)        |
| Selenium       | Browser-based E2E tests (headless Chrome)     |
| requests       | Python HTTP client for E2E tests              |
| Bandit         | Python SAST security scanning                 |
| Safety         | Python dependency vulnerability scanning      |
| npm audit      | JavaScript dependency vulnerability scanning  |
| Hadolint       | Dockerfile linting                            |
| Trivy          | Docker image vulnerability scanning           |
| OWASP ZAP      | Dynamic application security testing (DAST)   |

### 1.4 Environments

| Environment | Description                                                      | Access                     |
|-------------|------------------------------------------------------------------|----------------------------|
| **Local Dev** | Flask dev server + MySQL 5.7 (Homebrew)                        | `http://127.0.0.1:5000`   |
| **Docker Dev** | Flask debug + MySQL 8.0 (Docker Compose, dev profile)          | `http://127.0.0.1:5050`   |
| **Docker Prod** | nginx + gunicorn + MySQL 8.0 (Docker Compose, prod profile)  | `http://127.0.0.1:5050`   |

---

## 2. Test Cases - Audio Streaming

**TC-101**: Play/Pause Toggle
- Requirement: FR-101
- Precondition: App loaded in browser, stream available
- Steps:
  1. Open the app in a browser
  2. Click the play button
  3. Observe the icon changes to a spinner, then to a pause icon
  4. Click the pause button
  5. Observe the icon changes back to a play icon
- Expected result: Audio starts playing on first click (spinner shown during buffering, then pause icon). Audio stops on second click (play icon shown). No errors in console.
- Automated: Yes — `static/js/player.test.js::togglePlay > starts playing and shows spinner`, `togglePlay > pauses when already playing`, `togglePlay > reverts to play icon on play failure`

**TC-102**: Pause Stops Audio Output
- Requirement: FR-101
- Precondition: Audio is currently playing
- Steps:
  1. While audio is playing, click the pause button
  2. Verify no audio output from speakers
  3. Verify the play icon is displayed
- Expected result: Audio output ceases immediately. The play icon is shown. The stream connection may remain open.
- Automated: Yes — `static/js/player.test.js::togglePlay > pauses when already playing`

**TC-103**: Quality Switch (FLAC to AAC)
- Requirement: FR-104
- Precondition: App is playing in FLAC mode (default)
- Steps:
  1. Click the settings gear icon in the navbar
  2. Select "AAC Hi-Fi (211 kbps)" radio button
  3. Observe stream reinitializes
  4. Verify audio resumes playing
  5. Verify the quality label updates to "AAC Hi-Fi (211 kbps)"
- Expected result: Stream seamlessly switches to AAC codec. Playback resumes without user re-clicking play. The `rc-stream-quality` localStorage key is set to "aac".
- Automated: Yes — `static/js/player.test.js::applyStreamQuality > switches to AAC and reinitializes HLS`, `applyStreamQuality > resumes playback if was playing`

**TC-104**: Volume Control
- Requirement: FR-105
- Precondition: App loaded, audio may or may not be playing
- Steps:
  1. Locate the volume slider
  2. Drag the slider to approximately 50%
  3. Verify audio volume decreases
  4. Drag the slider to 0%
  5. Verify audio is silent
  6. Drag the slider to 100%
  7. Verify audio is at maximum volume
- Expected result: Audio volume adjusts smoothly in real time as the slider moves. The `audio.volume` property reflects the slider value (0.0 to 1.0).
- Automated: Yes — `static/js/player.test.js::volume and mute > volume input updates audio volume`

**TC-105**: Mute Toggle
- Requirement: FR-106
- Precondition: App loaded, audio playing at non-zero volume
- Steps:
  1. Click the mute button
  2. Verify audio is silenced and mute icon is shown
  3. Click the mute button again
  4. Verify audio resumes at previous volume and volume icon is shown
- Expected result: First click silences audio and shows mute icon. Second click restores audio and shows volume icon. The volume slider position does not change.
- Automated: Yes — `static/js/player.test.js::volume and mute > mute button toggles mute state`

**TC-106**: HLS Fatal Error Recovery
- Requirement: FR-107, NFR-301
- Precondition: App is playing audio
- Steps:
  1. Simulate a network interruption (disable Wi-Fi or block CDN)
  2. Observe that a fatal HLS error occurs
  3. Wait and observe retry attempts in the console
  4. Restore network connectivity
  5. Verify audio resumes after successful retry
- Expected result: Player retries with exponential backoff (4s, 8s, 16s, 32s, 60s, 60s...). Retry count shown in console logs. After network restoration, playback resumes. Maximum 10 retry attempts.
- Automated: Yes — `static/js/player.test.js::initHls event handlers > ERROR handler resets state on fatal error`, `ERROR handler ignores non-fatal errors`

---

## 3. Test Cases - Track Metadata

**TC-201**: Current Track Display
- Requirement: FR-201
- Precondition: App loaded, stream metadata available from CloudFront
- Steps:
  1. Open the app
  2. Observe the Now Playing area
  3. Verify artist name, track title, and album name are displayed
- Expected result: The Now Playing section shows the current artist, title, and album from the CloudFront JSON endpoint. Default display before metadata loads is "Radio Calico / Live Stream".
- Automated: Yes — `static/js/player.test.js::updateTrack > updates DOM elements`

**TC-202**: Album Artwork Display
- Requirement: FR-205
- Precondition: App loaded, track metadata available, iTunes API reachable
- Steps:
  1. Observe the artwork area in the Now Playing section
  2. Verify album artwork image is displayed
  3. Verify the image resolution is 600x600
- Expected result: Album artwork from iTunes is displayed. If iTunes returns no results, a "music note" placeholder is shown instead.
- Automated: Yes — `static/js/player.test.js::fetchArtwork > sets artwork from iTunes API result`, `fetchArtwork > shows placeholder when no results`

**TC-203**: Track Duration Display
- Requirement: FR-206, FR-109
- Precondition: App is playing, metadata and iTunes data available
- Steps:
  1. Start playback
  2. Observe the time display area
  3. Verify elapsed time increments in real time
  4. Verify total duration is shown (or "Live" if unavailable)
- Expected result: Time display shows `elapsed / total` format (e.g., "1:23 / 3:45"). If iTunes `trackTimeMillis` is unavailable, shows `elapsed / Live`. Elapsed uses wall-clock time, not HLS buffer position.
- Automated: Yes — `static/js/player.test.js::audio timeupdate > updates bar-time when playing`, `fetchArtwork > handles result without trackTimeMillis`

**TC-204**: Track Change Updates Display
- Requirement: FR-201, FR-203
- Precondition: App is playing, waiting for a track change on the live stream
- Steps:
  1. Wait for the live stream to transition to a new song
  2. Observe the Now Playing area updates
  3. Verify the new artist, title, album, and artwork are displayed
  4. Verify the update is delayed to match HLS latency
- Expected result: Display updates when the new song audio is actually heard (not when CloudFront publishes the metadata). The latency delay (fallback 6s, max 15s) ensures synchronization.
- Automated: Yes — `static/js/player.test.js::fetchMetadata > fetches metadata and schedules track update`

**TC-205**: Recently Played History
- Requirement: FR-207
- Precondition: App has been playing through multiple tracks
- Steps:
  1. Observe the Recently Played list below the Now Playing area
  2. Verify previously played tracks appear in reverse chronological order
  3. Verify each entry shows artist, title, and album
  4. Verify rating badges (likes/dislikes) are shown per track
- Expected result: Up to 20 previously played tracks are listed. Each entry shows title, artist, album name, and rating badges. List scrolls vertically if needed.
- Automated: Yes — `static/js/player.test.js::renderHistory > renders history items with album`, `renderHistory > renders rating badges when summary available`

**TC-206**: History Filtering
- Requirement: FR-208
- Precondition: Recently Played list has tracks with mixed ratings
- Steps:
  1. Click the "All" filter button — verify all tracks shown
  2. Click the "Liked" filter button — verify only tracks with likes > 0 shown
  3. Click the "Disliked" filter button — verify only tracks with dislikes > 0 shown
- Expected result: Filter buttons restrict the displayed list to matching tracks. Active filter is visually highlighted.
- Automated: Yes — `static/js/player.test.js::getFilteredHistory > filters by liked tracks`, `getFilteredHistory > filters by disliked tracks`

**TC-207**: History Limit Dropdown
- Requirement: FR-209
- Precondition: Recently Played list has more than 5 tracks
- Steps:
  1. Locate the history limit dropdown
  2. Select "5" — verify only 5 tracks shown
  3. Select "10" — verify up to 10 tracks shown
  4. Select "20" — verify up to 20 tracks shown
- Expected result: The dropdown limits the number of displayed tracks. Changing the limit updates the list immediately.
- Automated: Yes — `static/js/player.test.js::history filter and limit > prev-limit change updates historyLimit`, `getFilteredHistory > respects historyLimit`

---

## 4. Test Cases - Ratings

**TC-301**: Thumbs Up Rating
- Requirement: FR-301
- Precondition: App loaded, a track is displayed, user has not rated this track
- Steps:
  1. Click the thumbs up button for the current track
  2. Observe the confirmation message "Thanks!"
  3. Verify the like count increments by 1
- Expected result: Rating is submitted via `POST /api/ratings` with `score: 1`. Like count badge updates. Thumbs up button shows as rated (disabled).
- Automated: Yes — `static/js/player.test.js::submitRating > shows Thanks! on thumbs up success`, `api/test_app.py::TestPostRating::test_success`

**TC-302**: Thumbs Down Rating
- Requirement: FR-301
- Precondition: App loaded, a track is displayed, user has not rated this track
- Steps:
  1. Click the thumbs down button for the current track
  2. Observe the confirmation message "Noted!"
  3. Verify the dislike count increments by 1
- Expected result: Rating is submitted via `POST /api/ratings` with `score: 0`. Dislike count badge updates. Thumbs down button shows as rated.
- Automated: Yes — `static/js/player.test.js::submitRating > shows Noted! on thumbs down success`

**TC-303**: Duplicate Rating Prevention
- Requirement: FR-302
- Precondition: User has already rated the current track
- Steps:
  1. Attempt to click the thumbs up or thumbs down button
  2. Observe that the buttons are disabled/greyed out
  3. Verify no additional API call is made
- Expected result: Rating buttons are disabled after the first rating. If the API is called again, it returns HTTP 409 "already rated". The UI shows the existing rating state.
- Automated: Yes — `static/js/player.test.js::submitRating > handles 409 duplicate rating`, `api/test_app.py::TestPostRating::test_duplicate_rating`

**TC-304**: Rating Persistence Across Page Loads
- Requirement: FR-303
- Precondition: User has rated a track, then reloads the page
- Steps:
  1. Rate a track with thumbs up
  2. Reload the page (or navigate away and return)
  3. Wait for the same track to be displayed again
  4. Verify the rating buttons reflect the previous rating
- Expected result: The frontend calls `GET /api/ratings/check` on track change and correctly shows the existing rating state (buttons disabled, correct button highlighted).
- Automated: Yes — `static/js/player.test.js::checkIfRated > returns true when rated`, `api/test_app.py::TestCheckRating::test_rated`

**TC-305**: Rating Badges in Recently Played
- Requirement: FR-304, FR-306
- Precondition: Some tracks in the Recently Played list have been rated
- Steps:
  1. Observe the Recently Played list
  2. Verify rated tracks display like/dislike count badges
  3. Verify unrated tracks show 0/0 or no badges
- Expected result: Each track in the Recently Played list shows its aggregated like and dislike counts from `GET /api/ratings/summary`.
- Automated: Yes — `static/js/player.test.js::renderHistory > renders rating badges when summary available`, `api/test_app.py::TestGetRatingsSummary::test_counts`

**TC-306**: Ratings Independent Per Track
- Requirement: FR-302
- Precondition: Multiple different tracks have been played
- Steps:
  1. Rate Track A with thumbs up
  2. Wait for Track B to start playing
  3. Verify rating buttons are re-enabled for Track B
  4. Rate Track B with thumbs down
  5. Verify both ratings are stored independently
- Expected result: Each track has its own independent rating state per IP. Rating one track does not affect the rating state of other tracks.
- Automated: Yes — `api/test_integration.py::TestRatingWorkflow::test_multiple_stations`

---

## 5. Test Cases - Authentication

**TC-401**: User Registration
- Requirement: FR-401
- Precondition: App loaded, drawer open to login/register section
- Steps:
  1. Open the hamburger menu (side drawer)
  2. Enter a unique username (e.g., "testuser123")
  3. Enter a password with at least 8 characters (e.g., "mypassword")
  4. Click the "Register" button
  5. Observe success message
- Expected result: Account is created. Success message is displayed. The user can now log in with these credentials.
- Automated: Yes — `static/js/player.test.js::register button > successful registration shows success message`, `api/test_app.py::TestRegister::test_success`

**TC-402**: Short Password Rejected
- Requirement: FR-406
- Precondition: App loaded, drawer open
- Steps:
  1. Enter a username
  2. Enter a password with fewer than 8 characters (e.g., "short")
  3. Click "Register"
- Expected result: Registration fails with error message "Password must be at least 8 characters". HTTP 400 returned.
- Automated: Yes — `static/js/player.test.js::register button > failed registration shows error`, `api/test_app.py::TestRegister::test_short_password`

**TC-403**: Duplicate Username Rejected
- Requirement: FR-401
- Precondition: A user "testuser" already exists
- Steps:
  1. Enter "testuser" as the username
  2. Enter a valid password
  3. Click "Register"
- Expected result: Registration fails with error message "Username already taken". HTTP 409 returned.
- Automated: Yes — `api/test_app.py::TestRegister::test_duplicate_username`, `api/test_integration.py::TestSessionHandling::test_register_duplicate_username`

**TC-404**: User Login
- Requirement: FR-402
- Precondition: User account "testuser" exists
- Steps:
  1. Open the side drawer
  2. Enter "testuser" as the username
  3. Enter the correct password
  4. Click "Login"
  5. Observe the drawer switches to the profile view
- Expected result: Login succeeds. A bearer token is returned and stored in `localStorage` (`rc-token`). The drawer shows the profile section with "Logged in as testuser". Profile and feedback sections become visible.
- Automated: Yes — `static/js/player.test.js::login form > successful login switches to profile view and loads profile`, `api/test_app.py::TestLogin::test_success`

**TC-405**: Wrong Password Rejected
- Requirement: FR-402
- Precondition: User account exists
- Steps:
  1. Enter the correct username
  2. Enter an incorrect password
  3. Click "Login"
- Expected result: Login fails with error message "Invalid username or password". HTTP 401 returned. No token is stored.
- Automated: Yes — `static/js/player.test.js::login form > failed login shows error`, `api/test_app.py::TestLogin::test_wrong_password`

**TC-406**: User Logout
- Requirement: FR-403
- Precondition: User is logged in
- Steps:
  1. Open the side drawer (should show profile view)
  2. Click the "Logout" button
  3. Observe the drawer reverts to the login/register form
- Expected result: Token is invalidated server-side. `localStorage` keys `rc-token` and `rc-user` are removed. The drawer shows the auth section again. Protected API calls return 401.
- Automated: Yes — `static/js/player.test.js::logout > clears auth state and shows auth view`, `api/test_app.py::TestLogout::test_success`, `api/test_app.py::TestLogout::test_token_invalidated_after_logout`

**TC-407**: Protected Endpoints Require Auth
- Requirement: FR-404
- Precondition: No user is logged in (no valid token)
- Steps:
  1. Attempt to access `GET /api/profile` without a token
  2. Attempt to access `PUT /api/profile` without a token
  3. Attempt to access `POST /api/feedback` without a token
  4. Attempt to access `POST /api/logout` without a token
- Expected result: All four endpoints return HTTP 401 with `{"error": "Unauthorized"}` or `{"error": "Login required to send feedback"}`.
- Automated: Yes — `api/test_integration.py::TestAuthEdgeCases::test_all_protected_endpoints_require_auth`, `api/test_app.py::TestGetProfile::test_unauthorized`

---

## 6. Test Cases - User Profile

**TC-501**: Empty Profile on First Login
- Requirement: FR-501
- Precondition: User just registered and logged in for the first time
- Steps:
  1. Log in with a newly registered account
  2. Observe the profile form in the side drawer
  3. Verify all fields (nickname, email, genres, about) are empty
- Expected result: Profile fields are empty strings. The API returns `{"nickname": "", "email": "", "genres": "", "about": ""}`.
- Automated: Yes — `api/test_app.py::TestGetProfile::test_empty_profile`, `api/test_integration.py::TestUserLifecycle::test_full_lifecycle`

**TC-502**: Update Profile
- Requirement: FR-502
- Precondition: User is logged in
- Steps:
  1. Open the side drawer (profile view)
  2. Enter a nickname (e.g., "DJ Cool")
  3. Enter an email (e.g., "dj@example.com")
  4. Write something in the "About You" textarea
  5. Click "Save Profile"
  6. Observe success confirmation
  7. Reload the page and verify data persists
- Expected result: Profile is saved via `PUT /api/profile`. Success message shown. On page reload, the profile form is populated with the saved data.
- Automated: Yes — `static/js/player.test.js::profile save > successful save shows confirmation`, `api/test_app.py::TestUpdateProfile::test_create_profile`

**TC-503**: Profile Persistence After Update
- Requirement: FR-502
- Precondition: User has previously saved a profile
- Steps:
  1. Log in
  2. Modify the nickname from "DJ Cool" to "DJ Awesome"
  3. Save the profile
  4. Log out
  5. Log back in
  6. Verify the profile shows "DJ Awesome"
- Expected result: The updated profile data persists across sessions. The API correctly returns the latest values.
- Automated: Yes — `api/test_app.py::TestUpdateProfile::test_update_existing_profile`, `api/test_integration.py::TestProfileUpsert::test_profile_upsert`

**TC-504**: Genre Selection
- Requirement: FR-503
- Precondition: User is logged in, profile view open
- Steps:
  1. Check several genre checkboxes (e.g., Rock, Jazz, Electronic)
  2. Save the profile
  3. Reload the page
  4. Verify the same genre checkboxes are checked
- Expected result: Selected genres are stored as a comma-separated string (e.g., "Rock,Jazz,Electronic"). On reload, `loadProfile()` parses the string and re-checks the matching checkboxes.
- Automated: Yes — `static/js/player.test.js::loadProfile > populates form fields when logged in (via login flow)`

---

## 7. Test Cases - Feedback

**TC-601**: Submit Feedback Message
- Requirement: FR-601
- Precondition: User is logged in
- Steps:
  1. Open the side drawer
  2. Scroll to the feedback section
  3. Enter a message in the feedback textarea (e.g., "Great station!")
  4. Click the submit button (envelope icon)
  5. Observe success confirmation
- Expected result: Feedback is submitted via `POST /api/feedback`. The response is HTTP 201. A "Thank you" message is shown. The feedback record in the database includes the user's profile snapshot (username, nickname, email, genres, about).
- Automated: Yes — `static/js/player.test.js::feedback form > successful feedback shows thank you`, `api/test_app.py::TestFeedback::test_success_with_profile`

**TC-602**: Empty Feedback Validation
- Requirement: FR-601
- Precondition: User is logged in
- Steps:
  1. Leave the feedback textarea empty
  2. Click the submit button
- Expected result: Submission is rejected. Error message "Message required" is shown. HTTP 400 returned.
- Automated: Yes — `static/js/player.test.js::feedback form > empty message shows validation error`, `api/test_app.py::TestFeedback::test_empty_message`

**TC-603**: Feedback via X/Twitter
- Requirement: FR-602
- Precondition: User is logged in, feedback message typed
- Steps:
  1. Enter a feedback message
  2. Click the X/Twitter button in the feedback section
  3. Observe a new tab opens with X/Twitter tweet intent
- Expected result: A new browser tab opens to `https://x.com/intent/tweet?text=...` with the message prefixed by "Hey @RadioCalico,". The tab uses `noopener`.
- Automated: Yes — `static/js/player.test.js::feedback social buttons > feedback-twitter opens tweet intent with message`

**TC-604**: Feedback via Telegram
- Requirement: FR-603
- Precondition: User is logged in, feedback message typed
- Steps:
  1. Enter a feedback message
  2. Click the Telegram button in the feedback section
  3. Observe a new tab opens with Telegram share
- Expected result: A new browser tab opens to `https://t.me/share/url?text=...` with the message prefixed by "Radio Calico feedback:". The tab uses `noopener`.
- Automated: Yes — `static/js/player.test.js::feedback social buttons > feedback-telegram opens share URL`

---

## 8. Test Cases - Social Sharing

**TC-701**: Share Now Playing on WhatsApp
- Requirement: FR-701
- Precondition: A track is currently displayed in the Now Playing section
- Steps:
  1. Click the WhatsApp share button below the rating row
  2. Observe a new tab opens
- Expected result: New tab opens to `https://wa.me/?text=...` with text `Listening to "Title" by Artist (Album) on Radio Calico!` followed by `Album cover: {300x300 URL}`.
- Automated: Yes — `static/js/player.test.js::share button click handlers > WhatsApp share opens correct URL`

**TC-702**: Share Now Playing on X/Twitter
- Requirement: FR-702
- Precondition: A track is currently displayed
- Steps:
  1. Click the X/Twitter share button
  2. Observe a new tab opens with tweet intent
- Expected result: New tab opens to `https://x.com/intent/tweet?text=...` with the same share text as WhatsApp.
- Automated: Yes — `static/js/player.test.js::share button click handlers > Twitter share opens correct URL`

**TC-703**: Share Now Playing on Telegram
- Requirement: FR-703
- Precondition: A track is currently displayed
- Steps:
  1. Click the Telegram share button
  2. Observe a new tab opens
- Expected result: New tab opens to `https://t.me/share/url?text=...` with the share text.
- Automated: Yes — `static/js/player.test.js::share button click handlers > Telegram share opens correct URL`

**TC-704**: Search on Spotify
- Requirement: FR-704
- Precondition: A track is currently displayed with artist and title
- Steps:
  1. Click the Spotify button
  2. Observe a new tab opens to Spotify search
- Expected result: New tab opens to `https://open.spotify.com/search/{artist} {title}`.
- Automated: Yes — `static/js/player.test.js::share button click handlers > Spotify search opens correct URL`

**TC-705**: Search on YouTube Music
- Requirement: FR-705
- Precondition: A track is currently displayed
- Steps:
  1. Click the YouTube Music button
  2. Observe a new tab opens
- Expected result: New tab opens to `https://music.youtube.com/search?q={artist} {title}`.
- Automated: Yes — `static/js/player.test.js::share button click handlers > YouTube Music search opens correct URL`

**TC-706**: Search on Amazon Music
- Requirement: FR-706
- Precondition: A track is currently displayed
- Steps:
  1. Click the Amazon Music button
  2. Observe a new tab opens
- Expected result: New tab opens to `https://www.amazon.com/s?k={artist} {title}&i=digital-music`.
- Automated: Yes — `static/js/player.test.js::share button click handlers > Amazon Music search opens correct URL`

**TC-707**: Share Recently Played on WhatsApp
- Requirement: FR-707
- Precondition: Recently Played list has at least one track
- Steps:
  1. Scroll to the Recently Played section
  2. Click the WhatsApp share button below the list
  3. Observe a new tab opens
- Expected result: New tab opens with a numbered list of recently played tracks formatted as `"N. Title by Artist (Album) [N likes / N unlikes]"`. Respects active filter and limit settings. No-op if list is empty.
- Automated: Yes — `static/js/player.test.js::recently played share handlers > prev-share-whatsapp opens with text when history exists`

**TC-708**: Share Recently Played on X/Twitter
- Requirement: FR-708
- Precondition: Recently Played list has at least one track
- Steps:
  1. Click the X/Twitter share button below the Recently Played list
  2. Observe a new tab opens with tweet intent
- Expected result: New tab opens with the same numbered list as WhatsApp. Plain text ratings `[N likes / N unlikes]` used (no emoji to avoid URL encoding issues).
- Automated: Yes — `static/js/player.test.js::recently played share handlers > prev-share-twitter opens with text when history exists`

---

## 9. Test Cases - Theme & Settings

**TC-801**: Light Theme
- Requirement: FR-801
- Precondition: App loaded (default is dark theme)
- Steps:
  1. Click the settings gear icon
  2. Select "Light" radio button
  3. Observe the UI color scheme changes
- Expected result: Background becomes light (cream/white), text becomes dark (charcoal). The `data-theme` attribute on `<html>` is removed or set to "light". CSS custom properties revert to light mode values.
- Automated: Yes — `static/js/player.test.js::applyTheme > sets data-theme attribute`

**TC-802**: Dark Theme
- Requirement: FR-801
- Precondition: App is currently in light theme
- Steps:
  1. Click the settings gear icon
  2. Select "Dark" radio button
  3. Observe the UI color scheme changes
- Expected result: Background becomes dark, text becomes light. The `data-theme="dark"` attribute is set on `<html>`. Navbar and footer text forced to white.
- Automated: Yes — `static/js/player.test.js::applyTheme > sets data-theme attribute`

**TC-803**: Theme Persistence
- Requirement: FR-802
- Precondition: User has selected light theme
- Steps:
  1. Select light theme via settings
  2. Reload the page
  3. Verify the app loads in light theme
- Expected result: The `rc-theme` localStorage key stores the selected theme. On page load, the saved theme is applied before content renders.
- Automated: Yes — `static/js/player.test.js::applyTheme > persists to localStorage`

**TC-804**: Stream Quality Persistence
- Requirement: FR-803, FR-104
- Precondition: User has switched to AAC quality
- Steps:
  1. Switch quality to AAC via settings
  2. Reload the page
  3. Verify the app loads with AAC quality selected
  4. Verify the quality label shows "AAC Hi-Fi (211 kbps)"
- Expected result: The `rc-stream-quality` localStorage key stores "aac". On page load, AAC is selected and the HLS level is forced accordingly.
- Automated: Yes — `static/js/player.test.js::updateStreamQualityDisplay > updates for AAC`, `STREAM_LABELS > has flac and aac entries`

**TC-805**: Settings Dropdown Open/Close
- Requirement: FR-804
- Precondition: App loaded
- Steps:
  1. Click the settings gear icon — verify dropdown opens
  2. Click outside the dropdown — verify it closes
  3. Click the gear icon again — verify it opens
  4. Click the gear icon once more — verify it closes (toggle)
- Expected result: The settings dropdown toggles the `.open` class. Clicking outside closes it via a document click handler.
- Automated: Yes — `static/js/player.test.js::settings dropdown > toggles open class on settings button click`, `settings dropdown > closes on outside click`

---

## 10. Test Cases - Non-Functional

**TC-901**: Page Load Performance
- Requirement: NFR-101, NFR-102, NFR-103, NFR-104
- Precondition: Docker prod stack running with nginx
- Steps:
  1. Open the app in a browser with DevTools Network tab open
  2. Observe the total page load time
  3. Verify static assets (CSS, JS) are served with gzip compression
  4. Verify `Cache-Control` headers include `immutable` for static assets
- Expected result: HTML, CSS, JS responses are gzip-compressed. Static assets have 7-day cache expiry with `immutable` directive. DNS prefetch and preconnect hints are present in HTML.
- Automated: Partial — `tests/test_e2e.py::TestStaticFiles::test_static_cache_headers`

**TC-902**: WebP Image Support
- Requirement: NFR-107, NFR-604
- Precondition: App loaded
- Steps:
  1. Inspect the logo in the navbar using DevTools
  2. Verify it uses a `<picture>` element with WebP source
  3. Verify a PNG fallback `<img>` exists
- Expected result: The logo is served as WebP with a PNG fallback. Favicon also uses WebP format.
- Automated: No

**TC-903**: Security Response Headers
- Requirement: NFR-203, NFR-204, NFR-208, NFR-213
- Precondition: Docker prod stack running with nginx
- Steps:
  1. Make an HTTP request to the app
  2. Inspect the response headers
  3. Verify presence of: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Content-Security-Policy`, `Permissions-Policy`, `Referrer-Policy`, `X-XSS-Protection`
  4. Verify the `Server` header does not expose the nginx version
- Expected result: All six security headers are present. CSP restricts script/style/image/media sources to known origins. Server version is hidden.
- Automated: Yes — `tests/test_e2e.py::TestSecurityHeaders::test_x_content_type_options`, `test_x_frame_options`, `test_csp_header`, `test_permissions_policy`, `test_server_version_hidden`

**TC-904**: X-Request-ID Propagation
- Requirement: NFR-402
- Precondition: Docker prod stack running
- Steps:
  1. Send an API request (e.g., `GET /api/ratings/summary`)
  2. Check the response headers for `X-Request-ID`
  3. Send a request with a custom `X-Request-ID` header
  4. Verify the same ID is echoed back
- Expected result: Every response includes an `X-Request-ID` header. If the client provides one, it is propagated; otherwise, a new one is auto-generated.
- Automated: Yes — `tests/test_e2e.py::TestSecurityHeaders::test_request_id_header`

**TC-905**: Structured JSON Logging
- Requirement: NFR-401, NFR-406
- Precondition: Backend running, browser console open
- Steps:
  1. Make API requests and observe Flask backend logs
  2. Verify logs are in JSON format with fields: `timestamp`, `level`, `logger`, `message`, `request_id`, `method`, `path`, `status`, `duration_ms`
  3. Open the browser console and interact with the player
  4. Verify frontend logs are structured JSON with: `timestamp`, `level`, `logger: "player"`, `message`
- Expected result: Both backend and frontend emit structured JSON logs suitable for log aggregation systems.
- Automated: Yes — `static/js/player.test.js::log > log.info outputs JSON to console.log`, `log > log.warn outputs JSON to console.warn`, `log > log.error outputs JSON to console.error`

**TC-906**: Slash Commands Available
- Requirement: NFR-505
- Precondition: Claude Code environment with project loaded
- Steps:
  1. Verify 18 slash command files exist in `.claude/commands/`
  2. Run `/start` to verify the dev environment launch command works
  3. Run `/run-ci` to verify the CI pipeline command works
- Expected result: All 18 slash commands are present and parseable. They provide automated workflows for development, testing, and deployment tasks.
- Automated: Yes — `tests/test_skills.py` (169 tests validate all slash commands)

---

## 11. Automated Test Coverage Matrix

| Test Case | Requirement | Test File | Test Name(s) |
|-----------|-------------|-----------|---------------|
| TC-101 | FR-101 | `static/js/player.test.js` | `togglePlay > starts playing and shows spinner`, `togglePlay > pauses when already playing` |
| TC-102 | FR-101 | `static/js/player.test.js` | `togglePlay > pauses when already playing` |
| TC-103 | FR-104 | `static/js/player.test.js` | `applyStreamQuality > switches to AAC and reinitializes HLS`, `applyStreamQuality > resumes playback if was playing` |
| TC-104 | FR-105 | `static/js/player.test.js` | `volume and mute > volume input updates audio volume`, `volume and mute > volume input unmutes when muted and volume > 0` |
| TC-105 | FR-106 | `static/js/player.test.js` | `volume and mute > mute button toggles mute state` |
| TC-106 | FR-107 | `static/js/player.test.js` | `initHls event handlers > ERROR handler resets state on fatal error` |
| TC-201 | FR-201 | `static/js/player.test.js` | `updateTrack > updates DOM elements` |
| TC-202 | FR-205 | `static/js/player.test.js` | `fetchArtwork > sets artwork from iTunes API result`, `fetchArtwork > shows placeholder when no results` |
| TC-203 | FR-206, FR-109 | `static/js/player.test.js` | `audio timeupdate > updates bar-time when playing`, `fetchArtwork > handles result without trackTimeMillis` |
| TC-204 | FR-201, FR-203 | `static/js/player.test.js` | `fetchMetadata > fetches metadata and schedules track update` |
| TC-205 | FR-207 | `static/js/player.test.js` | `renderHistory > renders history items with album`, `renderHistory > renders rating badges when summary available` |
| TC-206 | FR-208 | `static/js/player.test.js` | `getFilteredHistory > filters by liked tracks`, `getFilteredHistory > filters by disliked tracks` |
| TC-207 | FR-209 | `static/js/player.test.js` | `history filter and limit > prev-limit change updates historyLimit`, `getFilteredHistory > respects historyLimit` |
| TC-301 | FR-301 | `static/js/player.test.js`, `api/test_app.py` | `submitRating > shows Thanks! on thumbs up success`, `TestPostRating::test_success` |
| TC-302 | FR-301 | `static/js/player.test.js` | `submitRating > shows Noted! on thumbs down success` |
| TC-303 | FR-302 | `static/js/player.test.js`, `api/test_app.py` | `submitRating > handles 409 duplicate rating`, `TestPostRating::test_duplicate_rating` |
| TC-304 | FR-303 | `static/js/player.test.js`, `api/test_app.py` | `checkIfRated > returns true when rated`, `TestCheckRating::test_rated` |
| TC-305 | FR-304, FR-306 | `static/js/player.test.js`, `api/test_app.py` | `renderHistory > renders rating badges when summary available`, `TestGetRatingsSummary::test_counts` |
| TC-306 | FR-302 | `api/test_integration.py` | `TestRatingWorkflow::test_multiple_stations` |
| TC-401 | FR-401 | `static/js/player.test.js`, `api/test_app.py` | `register button > successful registration shows success message`, `TestRegister::test_success` |
| TC-402 | FR-406 | `static/js/player.test.js`, `api/test_app.py` | `register button > failed registration shows error`, `TestRegister::test_short_password` |
| TC-403 | FR-401 | `api/test_app.py`, `api/test_integration.py` | `TestRegister::test_duplicate_username`, `TestSessionHandling::test_register_duplicate_username` |
| TC-404 | FR-402 | `static/js/player.test.js`, `api/test_app.py` | `login form > successful login switches to profile view and loads profile`, `TestLogin::test_success` |
| TC-405 | FR-402 | `static/js/player.test.js`, `api/test_app.py` | `login form > failed login shows error`, `TestLogin::test_wrong_password` |
| TC-406 | FR-403 | `static/js/player.test.js`, `api/test_app.py` | `logout > clears auth state and shows auth view`, `TestLogout::test_success`, `TestLogout::test_token_invalidated_after_logout` |
| TC-407 | FR-404 | `api/test_integration.py` | `TestAuthEdgeCases::test_all_protected_endpoints_require_auth` |
| TC-501 | FR-501 | `api/test_app.py`, `api/test_integration.py` | `TestGetProfile::test_empty_profile`, `TestUserLifecycle::test_full_lifecycle` |
| TC-502 | FR-502 | `static/js/player.test.js`, `api/test_app.py` | `profile save > successful save shows confirmation`, `TestUpdateProfile::test_create_profile` |
| TC-503 | FR-502 | `api/test_app.py`, `api/test_integration.py` | `TestUpdateProfile::test_update_existing_profile`, `TestProfileUpsert::test_profile_upsert` |
| TC-504 | FR-503 | `static/js/player.test.js` | `loadProfile > populates form fields when logged in (via login flow)` |
| TC-601 | FR-601 | `static/js/player.test.js`, `api/test_app.py` | `feedback form > successful feedback shows thank you`, `TestFeedback::test_success_with_profile` |
| TC-602 | FR-601 | `static/js/player.test.js`, `api/test_app.py` | `feedback form > empty message shows validation error`, `TestFeedback::test_empty_message` |
| TC-603 | FR-602 | `static/js/player.test.js` | `feedback social buttons > feedback-twitter opens tweet intent with message` |
| TC-604 | FR-603 | `static/js/player.test.js` | `feedback social buttons > feedback-telegram opens share URL` |
| TC-701 | FR-701 | `static/js/player.test.js` | `share button click handlers > WhatsApp share opens correct URL` |
| TC-702 | FR-702 | `static/js/player.test.js` | `share button click handlers > Twitter share opens correct URL` |
| TC-703 | FR-703 | `static/js/player.test.js` | `share button click handlers > Telegram share opens correct URL` |
| TC-704 | FR-704 | `static/js/player.test.js` | `share button click handlers > Spotify search opens correct URL` |
| TC-705 | FR-705 | `static/js/player.test.js` | `share button click handlers > YouTube Music search opens correct URL` |
| TC-706 | FR-706 | `static/js/player.test.js` | `share button click handlers > Amazon Music search opens correct URL` |
| TC-707 | FR-707 | `static/js/player.test.js` | `recently played share handlers > prev-share-whatsapp opens with text when history exists` |
| TC-708 | FR-708 | `static/js/player.test.js` | `recently played share handlers > prev-share-twitter opens with text when history exists` |
| TC-801 | FR-801 | `static/js/player.test.js` | `applyTheme > sets data-theme attribute` |
| TC-802 | FR-801 | `static/js/player.test.js` | `applyTheme > sets data-theme attribute` |
| TC-803 | FR-802 | `static/js/player.test.js` | `applyTheme > persists to localStorage` |
| TC-804 | FR-803 | `static/js/player.test.js` | `updateStreamQualityDisplay > updates for AAC`, `STREAM_LABELS > has flac and aac entries` |
| TC-805 | FR-804 | `static/js/player.test.js` | `settings dropdown > toggles open class on settings button click`, `settings dropdown > closes on outside click` |
| TC-901 | NFR-101, NFR-102 | `tests/test_e2e.py` | `TestStaticFiles::test_static_cache_headers` |
| TC-902 | NFR-107, NFR-604 | `tests/playwright/radio-calico.spec.js` | Response header inspection for WebP content-type |
| TC-903 | NFR-203, NFR-204 | `tests/test_e2e.py` | `TestSecurityHeaders::test_x_content_type_options`, `test_x_frame_options`, `test_csp_header`, `test_permissions_policy`, `test_server_version_hidden` |
| TC-904 | NFR-402 | `tests/test_e2e.py` | `TestSecurityHeaders::test_request_id_header` |
| TC-905 | NFR-401, NFR-406 | `static/js/player.test.js` | `log > log.info outputs JSON to console.log`, `log > log.warn outputs JSON to console.warn`, `log > log.error outputs JSON to console.error` |
| TC-906 | NFR-505 | `tests/test_skills.py` | 169 slash command validation tests |

### 11.1 Selenium Browser Tests (`tests/test_browser.py`)

37 browser-based tests using Selenium + headless Chrome that automate previously manual test cases:

| Test Case | Selenium Test Class::Method |
|-----------|----------------------------|
| TC-101 | `TestAudioPlayback::test_play_button_visible`, `test_click_play_starts_loading` |
| TC-104 | `TestAudioPlayback::test_volume_slider_exists` |
| TC-105 | `TestAudioPlayback::test_mute_button_exists` |
| TC-201 | `TestPageLoad::test_artist_element_exists`, `test_track_element_exists` |
| TC-202 | `TestPageLoad::test_artwork_container_exists` |
| TC-301 | `TestRatings::test_click_thumbs_up` |
| TC-401 | `TestAuth::test_register_and_login_flow` |
| TC-406 | `TestAuth::test_logout` |
| TC-701-706 | `TestShareButtons::test_share_whatsapp_exists` through `test_share_amazon_exists` |
| TC-801 | `TestTheme::test_switch_to_light_theme` |
| TC-802 | `TestTheme::test_default_theme_is_dark`, `test_switch_back_to_dark_theme` |
| TC-803 | `TestTheme::test_theme_persists_on_reload` |
| TC-805 | `TestTheme::test_data_theme_attribute_changes` |
| TC-103 | `TestStreamQuality::test_quality_radios_exist`, `test_quality_label_shows` |
| Responsive | `TestResponsive::test_desktop_layout_has_two_columns`, `test_mobile_layout_at_narrow_width` |
| Drawer | `TestDrawer::test_drawer_opens`, `test_drawer_closes_via_button`, `test_drawer_closes_via_overlay` |

Run: `make test-browser` (requires Docker prod stack + Chrome)

---

## 12. Manual Test Procedures

The following test cases require manual execution because they involve subjective audio quality assessment and real-time streaming behavior that automated tests cannot evaluate.

### Manual Procedure: TC-101 - Play/Pause Toggle

**Environment**: Local dev (`http://127.0.0.1:5000`) or Docker prod (`http://127.0.0.1:5050`)

1. Open the app in Chrome (or Firefox/Safari)
2. Verify the play button (triangle icon) is visible in the player bar
3. Put on headphones or ensure speakers are on
4. Click the play button
5. **Verify**: Icon changes to a spinner (buffering indicator)
6. **Verify**: Within 2-10 seconds, the spinner changes to a pause icon
7. **Verify**: Audio output is heard through speakers/headphones
8. Click the pause icon
9. **Verify**: Icon changes back to the play triangle
10. **Verify**: Audio output stops immediately
11. Click play again
12. **Verify**: Audio resumes (may take a moment to rebuffer)

**Pass criteria**: All 12 verification steps pass. No JavaScript errors in console.

### Manual Procedure: TC-102 - Pause Stops Audio Output

**Environment**: Same as TC-101

1. Start playback (follow TC-101 steps 1-7)
2. Confirm audio is playing through speakers
3. Click the pause button
4. **Verify**: Audio stops within 1 second
5. **Verify**: The play icon is displayed
6. Wait 10 seconds
7. **Verify**: No audio output during the wait period
8. **Verify**: No errors in the browser console

**Pass criteria**: Audio completely stops on pause, no residual sound.

### Manual Procedure: TC-103 - Quality Switch (FLAC to AAC)

**Environment**: Same as TC-101, with DevTools Network tab open

1. Start playback in FLAC mode (default)
2. Open DevTools Network tab and filter by "m3u8" or "ts"
3. Note the current segment URLs (should reference FLAC variant)
4. Click the settings gear icon in the navbar
5. Select "AAC Hi-Fi (211 kbps)" radio button
6. **Verify**: The player briefly pauses and reinitializes
7. **Verify**: Audio resumes within 5 seconds
8. **Verify**: Quality label updates to "AAC Hi-Fi (211 kbps)"
9. **Verify**: Network requests show AAC variant segments
10. Open `localStorage` in DevTools Application tab
11. **Verify**: `rc-stream-quality` is set to "aac"
12. Repeat steps 4-11 switching back to FLAC

**Pass criteria**: Quality switches successfully in both directions. Playback resumes without user re-clicking play.

### Manual Procedure: TC-104 - Volume Control

**Environment**: Same as TC-101

1. Start playback
2. Locate the volume slider in the player bar
3. Set the slider to approximately 100% (rightmost)
4. **Verify**: Audio is at maximum volume
5. Slowly drag the slider to the left (toward 0%)
6. **Verify**: Volume decreases gradually and smoothly
7. Set the slider to 0%
8. **Verify**: Audio is completely silent
9. Drag the slider back to approximately 50%
10. **Verify**: Audio resumes at moderate volume

**Pass criteria**: Volume changes are smooth and proportional to slider position. No audio pops or glitches during adjustment.

### Manual Procedure: TC-105 - Mute Toggle

**Environment**: Same as TC-101

1. Start playback at moderate volume (slider at ~50%)
2. Click the mute button
3. **Verify**: Audio is silenced immediately
4. **Verify**: Mute icon is displayed (speaker with X or line through it)
5. **Verify**: Volume slider position has not changed
6. Click the mute button again
7. **Verify**: Audio resumes at the same volume as before muting
8. **Verify**: Volume icon is restored

**Pass criteria**: Mute toggles cleanly without affecting the volume slider position. Audio resumes at the original level.

### Manual Procedure: TC-106 - HLS Fatal Error Recovery

**Environment**: Local dev or Docker, with DevTools Console open

1. Start playback and confirm audio is working
2. Open DevTools Console and filter for "player" logs
3. Disconnect from the network (disable Wi-Fi, or block `d3d4yli4hf5bmh.cloudfront.net` in hosts file)
4. Wait for the HLS error to appear in the console
5. **Verify**: Console shows retry attempt with ~4 second delay
6. Wait for subsequent retries
7. **Verify**: Retry delays increase (4s, 8s, 16s, 32s, 60s max)
8. Reconnect to the network before 10 retries are exhausted
9. **Verify**: The player successfully reconnects and audio resumes
10. **Verify**: Retry counter resets on successful connection

**Pass criteria**: Exponential backoff is observed in console logs. Audio recovers after network restoration (within the 10-retry window).

---

## 13. Test Execution Summary

**Test run date**: 2026-03-24 — all automated suites executed locally (MySQL 5.7 + Docker prod stack).

**Results**: 52 TCs verified across automated suites — **52 ✅ Approved, 0 ❌ Rejected**. 1 TC require manual execution.

**Test Type key**: JS Unit = Jest/jsdom (`player.test.js`) · Python Unit = pytest (`test_app.py`) · Integration = pytest (`test_integration.py`) · E2E = pytest (`test_e2e.py`) · Browser = Selenium (`test_browser.py`) · Playwright = Playwright + Chromium (`radio-calico.spec.js`) · Skills = pytest (`test_skills.py`) · Manual = requires human interaction

**Note**: Playwright automates previously manual V&V test cases (TC-106, TC-902) using network interception and response header inspection.

**Status legend**: ✅ **Approved** &nbsp; ❌ **Rejected** &nbsp; 🚧 **Blocked** &nbsp; 🔕 **Ignored** &nbsp; ⬛ **Not Executed**

| TC ID | Category | Test Type | Executed By | Date | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| TC-101 | Audio Streaming | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** | Audio output requires manual verification |
| TC-102 | Audio Streaming | Manual | — | — | ⬛ **Not Executed** | Requires active audio hardware |
| TC-103 | Audio Streaming | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** | Audio quality requires manual verification |
| TC-104 | Audio Streaming | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** | Volume level requires manual verification |
| TC-105 | Audio Streaming | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** | Mute output requires manual verification |
| TC-106 | Audio Streaming | Playwright | — | 2026-03-24 | ✅ **Approved** | Network interception simulates HLS failure |
| TC-201 | Track Metadata | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-202 | Track Metadata | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-203 | Track Metadata | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-204 | Track Metadata | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-205 | Track Metadata | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-206 | Track Metadata | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-207 | Track Metadata | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-301 | Ratings | JS Unit + Python Unit + Browser | Jest + pytest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-302 | Ratings | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-303 | Ratings | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-304 | Ratings | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-305 | Ratings | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-306 | Ratings | Integration | pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-401 | Authentication | JS Unit + Python Unit + Browser | Jest + pytest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-402 | Authentication | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-403 | Authentication | Python Unit + Integration | pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-404 | Authentication | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-405 | Authentication | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-406 | Authentication | JS Unit + Python Unit + Browser | Jest + pytest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-407 | Authentication | Integration | pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-501 | User Profile | Python Unit + Integration | pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-502 | User Profile | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-503 | User Profile | Python Unit + Integration | pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-504 | User Profile | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-601 | Feedback | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-602 | Feedback | JS Unit + Python Unit | Jest + pytest | 2026-03-24 | ✅ **Approved** |  |
| TC-603 | Feedback | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-604 | Feedback | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-701 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-702 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-703 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-704 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-705 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-706 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-707 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-708 | Social Sharing | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-801 | Theme & Settings | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-802 | Theme & Settings | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-803 | Theme & Settings | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-804 | Theme & Settings | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-805 | Theme & Settings | JS Unit + Browser | Jest + Selenium | 2026-03-24 | ✅ **Approved** |  |
| TC-901 | Non-Functional | E2E | pytest | 2026-03-24 | ✅ **Approved** | Docker prod stack required |
| TC-902 | Non-Functional | Playwright | — | 2026-03-24 | ✅ **Approved** | Response header inspection for WebP content-type |
| TC-903 | Non-Functional | E2E | pytest | 2026-03-24 | ✅ **Approved** | Docker prod stack required |
| TC-904 | Non-Functional | E2E | pytest | 2026-03-24 | ✅ **Approved** | Docker prod stack required |
| TC-905 | Non-Functional | JS Unit | Jest | 2026-03-24 | ✅ **Approved** |  |
| TC-906 | Non-Functional | Skills | pytest | 2026-03-24 | ✅ **Approved** | 291 skill + agent validation tests |
