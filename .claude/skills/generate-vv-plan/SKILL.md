<!-- Radio Calico Skill v1.0.0 -->
Generate or update the Verification & Validation (V&V) test plan for Radio Calico.

### Output file

Create/update `docs/vv-test-plan.md` with a complete V&V test plan written from the user's perspective.

### Document layout

1. **Title & Metadata** — use this exact header layout (logo right, version table left, vertically centered). Read version from `VERSION` file; set date to today:

   ```html
   <table><tr>
   <td valign="middle">

   # Radio Calico - Verification & Validation Test Plan

   | Field | Value |
   | --- | --- |
   | **Project** | Radio Calico |
   | **Version** | 1.0.0 |
   | **Date** | YYYY-MM-DD |
   | **Status** | Draft |
   | **Author** | QA Team |

   </td>
   <td valign="middle" width="20%" align="right"><img src="../RadioCalicoLogoTM.png" alt="Radio Calico Logo" width="100%"></td>
   </tr></table>

   ---

   ## Table of Contents
   ...

   ---
   ```

   References: `docs/requirements.md`, `docs/tech-spec.md`

2. **Test Plan Overview**
   - Objectives: verify all functional/non-functional requirements
   - Test levels: unit, integration, E2E, manual acceptance
   - Tools: pytest, Jest, requests, browser (manual)
   - Environments: local (Flask + MySQL), Docker prod (nginx + gunicorn + MySQL)

3. **Test Cases — Audio Streaming**
   Write user-facing test cases for each streaming feature:

   ```
   **TC-1xx**: <Test Case Title>
   - Requirement: FR-1xx
   - Precondition: <Setup needed>
   - Steps:
     1. <User action>
     2. <User action>
     3. ...
   - Expected result: <What the user should see/hear>
   - Automated: Yes/No (link to test file + test name if automated)
   ```

   Derive from `static/js/player.js`:
   - TC-101: Play audio stream (click play, hear audio)
   - TC-102: Pause audio stream (click pause, audio stops)
   - TC-103: Switch stream quality FLAC → AAC
   - TC-104: Adjust volume slider
   - TC-105: Mute/unmute toggle
   - TC-106: HLS error recovery (stream reconnects after network drop)

4. **Test Cases — Track Metadata**
   - TC-201: Current track displays artist, title, album
   - TC-202: Album artwork loads from iTunes
   - TC-203: Song duration shows elapsed/total time
   - TC-204: Track change updates display when new song starts
   - TC-205: Recently played list accumulates tracks
   - TC-206: Filter recently played by liked/disliked
   - TC-207: Change history limit (5/10/15/20)

5. **Test Cases — Ratings**
   - TC-301: Rate a track thumbs up (count increments)
   - TC-302: Rate a track thumbs down (count increments)
   - TC-303: Cannot rate same track twice (buttons disabled after rating)
   - TC-304: Rating persists across page reload
   - TC-305: Rating badges show in recently played list
   - TC-306: Different songs can be rated independently

6. **Test Cases — Authentication**
   - TC-401: Register new account (valid username/password)
   - TC-402: Register fails with short password (<8 chars)
   - TC-403: Register fails with duplicate username
   - TC-404: Login with valid credentials (drawer switches to profile)
   - TC-405: Login fails with wrong password
   - TC-406: Logout clears session (drawer switches to auth)
   - TC-407: Protected endpoints reject unauthenticated requests

7. **Test Cases — User Profile**
   - TC-501: View empty profile after first login
   - TC-502: Update profile (nickname, email, genres, about)
   - TC-503: Profile persists after logout and re-login
   - TC-504: Genre checkboxes reflect saved genres

8. **Test Cases — Feedback**
   - TC-601: Submit feedback message (success confirmation)
   - TC-602: Submit empty feedback (validation error)
   - TC-603: Share feedback via Twitter button
   - TC-604: Share feedback via Telegram button

9. **Test Cases — Social Sharing**
   - TC-701: Share now playing via WhatsApp
   - TC-702: Share now playing via X/Twitter
   - TC-703: Share now playing via Telegram
   - TC-704: Search current track on Spotify
   - TC-705: Search current track on YouTube Music
   - TC-706: Search current track on Amazon Music
   - TC-707: Share recently played list via WhatsApp
   - TC-708: Share recently played list via X/Twitter

10. **Test Cases — Theme & Settings**
    - TC-801: Switch to light theme (colors change)
    - TC-802: Switch to dark theme (colors change)
    - TC-803: Theme persists after page reload
    - TC-804: Stream quality selection persists after reload
    - TC-805: Settings dropdown opens/closes

11. **Test Cases — Non-Functional**
    - TC-901: Page loads within 3 seconds on broadband
    - TC-902: WebP images served (check Network tab)
    - TC-903: Security headers present (X-Content-Type-Options, CSP, etc.)
    - TC-904: API returns X-Request-ID header
    - TC-905: Structured JSON logs in Docker container
    - TC-906: All 15 slash commands have version headers

12. **Automated Test Coverage Matrix**
    - Table mapping each TC to automated test(s):
      | TC ID | Automated? | Test File | Test Name |
    - Read actual tests from:
      - `api/test_app.py` (61 unit tests)
      - `api/test_integration.py` (19 integration tests)
      - `static/js/player.test.js` (162 JS tests)
      - `tests/test_e2e.py` (19 E2E tests)
      - `tests/test_skills.py` (112 skill tests)

13. **Manual Test Procedures**
    - For test cases NOT covered by automation, provide step-by-step manual procedures
    - Primarily audio playback (TC-101 to TC-106) — requires actual audio output

14. **Test Execution Summary** — run all automated suites and fill in real results:
    - Columns: TC ID | Category | Test Type | Executed By | Date | Status | Notes
    - **Test Type** values: JS Unit · Python Unit · Integration · E2E · Browser · Skills · Manual (or combinations with `+`)
    - **Executed By**: the test framework (Jest, pytest, Selenium, etc.)
    - **Status** (emoji + bold in each table cell):
      - `✅ **Approved**` — tests passed (dark green) &nbsp;&nbsp; `❌ **Rejected**` — tests failed (dark red)
      - `🚧 **Blocked**` — environment unavailable (dark yellow) &nbsp;&nbsp; `🔕 **Ignored**` — skipped by design (dark gray)
      - `⬛ **Not Executed**` — manual-only, not yet run (dark black)
    - Add a **Status legend** line above the table using `&nbsp;` spacers between entries
    - Manual-only TCs (TC-102, TC-106, TC-902) always use `⬛ **Not Executed**`
    - Add a summary line above the table: "N automated tests across N suites — N ✅ Approved, N ❌ Rejected"
    - Table separator must use `| --- |` style (not `|---|`)

### Steps

1. **Read** all test files to map existing automated coverage
2. **Read** `docs/requirements.md` for requirement IDs (run `/generate-requirements` first if missing)
3. **Read** `static/js/player.js` and `api/app.py` to verify user-facing behavior
4. **Generate** all test cases with detailed user-perspective steps
5. **Map** each test case to automated tests where they exist
6. **Identify** gaps where manual testing is needed
7. **Run** all automated test suites:
   - Start MySQL: `brew services start mysql@5.7`
   - `make test` (Python unit + JS unit)
   - `make test-integration`
   - `make test-skills`
   - `make docker-prod` then `make test-e2e` and `make test-browser`
8. **Fill** section 14 with real pass/fail results from step 7
9. **Report** total test cases, automation coverage percentage, and any failures

> **Note**: Use the `/vv-plan-updater` agent to re-run steps 7–8 at any time without regenerating the full plan.
