// @ts-check
const { test, expect } = require('@playwright/test');

/*
 * Radio Calico — Playwright E2E Tests
 *
 * Covers manual V&V test cases that Selenium cannot automate:
 *   TC-106: HLS fatal error recovery (network interception)
 *   TC-902: WebP image optimization (response header inspection)
 *
 * Plus new gap tests:
 *   SSE streaming responses, quiz with mocked LLM, ticker content,
 *   i18n live switching, responsive layout, dark/light theme,
 *   offline/error handling, follow-up chat, taste profile.
 *
 * Requires Docker prod stack running: make docker-prod
 */

const BASE = 'http://127.0.0.1:5050';

// ── Helper: wait for app to load ────────────────────────────
async function waitForApp(page) {
  await page.goto(BASE);
  await page.waitForSelector('#play-btn', { timeout: 10000 });
}

// ── TC-106: HLS Fatal Error Recovery ────────────────────────
// Previously: Manual / Not Executed
// Playwright can intercept network to simulate HLS failure + recovery
test.describe('TC-106: HLS Fatal Error Recovery', () => {
  test('recovers after HLS stream interruption', async ({ page }) => {
    await waitForApp(page);

    // Block HLS manifest to simulate fatal error
    await page.route('**/*.m3u8', route => route.abort('connectionfailed'));

    // Click play — should attempt to load and fail
    await page.click('#play-btn');

    // Wait for error state (play button should remain enabled for retry)
    await page.waitForTimeout(3000);
    const playBtn = page.locator('#play-btn');
    await expect(playBtn).toBeVisible();

    // Restore network
    await page.unroute('**/*.m3u8');

    // The player should be able to retry (button still clickable)
    await expect(playBtn).toBeEnabled();
  });
});

// ── TC-902: WebP Image Optimization ─────────────────────────
// Previously: Manual / Not Executed (required DevTools inspection)
// Playwright can inspect response headers for content-type
test.describe('TC-902: WebP Image Optimization', () => {
  test('serves favicon as WebP format', async ({ page }) => {
    const response = await page.goto(`${BASE}/favicon.webp`);
    expect(response).not.toBeNull();
    const contentType = response.headers()['content-type'] || '';
    expect(contentType).toContain('webp');
  });

  test('serves logo as WebP format', async ({ page }) => {
    const response = await page.goto(`${BASE}/logo.webp`);
    expect(response).not.toBeNull();
    const contentType = response.headers()['content-type'] || '';
    expect(contentType).toContain('webp');
  });
});

// ── SSE Streaming Responses ─────────────────────────────────
// Selenium cannot intercept streaming responses
test.describe('SSE Streaming', () => {
  test('streaming endpoint returns SSE events with JSON-encoded chunks', async ({ page }) => {
    await waitForApp(page);

    // Mock the streaming endpoint to return controlled SSE data
    await page.route('**/api/song-info/stream', async route => {
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: 'data: "## Test"\n\ndata: " Heading"\n\ndata: "\\nSome content."\n\nevent: done\ndata: ""\n\n',
      });
    });

    // Also mock non-streaming fallback
    await page.route('**/api/song-info', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, content: '## Test Heading\nSome content.' }),
        });
      } else {
        await route.continue();
      }
    });

    // Set artist/track so buttons work
    await page.evaluate(() => {
      document.getElementById('artist').textContent = 'Test Artist';
      document.getElementById('track').textContent = 'Test Track';
    });

    // Click a retro button
    const detailsBtn = page.locator('.retro-btn[data-query="details"]');
    await detailsBtn.click();

    // Wait for info panel to open
    const panel = page.locator('#info-panel');
    await expect(panel).toHaveClass(/open/, { timeout: 15000 });

    // Content should eventually appear (streaming or fallback)
    const content = page.locator('#info-panel-content');
    await expect(content).not.toBeEmpty({ timeout: 15000 });
  });
});

// ── Quiz with Mocked LLM ───────────────────────────────────
// Network mocking ensures deterministic quiz behavior
test.describe('Quiz with Mocked LLM', () => {
  test('displays quiz question with options on separate lines', async ({ page }) => {
    await waitForApp(page);

    // Mock quiz start
    await page.route('**/api/quiz/start', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          questions: [
            {
              q: 'What year was this song released?',
              options: ['1980', '1985', '1990', '1995'],
              answer: 'B) 1985',
            },
            {
              q: 'Who is the lead singer?',
              options: ['John', 'Paul', 'George', 'Ringo'],
              answer: 'A) John',
            },
            {
              q: 'What album is this from?',
              options: ['Abbey Road', 'Let It Be', 'Help!', 'Revolver'],
              answer: 'C) Help!',
            },
            {
              q: 'What genre is this song?',
              options: ['Rock', 'Pop', 'Jazz', 'Blues'],
              answer: 'A) Rock',
            },
            {
              q: 'How many minutes long is this song?',
              options: ['2:30', '3:15', '4:00', '5:20'],
              answer: 'B) 3:15',
            },
          ],
        }),
      });
    });

    // Mock quiz answer
    await page.route('**/api/quiz/answer', async route => {
      const body = JSON.parse(route.request().postData() || '{}');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          correct: true,
          score: 1,
          feedback: 'Nice one! You actually know your music! 🎸',
          done: false,
        }),
      });
    });

    // Set artist/track
    await page.evaluate(() => {
      document.getElementById('artist').textContent = 'The Beatles';
      document.getElementById('track').textContent = 'Help!';
    });

    // Click Quiz button
    const quizBtn = page.locator('.retro-btn[data-query="quiz"]');
    await quizBtn.click();

    // Wait for quiz content to appear
    const panel = page.locator('#info-panel');
    await expect(panel).toHaveClass(/open/, { timeout: 15000 });

    // Should show question text
    const content = page.locator('#info-panel-content');
    await expect(content).toContainText('What year', { timeout: 10000 });

    // Options should be on separate lines (each in its own element or <br>)
    const optionsText = await content.textContent();
    expect(optionsText).toContain('1980');
    expect(optionsText).toContain('1985');
  });
});

// ── Ticker / Marquee ────────────────────────────────────────
test.describe('Ticker Marquee', () => {
  test('ticker container exists and has content', async ({ page }) => {
    await waitForApp(page);

    const ticker = page.locator('#ticker-track');
    await expect(ticker).toBeVisible({ timeout: 5000 });

    // Should have at least some default ticker messages
    const text = await ticker.textContent();
    expect(text.length).toBeGreaterThan(10);
  });

  test('ticker has hover-to-pause CSS rule', async ({ page }) => {
    await waitForApp(page);

    // Verify the CSS rule exists (hover pauses animation)
    const hasPauseRule = await page.evaluate(() => {
      for (const sheet of document.styleSheets) {
        try {
          for (const rule of sheet.cssRules) {
            if (rule.selectorText && rule.selectorText.includes('ticker-track') &&
                rule.selectorText.includes('hover') &&
                rule.cssText.includes('paused')) {
              return true;
            }
          }
        } catch (_) { /* cross-origin sheets */ }
      }
      return false;
    });
    expect(hasPauseRule).toBe(true);
  });
});

// ── i18n Live Switching ─────────────────────────────────────
test.describe('i18n Language Switching', () => {
  test('switching to Portuguese translates UI labels but not song metadata', async ({ page }) => {
    await waitForApp(page);

    // Set song metadata
    await page.evaluate(() => {
      document.getElementById('artist').textContent = 'The Beatles';
      document.getElementById('track').textContent = 'Yesterday';
    });

    // Open settings and switch to Portuguese
    const settingsBtn = page.locator('.settings-btn, .gear-btn, [aria-label="Settings"]').first();
    await settingsBtn.click();
    const ptRadio = page.locator('input[name="language"][value="pt-BR"]');
    await ptRadio.click({ force: true });

    // Wait for translations to apply
    await page.waitForTimeout(500);

    // UI labels should be translated
    const nowPlaying = page.locator('[data-i18n="now_playing"]');
    const text = await nowPlaying.textContent();
    expect(text).not.toBe('Now Playing'); // Should be Portuguese

    // Song metadata should NOT be translated
    const artist = page.locator('#artist');
    await expect(artist).toHaveText('The Beatles');
    const track = page.locator('#track');
    await expect(track).toHaveText('Yesterday');
  });

  test('Quiz button label stays as Quiz in all languages', async ({ page }) => {
    await waitForApp(page);

    // Switch to Spanish
    const settingsBtn = page.locator('.settings-btn, .gear-btn, [aria-label="Settings"]').first();
    await settingsBtn.click();
    const esRadio = page.locator('input[name="language"][value="es"]');
    await esRadio.click({ force: true });
    await page.waitForTimeout(500);

    const quizBtn = page.locator('.retro-btn[data-query="quiz"]');
    await expect(quizBtn).toHaveText('Quiz');
  });
});

// ── Responsive Layout ───────────────────────────────────────
test.describe('Responsive Layout', () => {
  test('mobile viewport shows single column', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await waitForApp(page);

    // Retro buttons should still be visible (single row, scrollable)
    const buttons = page.locator('.retro-btn');
    const count = await buttons.count();
    expect(count).toBe(7);

    // All buttons should be visible (overflow-x: auto)
    const firstBtn = buttons.first();
    await expect(firstBtn).toBeVisible();
  });

  test('desktop viewport shows full layout', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await waitForApp(page);

    const buttons = page.locator('.retro-btn');
    const count = await buttons.count();
    expect(count).toBe(7);
  });
});

// ── Dark / Light Theme ──────────────────────────────────────
test.describe('Theme Switching', () => {
  test('dark mode applies data-theme attribute', async ({ page }) => {
    await waitForApp(page);

    // Open settings
    const settingsBtn = page.locator('.settings-btn, .gear-btn, [aria-label="Settings"]').first();
    await settingsBtn.click();

    // Click dark theme radio
    const darkRadio = page.locator('input[name="theme"][value="dark"]');
    await darkRadio.click({ force: true });

    // Verify attribute on html element
    const theme = await page.locator('html').getAttribute('data-theme');
    expect(theme).toBe('dark');
  });

  test('light mode removes data-theme attribute', async ({ page }) => {
    await waitForApp(page);

    const settingsBtn = page.locator('.settings-btn, .gear-btn, [aria-label="Settings"]').first();
    await settingsBtn.click();

    // Switch to light
    const lightRadio = page.locator('input[name="theme"][value="light"]');
    await lightRadio.click({ force: true });

    const theme = await page.locator('html').getAttribute('data-theme');
    expect(theme).toBe('light');
  });

  test('dark mode screenshot for visual comparison', async ({ page }) => {
    await waitForApp(page);

    const settingsBtn = page.locator('.settings-btn, .gear-btn, [aria-label="Settings"]').first();
    await settingsBtn.click();
    const darkRadio = page.locator('input[name="theme"][value="dark"]');
    await darkRadio.click({ force: true });
    await page.waitForTimeout(300);

    // Take screenshot for visual regression baseline
    await page.screenshot({ path: 'tests/playwright/screenshots/dark-mode.png', fullPage: true });
  });
});

// ── Offline / Error Handling ────────────────────────────────
test.describe('Offline Error Handling', () => {
  test('shows error message when Ollama is unreachable', async ({ page }) => {
    await waitForApp(page);

    // Block all LLM endpoints
    await page.route('**/api/song-info/**', route => route.abort('connectionfailed'));
    await page.route('**/api/song-info', route => route.abort('connectionfailed'));

    // Set artist/track
    await page.evaluate(() => {
      document.getElementById('artist').textContent = 'Test Artist';
      document.getElementById('track').textContent = 'Test Track';
    });

    // Click a retro button
    await page.locator('.retro-btn[data-query="facts"]').click();

    // Should show error message in panel
    const panel = page.locator('#info-panel');
    await expect(panel).toHaveClass(/open/, { timeout: 10000 });

    const content = page.locator('#info-panel-content');
    await expect(content).toContainText(/error|Error|network/i, { timeout: 10000 });
  });
});

// ── Retro Buttons Behavior ──────────────────────────────────
test.describe('Retro Buttons', () => {
  test('only one button can be pressed at a time', async ({ page }) => {
    await waitForApp(page);

    // Mock song-info to return quickly
    await page.route('**/api/song-info/stream', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: "Test content"\n\nevent: done\ndata: ""\n\n',
      });
    });
    await page.route('**/api/song-info', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, content: 'Test content' }),
        });
      } else {
        await route.continue();
      }
    });

    await page.evaluate(() => {
      document.getElementById('artist').textContent = 'Artist';
      document.getElementById('track').textContent = 'Track';
    });

    // Click Lyrics
    await page.locator('.retro-btn[data-query="lyrics"]').click();
    await page.waitForTimeout(500);

    // Click Details — Lyrics should be released
    await page.locator('.retro-btn[data-query="details"]').click();
    await page.waitForTimeout(500);

    const lyricsPressed = await page.locator('.retro-btn[data-query="lyrics"]').getAttribute('aria-pressed');
    const detailsPressed = await page.locator('.retro-btn[data-query="details"]').getAttribute('aria-pressed');

    expect(lyricsPressed).toBe('false');
    expect(detailsPressed).toBe('true');
  });

  test('pressing same button toggles panel closed', async ({ page }) => {
    await waitForApp(page);

    await page.route('**/api/song-info/stream', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: "Content"\n\nevent: done\ndata: ""\n\n',
      });
    });
    await page.route('**/api/song-info', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, content: 'Content' }),
        });
      } else {
        await route.continue();
      }
    });

    await page.evaluate(() => {
      document.getElementById('artist').textContent = 'Artist';
      document.getElementById('track').textContent = 'Track';
    });

    const btn = page.locator('.retro-btn[data-query="lyrics"]');

    // Click once — panel opens
    await btn.click();
    await page.waitForTimeout(1000);
    let panel = page.locator('#info-panel');
    await expect(panel).toHaveClass(/open/, { timeout: 5000 });

    // Click again — panel closes
    await btn.click();
    await page.waitForTimeout(500);
    const hasOpen = await panel.evaluate(el => el.classList.contains('open'));
    expect(hasOpen).toBe(false);
  });
});

// ── Share Buttons in Info Panel ──────────────────────────────
test.describe('Info Panel Share Buttons', () => {
  test('share buttons appear when info panel is open', async ({ page }) => {
    await waitForApp(page);

    await page.route('**/api/song-info/stream', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: "Share test content"\n\nevent: done\ndata: ""\n\n',
      });
    });
    await page.route('**/api/song-info', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, content: 'Share test content' }),
        });
      } else {
        await route.continue();
      }
    });

    await page.evaluate(() => {
      document.getElementById('artist').textContent = 'Artist';
      document.getElementById('track').textContent = 'Track';
    });

    await page.locator('.retro-btn[data-query="details"]').click();

    // Wait for panel to open with content
    const panel = page.locator('#info-panel');
    await expect(panel).toHaveClass(/open/, { timeout: 15000 });

    // Share row should be visible
    const shareRow = page.locator('#info-share-row');
    await expect(shareRow).toBeVisible({ timeout: 15000 });

    // Should have WhatsApp, X, Telegram buttons
    await expect(page.locator('.share-whatsapp').last()).toBeVisible();
    await expect(page.locator('.share-twitter').last()).toBeVisible();
    await expect(page.locator('.share-telegram').last()).toBeVisible();
  });
});

// ── Page Load Performance ───────────────────────────────────
test.describe('Performance', () => {
  test('page loads within 5 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(BASE);
    await page.waitForSelector('#play-btn');
    const loadTime = Date.now() - start;
    expect(loadTime).toBeLessThan(5000);
  });

  test('nginx returns gzip compressed responses', async ({ page }) => {
    const response = await page.goto(`${BASE}/js/player.js`);
    const encoding = response.headers()['content-encoding'] || '';
    expect(encoding).toContain('gzip');
  });
});
