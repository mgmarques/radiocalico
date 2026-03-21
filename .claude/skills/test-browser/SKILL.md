<!-- Radio Calico Skill v2.0.0 -->
Run Selenium browser tests against the Docker production stack.

## Agent
Delegate this entire skill to the **QA Engineer** subagent (`qa-engineer`).
The QA Engineer has specialized knowledge of all 6 test suites, coverage thresholds, and the CI pipeline. It will run all steps in an isolated context window and return only a summary to the main conversation.

### Steps

1. **Check Docker prod is running**: `docker compose --profile prod ps`
   - If not running, start it: `make docker-prod`
   - Wait for healthy: `curl -sf http://127.0.0.1:5050/health`

2. **Run browser tests**: `make test-browser`
   - Runs 37 Selenium tests with headless Chrome
   - Tests: page load, theme switching, ratings, drawer, auth flow, share buttons, responsive layout, audio playback, stream quality

3. **Report results**:
   - Total passed/failed
   - For each failure: test name, what was expected, what happened
   - Screenshot hint: if a visual test fails, suggest running with `BROWSER_HEADLESS=false` to see the browser

4. **If tests fail**, investigate:
   - Docker not running → `make docker-prod`
   - Chrome not installed → `brew install --cask google-chrome` or check CI uses `browser-actions/setup-chrome`
   - Timeout errors → increase `WAIT_TIMEOUT` in test_browser.py or check if stream is live
   - Stale state → `Cmd+Shift+R` in browser, or `docker compose --profile prod down && make docker-prod`

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `E2E_BASE_URL` | `http://127.0.0.1:5050` | App URL to test against |
| `BROWSER_HEADLESS` | `true` | Set to `false` to watch the browser |

### Examples

```bash
# Headless (default, CI mode)
make test-browser

# Watch the browser (debugging)
BROWSER_HEADLESS=false make test-browser

# Against a different URL
E2E_BASE_URL=http://staging.example.com make test-browser

# Run a single test class
E2E_BASE_URL=http://127.0.0.1:5050 pytest tests/test_browser.py::TestTheme -v

# Run a single test
E2E_BASE_URL=http://127.0.0.1:5050 pytest tests/test_browser.py::TestAuth::test_register_and_login_flow -v
```

### Test coverage

| Class | Tests | What it verifies |
|-------|-------|-----------------|
| TestPageLoad | 9 | All critical UI elements render (navbar, logo, player, artwork, footer) |
| TestTheme | 5 | Dark/light toggle, persistence on reload, data-theme attribute |
| TestRatings | 3 | Buttons visible, counts display, click interaction |
| TestDrawer | 4 | Open/close via button and overlay, auth section exists |
| TestAuth | 2 | Register → login → profile view, logout |
| TestShareButtons | 6 | All 6 share/search buttons visible |
| TestResponsive | 2 | Desktop 2-column layout, mobile narrow viewport |
| TestAudioPlayback | 4 | Play button, loading state, volume slider, mute button |
| TestStreamQuality | 2 | Quality radio buttons, quality label text |

### Prerequisites

- Docker prod stack running (`make docker-prod`)
- Chrome/Chromium installed (or `webdriver-manager` auto-downloads chromedriver)
- Python packages: `selenium`, `webdriver-manager` (auto-installed by `make test-browser`)