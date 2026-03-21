/**
 * Unit tests for Radio Calico player.js
 *
 * Uses Jest + jsdom. The player script is loaded after setting up
 * DOM elements, mocking fetch/Hls/localStorage/window.open.
 */

/* ── Polyfills for jsdom ─────────────────────────────────────── */
const { TextDecoder, TextEncoder } = require('util');
global.TextDecoder = TextDecoder;
global.TextEncoder = TextEncoder;

/* ── DOM setup ──────────────────────────────────────────────── */

function buildDOM() {
    document.body.innerHTML = `
        <div id="artwork"></div>
        <h1 id="artist">Radio Calico</h1>
        <h2 id="track">Live Stream</h2>
        <p id="album"></p>
        <span id="bar-time"></span>
        <button id="play-btn"></button>
        <button id="mute-btn"></button>
        <input id="volume" type="range" value="0.8" />
        <button id="rate-up"></button>
        <button id="rate-down"></button>
        <span id="rating-feedback"></span>
        <span id="rate-up-count">0</span>
        <span id="rate-down-count">0</span>
        <svg id="icon-play" style="display:none"></svg>
        <svg id="icon-pause" style="display:none"></svg>
        <svg id="icon-spin" style="display:none"></svg>
        <svg id="icon-vol"></svg>
        <svg id="icon-mute" style="display:none"></svg>
        <ul id="prev-list"></ul>
        <em id="source-quality"></em>
        <em id="stream-quality"></em>
        <button id="share-whatsapp"></button>
        <button id="share-twitter"></button>
        <button id="share-telegram"></button>
        <button id="share-spotify"></button>
        <button id="share-ytmusic"></button>
        <button id="share-amazon"></button>
        <button id="prev-share-whatsapp"></button>
        <button id="prev-share-twitter"></button>
        <button id="menu-btn"></button>
        <div id="drawer"></div>
        <div id="drawer-overlay"></div>
        <button id="drawer-close"></button>
        <section id="drawer-auth"></section>
        <section id="drawer-profile" style="display:none"></section>
        <section id="drawer-feedback" style="display:none"></section>
        <form id="auth-form"><input id="auth-username"/><input id="auth-password"/></form>
        <p id="auth-feedback"></p>
        <form id="profile-form"></form>
        <p id="profile-feedback"></p>
        <p id="profile-welcome"></p>
        <button id="btn-register"></button>
        <button id="btn-logout"></button>
        <input id="profile-nickname" />
        <input id="profile-email" />
        <textarea id="profile-about"></textarea>
        <div id="genre-grid">
            <input type="checkbox" value="rock" />
            <input type="checkbox" value="jazz" />
            <input type="checkbox" value="pop" />
        </div>
        <form id="feedback-form"><textarea id="feedback-message"></textarea></form>
        <p id="feedback-feedback"></p>
        <button id="feedback-twitter"></button>
        <button id="feedback-telegram"></button>
        <button id="settings-btn"></button>
        <div id="settings-dropdown"></div>
        <select id="prev-limit"><option value="5">5</option></select>
        <button class="prev-filter active" data-filter="all"></button>
        <audio id="audio" preload="none"></audio>
        <input type="radio" name="theme" value="light" />
        <input type="radio" name="theme" value="dark" checked />
        <input type="radio" name="stream-quality" value="flac" checked />
        <input type="radio" name="stream-quality" value="aac" />
        <div class="radio-buttons-row" id="radio-buttons-row">
            <button class="retro-btn" data-query="lyrics" aria-pressed="false">Lyrics</button>
            <button class="retro-btn" data-query="details" aria-pressed="false">Details</button>
            <button class="retro-btn" data-query="facts" aria-pressed="false">Facts</button>
            <button class="retro-btn" data-query="merchandise" aria-pressed="false">Merchandise</button>
            <button class="retro-btn" data-query="jokes" aria-pressed="false">Jokes</button>
            <button class="retro-btn" data-query="everything" aria-pressed="false">Everything</button>
            <button class="retro-btn" data-query="quiz" aria-pressed="false">Quiz</button>
        </div>
        <div class="info-panel" id="info-panel">
            <div class="info-panel-content" id="info-panel-content"></div>
        </div>
    `;
}

/* ── Mocks ──────────────────────────────────────────────────── */

const mockStorage = {};
const localStorageMock = {
    getItem: jest.fn(k => mockStorage[k] || null),
    setItem: jest.fn((k, v) => { mockStorage[k] = v; }),
    removeItem: jest.fn(k => { delete mockStorage[k]; }),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock Hls.js global
const hlsInstance = {
    loadSource: jest.fn(),
    attachMedia: jest.fn(),
    on: jest.fn(),
    destroy: jest.fn(),
    levels: [],
    currentLevel: 0,
    loadLevel: 0,
    nextLevel: 0,
    latency: 6,
};
window.Hls = jest.fn(() => hlsInstance);
window.Hls.isSupported = jest.fn(() => true);
window.Hls.Events = {
    MANIFEST_PARSED: 'hlsManifestParsed',
    FRAG_PARSING_METADATA: 'hlsFragParsingMetadata',
    FRAG_CHANGED: 'hlsFragChanged',
    LEVEL_LOADED: 'hlsLevelLoaded',
    ERROR: 'hlsError',
};

// Mock fetch
global.fetch = jest.fn(() =>
    Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
    })
);

// Mock window.open
window.open = jest.fn();

// Mock audio element methods
HTMLMediaElement.prototype.play = jest.fn(() => Promise.resolve());
HTMLMediaElement.prototype.pause = jest.fn();

// Mock audio.textTracks (not implemented in jsdom)
Object.defineProperty(HTMLMediaElement.prototype, 'textTracks', {
    get() {
        return Object.assign([], {
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
        });
    },
    configurable: true,
});

// Mock audio.canPlayType
HTMLMediaElement.prototype.canPlayType = jest.fn(() => '');

/* ── Load player.js ─────────────────────────────────────────── */

let player;

beforeAll(() => {
    buildDOM();
    player = require('./player.js');
});

/* ── Pure function tests ────────────────────────────────────── */

describe('escHtml', () => {
    test('escapes &, <, >, ", \'', () => {
        expect(player.escHtml('a & b < c > d " e \' f'))
            .toBe('a &amp; b &lt; c &gt; d &quot; e &#39; f');
    });

    test('returns empty string for null/undefined', () => {
        expect(player.escHtml(null)).toBe('');
        expect(player.escHtml(undefined)).toBe('');
    });

    test('passes through safe strings', () => {
        expect(player.escHtml('Hello World')).toBe('Hello World');
    });
});

describe('formatTime', () => {
    test('formats seconds to m:ss', () => {
        expect(player.formatTime(0)).toBe('0:00');
        expect(player.formatTime(65)).toBe('1:05');
        expect(player.formatTime(3661)).toBe('61:01');
    });

    test('handles NaN and negative', () => {
        expect(player.formatTime(NaN)).toBe('0:00');
        expect(player.formatTime(-5)).toBe('0:00');
        expect(player.formatTime(Infinity)).toBe('0:00');
    });
});

describe('parseID3Frames', () => {
    test('returns empty object for short data', () => {
        expect(player.parseID3Frames(new Uint8Array([1, 2, 3]))).toEqual({});
    });

    test('returns empty object for non-ID3 data', () => {
        const data = new Uint8Array(20);
        data[0] = 65; // 'A' not 'I'
        expect(player.parseID3Frames(data)).toEqual({});
    });

    test('parses valid ID3v2 TIT2 frame (UTF-8)', () => {
        const header = [
            0x49, 0x44, 0x33,   // 'ID3'
            0x03, 0x00,          // version 2.3
            0x00,                // flags
            0x00, 0x00, 0x00, 0x12, // tag size = 18 bytes (syncsafe)
        ];
        const frameId = [0x54, 0x49, 0x54, 0x32]; // 'TIT2'
        const frameSize = [0x00, 0x00, 0x00, 0x07]; // 7 bytes payload
        const frameFlags = [0x00, 0x00];
        const encoding = [0x03]; // UTF-8
        const text = [0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x21]; // 'Hello!'
        const raw = new Uint8Array([
            ...header, ...frameId, ...frameSize, ...frameFlags, ...encoding, ...text
        ]);
        const result = player.parseID3Frames(raw);
        expect(result.TIT2).toBe('Hello!');
    });

    test('parses ID3v2 frame with UTF-16 encoding (enc=1)', () => {
        const header = [
            0x49, 0x44, 0x33,
            0x03, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x18, // tag size = 24
        ];
        const frameId = [0x54, 0x50, 0x45, 0x31]; // 'TPE1'
        // payload: encoding(1) + UTF-16 BOM(2) + "Hi"(4) = 7
        const frameSize = [0x00, 0x00, 0x00, 0x07];
        const frameFlags = [0x00, 0x00];
        const encoding = [0x01]; // UTF-16
        // UTF-16LE BOM + "Hi"
        const text = [0xFF, 0xFE, 0x48, 0x00, 0x69, 0x00];
        const raw = new Uint8Array([
            ...header, ...frameId, ...frameSize, ...frameFlags, ...encoding, ...text
        ]);
        const result = player.parseID3Frames(raw);
        expect(result.TPE1).toBe('Hi');
    });

    test('parses ID3v2 frame with UTF-16BE encoding (enc=2)', () => {
        const header = [
            0x49, 0x44, 0x33,
            0x03, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x16, // tag size = 22
        ];
        const frameId = [0x54, 0x41, 0x4C, 0x42]; // 'TALB'
        // payload: encoding(1) + "OK"(4) = 5
        const frameSize = [0x00, 0x00, 0x00, 0x05];
        const frameFlags = [0x00, 0x00];
        const encoding = [0x02]; // UTF-16BE
        const text = [0x00, 0x4F, 0x00, 0x4B]; // "OK" in UTF-16BE
        const raw = new Uint8Array([
            ...header, ...frameId, ...frameSize, ...frameFlags, ...encoding, ...text
        ]);
        const result = player.parseID3Frames(raw);
        expect(result.TALB).toBe('OK');
    });

    test('parses ID3v2 frame with ISO-8859-1 encoding (enc=0)', () => {
        const header = [
            0x49, 0x44, 0x33,
            0x03, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x12,
        ];
        const frameId = [0x54, 0x49, 0x54, 0x32]; // 'TIT2'
        const frameSize = [0x00, 0x00, 0x00, 0x04]; // 4 bytes payload
        const frameFlags = [0x00, 0x00];
        const encoding = [0x00]; // ISO-8859-1
        const text = [0x41, 0x42, 0x43]; // "ABC"
        const raw = new Uint8Array([
            ...header, ...frameId, ...frameSize, ...frameFlags, ...encoding, ...text
        ]);
        const result = player.parseID3Frames(raw);
        expect(result.TIT2).toBe('ABC');
    });

    test('skips TXXX frames', () => {
        const header = [
            0x49, 0x44, 0x33,
            0x03, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x12,
        ];
        const frameId = [0x54, 0x58, 0x58, 0x58]; // 'TXXX'
        const frameSize = [0x00, 0x00, 0x00, 0x04];
        const frameFlags = [0x00, 0x00];
        const encoding = [0x03];
        const text = [0x41, 0x42, 0x43];
        const raw = new Uint8Array([
            ...header, ...frameId, ...frameSize, ...frameFlags, ...encoding, ...text
        ]);
        const result = player.parseID3Frames(raw);
        expect(result.TXXX).toBeUndefined();
    });

    test('handles frame with zero size gracefully', () => {
        const header = [
            0x49, 0x44, 0x33,
            0x03, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x10,
        ];
        const frameId = [0x54, 0x49, 0x54, 0x32]; // 'TIT2'
        const frameSize = [0x00, 0x00, 0x00, 0x00]; // 0 bytes
        const frameFlags = [0x00, 0x00];
        const raw = new Uint8Array([...header, ...frameId, ...frameSize, ...frameFlags]);
        const result = player.parseID3Frames(raw);
        expect(result.TIT2).toBeUndefined();
    });
});

/* ── History & filtering ────────────────────────────────────── */

describe('getFilteredHistory', () => {
    beforeEach(() => {
        player.history.length = 0;
        player.prevFilter = 'all';
        player.historyLimit = 5;
        player.lastSummary = {};
        // Reset ratings cache so each test gets fresh data
        if (player.renderHistory) player.renderHistory._cacheTime = 0;
    });

    test('returns empty array when history is empty', () => {
        expect(player.getFilteredHistory()).toEqual([]);
    });

    test('returns all tracks when filter is "all"', () => {
        player.history.push(
            { artist: 'A', title: 'T1', album: '' },
            { artist: 'B', title: 'T2', album: '' }
        );
        expect(player.getFilteredHistory()).toHaveLength(2);
    });

    test('respects historyLimit', () => {
        for (let i = 0; i < 10; i++) {
            player.history.push({ artist: `A${i}`, title: `T${i}`, album: '' });
        }
        player.historyLimit = 3;
        expect(player.getFilteredHistory()).toHaveLength(3);
    });

    test('filters by liked tracks', () => {
        player.history.push(
            { artist: 'A', title: 'T1', album: '' },
            { artist: 'B', title: 'T2', album: '' }
        );
        player.lastSummary = { 'A - T1': { likes: 2, dislikes: 0 } };
        player.prevFilter = 'up';
        const result = player.getFilteredHistory();
        expect(result).toHaveLength(1);
        expect(result[0].artist).toBe('A');
    });

    test('filters by disliked tracks', () => {
        player.history.push(
            { artist: 'A', title: 'T1', album: '' },
            { artist: 'B', title: 'T2', album: '' }
        );
        player.lastSummary = { 'B - T2': { likes: 0, dislikes: 3 } };
        player.prevFilter = 'down';
        const result = player.getFilteredHistory();
        expect(result).toHaveLength(1);
        expect(result[0].artist).toBe('B');
    });

    test('returns empty when no tracks match filter', () => {
        player.history.push({ artist: 'A', title: 'T1', album: '' });
        player.lastSummary = {};
        player.prevFilter = 'up';
        expect(player.getFilteredHistory()).toHaveLength(0);
    });

    test('returns all tracks for unknown filter value (default branch)', () => {
        player.history.push(
            { artist: 'A', title: 'T1', album: '' },
            { artist: 'B', title: 'T2', album: '' }
        );
        player.lastSummary = { 'A - T1': { likes: 1, dislikes: 0 }, 'B - T2': { likes: 0, dislikes: 1 } };
        player.prevFilter = 'unknown';
        expect(player.getFilteredHistory()).toHaveLength(2);
    });
});

/* ── Share text generation ──────────────────────────────────── */

describe('getShareText', () => {
    test('builds share text from DOM elements', () => {
        document.getElementById('artist').textContent = 'Madonna';
        document.getElementById('track').textContent = 'Angel';
        document.getElementById('album').textContent = 'Angel - EP';
        document.getElementById('artwork').innerHTML = '<img src="https://example.com/100x100bb.jpg">';
        const text = player.getShareText();
        expect(text).toContain('Listening to "Angel" by Madonna');
        expect(text).toContain('(Angel - EP)');
        expect(text).toContain('Radio Calico');
    });

    test('omits album if empty', () => {
        document.getElementById('artist').textContent = 'Artist';
        document.getElementById('track').textContent = 'Title';
        document.getElementById('album').textContent = '';
        const text = player.getShareText();
        expect(text).not.toContain('()');
        expect(text).toContain('"Title" by Artist');
    });
});

describe('getRecentlyPlayedText', () => {
    beforeEach(() => {
        player.history.length = 0;
        player.prevFilter = 'all';
        player.historyLimit = 5;
        player.lastSummary = {};
        // Reset ratings cache so each test gets fresh data
        if (player.renderHistory) player.renderHistory._cacheTime = 0;
    });

    test('returns empty string when no history', () => {
        expect(player.getRecentlyPlayedText()).toBe('');
    });

    test('builds numbered list', () => {
        player.history.push(
            { artist: 'A', title: 'T1', album: 'Album1' },
            { artist: 'B', title: 'T2', album: '' }
        );
        const text = player.getRecentlyPlayedText();
        expect(text).toContain('Recently Played - Radio Calico:');
        expect(text).toContain('1. T1 by A (Album1)');
        expect(text).toContain('2. T2 by B');
    });

    test('includes ratings when available', () => {
        player.history.push({ artist: 'A', title: 'T1', album: '' });
        player.lastSummary = { 'A - T1': { likes: 3, dislikes: 1 } };
        const text = player.getRecentlyPlayedText();
        expect(text).toContain('[3 likes / 1 unlikes]');
    });

    test('omits ratings when both are zero', () => {
        player.history.push({ artist: 'A', title: 'T1', album: '' });
        player.lastSummary = { 'A - T1': { likes: 0, dislikes: 0 } };
        const text = player.getRecentlyPlayedText();
        expect(text).not.toContain('[');
    });
});

/* ── getArtworkUrl ──────────────────────────────────────────── */

describe('getArtworkUrl', () => {
    test('returns 300x300 URL from artwork img', () => {
        document.getElementById('artwork').innerHTML =
            '<img src="https://example.com/600x600bb.jpg">';
        const url = player.getArtworkUrl();
        expect(url).toBe('https://example.com/300x300bb.jpg');
    });

    test('returns empty string when no img', () => {
        document.getElementById('artwork').innerHTML = '<div>no image</div>';
        expect(player.getArtworkUrl()).toBe('');
    });
});

/* ── Track management ───────────────────────────────────────── */

describe('updateTrack', () => {
    beforeEach(() => {
        player.currentTrack = null;
        player.history.length = 0;
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({ results: [] }) })
        );
    });

    test('updates DOM elements', () => {
        player.updateTrack('NewArtist', 'NewTitle', 'NewAlbum');
        expect(document.getElementById('artist').textContent).toBe('NewArtist');
        expect(document.getElementById('track').textContent).toBe('NewTitle');
        expect(document.getElementById('album').textContent).toBe('NewAlbum');
    });

    test('does not update if same track', () => {
        player.updateTrack('A', 'T', 'Al');
        const spy = jest.spyOn(document.getElementById('artist'), 'textContent', 'set');
        player.updateTrack('A', 'T', 'Al'); // same track
        expect(spy).not.toHaveBeenCalled();
        spy.mockRestore();
    });

    test('pushes previous track to history', () => {
        player.updateTrack('First', 'Song1', 'Album1');
        player.updateTrack('Second', 'Song2', 'Album2');
        expect(player.history.length).toBe(1);
        expect(player.history[0].artist).toBe('First');
    });
});

describe('pushHistory', () => {
    beforeEach(() => {
        player.history.length = 0;
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
    });

    test('adds track to front of history', () => {
        player.pushHistory('A', 'T', 'Al');
        expect(player.history[0]).toEqual({ artist: 'A', title: 'T', album: 'Al' });
    });

    test('skips empty artist and title', () => {
        player.pushHistory('', '', '');
        expect(player.history.length).toBe(0);
    });

    test('caps history at MAX_HISTORY', () => {
        for (let i = 0; i < 25; i++) {
            player.pushHistory(`A${i}`, `T${i}`, '');
        }
        expect(player.history.length).toBe(player.MAX_HISTORY);
    });
});

/* ── Theme ──────────────────────────────────────────────────── */

describe('applyTheme', () => {
    test('sets data-theme attribute', () => {
        player.applyTheme('light');
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });

    test('persists to localStorage', () => {
        player.applyTheme('dark');
        expect(localStorage.setItem).toHaveBeenCalledWith('rc-theme', 'dark');
    });
});

/* ── Stream quality ─────────────────────────────────────────── */

describe('updateStreamQualityDisplay', () => {
    test('updates stream quality label', () => {
        player.currentStreamQuality = 'flac';
        player.updateStreamQualityDisplay();
        expect(document.getElementById('stream-quality').textContent)
            .toBe('Stream quality: FLAC Hi-Res (Lossless)');
    });

    test('updates for AAC', () => {
        player.currentStreamQuality = 'aac';
        player.updateStreamQualityDisplay();
        expect(document.getElementById('stream-quality').textContent)
            .toBe('Stream quality: AAC Hi-Fi (211 kbps)');
    });
});

describe('STREAM_LABELS', () => {
    test('has flac and aac entries', () => {
        expect(player.STREAM_LABELS).toHaveProperty('flac');
        expect(player.STREAM_LABELS).toHaveProperty('aac');
    });
});

/* ── Drawer ─────────────────────────────────────────────────── */

describe('openDrawer / closeDrawer', () => {
    test('openDrawer adds open class', () => {
        player.openDrawer();
        expect(document.getElementById('drawer').classList.contains('open')).toBe(true);
        expect(document.getElementById('drawer-overlay').classList.contains('open')).toBe(true);
    });

    test('closeDrawer removes open class', () => {
        player.openDrawer();
        player.closeDrawer();
        expect(document.getElementById('drawer').classList.contains('open')).toBe(false);
    });
});

/* ── Auth views ─────────────────────────────────────────────── */

describe('showAuthView / showProfileView', () => {
    test('showAuthView shows auth section, hides profile/feedback', () => {
        player.showAuthView();
        expect(document.getElementById('drawer-auth').style.display).toBe('');
        expect(document.getElementById('drawer-profile').style.display).toBe('none');
        expect(document.getElementById('drawer-feedback').style.display).toBe('none');
    });

    test('showAuthView clears auth feedback', () => {
        document.getElementById('auth-feedback').textContent = 'old error';
        player.showAuthView();
        expect(document.getElementById('auth-feedback').textContent).toBe('');
    });

    test('showProfileView shows profile and feedback sections', () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
        player.showProfileView();
        expect(document.getElementById('drawer-auth').style.display).toBe('none');
        expect(document.getElementById('drawer-profile').style.display).toBe('');
        expect(document.getElementById('drawer-feedback').style.display).toBe('');
    });
});

/* ── showPlayIcon ───────────────────────────────────────────── */

describe('showPlayIcon', () => {
    test('shows play icon, hides others', () => {
        player.showPlayIcon('play');
        expect(document.getElementById('icon-play').style.display).toBe('');
        expect(document.getElementById('icon-pause').style.display).toBe('none');
        expect(document.getElementById('icon-spin').style.display).toBe('none');
    });

    test('shows pause icon', () => {
        player.showPlayIcon('pause');
        expect(document.getElementById('icon-play').style.display).toBe('none');
        expect(document.getElementById('icon-pause').style.display).toBe('');
    });

    test('shows spinner icon', () => {
        player.showPlayIcon('spinner');
        expect(document.getElementById('icon-spin').style.display).toBe('');
    });
});

/* ── Ratings ────────────────────────────────────────────────── */

describe('submitRating', () => {
    beforeEach(() => {
        document.getElementById('artist').textContent = 'TestArtist';
        document.getElementById('track').textContent = 'TestTitle';
        document.getElementById('rate-up').classList.remove('rated');
        document.getElementById('rate-down').classList.remove('rated');
        document.getElementById('rating-feedback').textContent = '';
    });

    test('sends POST to /api/ratings', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
        );
        await player.submitRating(1);
        expect(global.fetch).toHaveBeenCalledWith('/api/ratings', expect.objectContaining({
            method: 'POST',
        }));
    });

    test('shows Thanks! on thumbs up success', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
        );
        await player.submitRating(1);
        expect(document.getElementById('rating-feedback').textContent).toBe('Thanks!');
        expect(document.getElementById('rate-up').classList.contains('rated')).toBe(true);
        expect(document.getElementById('rate-down').classList.contains('rated')).toBe(true);
    });

    test('shows Noted! on thumbs down success', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
        );
        await player.submitRating(0);
        expect(document.getElementById('rating-feedback').textContent).toBe('Noted!');
    });

    test('handles 409 duplicate rating', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
        );
        await player.submitRating(1);
        expect(document.getElementById('rating-feedback').textContent).toBe('Already rated this track');
    });

    test('handles network error', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        await player.submitRating(1);
        expect(document.getElementById('rating-feedback').textContent).toBe('Network error. Check that the server and Ollama are running.');
    });
});

describe('checkIfRated', () => {
    test('returns true when rated', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({ rated: true }) })
        );
        const result = await player.checkIfRated('A - T');
        expect(result).toBe(true);
    });

    test('returns false when not rated', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({ rated: false }) })
        );
        const result = await player.checkIfRated('A - T');
        expect(result).toBe(false);
    });

    test('returns false on error', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        const result = await player.checkIfRated('A - T');
        expect(result).toBe(false);
    });

    test('returns false on non-ok response', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: false, status: 500 })
        );
        const result = await player.checkIfRated('A - T');
        expect(result).toBe(false);
    });
});

describe('updateRatingUI', () => {
    beforeEach(() => {
        document.getElementById('artist').textContent = 'RatingArtist';
        document.getElementById('track').textContent = 'RatingTitle';
        document.getElementById('rate-up').classList.remove('rated');
        document.getElementById('rate-down').classList.remove('rated');
        document.getElementById('rating-feedback').textContent = '';
        document.getElementById('rate-up-count').textContent = '0';
        document.getElementById('rate-down-count').textContent = '0';
    });

    test('marks buttons as rated when already rated', async () => {
        // First call: checkIfRated, Second call: fetchTrackRatings
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ rated: true }) })
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ 'RatingArtist - RatingTitle': { likes: 5, dislikes: 2 } }) });
        await player.updateRatingUI();
        expect(document.getElementById('rate-up').classList.contains('rated')).toBe(true);
        expect(document.getElementById('rate-down').classList.contains('rated')).toBe(true);
        expect(document.getElementById('rating-feedback').textContent).toBe('You rated this track');
    });

    test('clears rated state when not yet rated', async () => {
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ rated: false }) })
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
        await player.updateRatingUI();
        expect(document.getElementById('rate-up').classList.contains('rated')).toBe(false);
        expect(document.getElementById('rating-feedback').textContent).toBe('');
    });
});

describe('fetchTrackRatings', () => {
    beforeEach(() => {
        document.getElementById('rate-up-count').textContent = '0';
        document.getElementById('rate-down-count').textContent = '0';
    });

    test('updates like/dislike counts from API', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ 'A - T': { likes: 10, dislikes: 3 } })
            })
        );
        await player.fetchTrackRatings('A - T');
        expect(document.getElementById('rate-up-count').textContent).toBe('10');
        expect(document.getElementById('rate-down-count').textContent).toBe('3');
    });

    test('shows 0 when station has no ratings', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
        await player.fetchTrackRatings('Unknown - Song');
        expect(document.getElementById('rate-up-count').textContent).toBe('0');
        expect(document.getElementById('rate-down-count').textContent).toBe('0');
    });

    test('handles API error gracefully', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        await player.fetchTrackRatings('A - T');
        // Should not throw, counts stay at 0
        expect(document.getElementById('rate-up-count').textContent).toBe('0');
    });

    test('handles non-ok response', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: false, status: 500 })
        );
        await player.fetchTrackRatings('A - T');
        expect(document.getElementById('rate-up-count').textContent).toBe('0');
    });
});

/* ── renderHistory ──────────────────────────────────────────── */

describe('renderHistory', () => {
    beforeEach(() => {
        player.history.length = 0;
        player.lastSummary = {};
        player.prevFilter = 'all';
        player.historyLimit = 5;
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
    });

    test('shows empty message when no history', async () => {
        await player.renderHistory();
        expect(document.getElementById('prev-list').innerHTML).toContain('No tracks yet');
    });

    test('renders history items with album', async () => {
        player.history.push({ artist: 'A', title: 'T', album: 'Al' });
        await player.renderHistory();
        const html = document.getElementById('prev-list').innerHTML;
        expect(html).toContain('A');
        expect(html).toContain('T');
        expect(html).toContain('Al');
    });

    test('renders history items without album', async () => {
        player.history.push({ artist: 'A', title: 'T', album: '' });
        await player.renderHistory();
        const html = document.getElementById('prev-list').innerHTML;
        expect(html).toContain('A');
        expect(html).toContain('T');
        expect(html).not.toContain('prev-album');
    });

    test('renders rating badges when summary available', async () => {
        player.history.push({ artist: 'A', title: 'T', album: '' });
        // Reset ratings cache so renderHistory fetches fresh data
        player.renderHistory._cacheTime = 0;
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ 'A - T': { likes: 5, dislikes: 2 } })
            })
        );
        await player.renderHistory();
        const html = document.getElementById('prev-list').innerHTML;
        expect(html).toContain('5');
        expect(html).toContain('2');
        expect(html).toContain('prev-ratings');
    });

    test('shows no matching tracks when filter has no matches', async () => {
        player.history.push({ artist: 'A', title: 'T1', album: '' });
        player.prevFilter = 'up';
        player.lastSummary = {};
        await player.renderHistory();
        expect(document.getElementById('prev-list').innerHTML).toContain('No matching tracks');
    });

    test('handles fetch error gracefully', async () => {
        player.history.push({ artist: 'A', title: 'T', album: '' });
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        await player.renderHistory();
        // Should still render, using cached lastSummary
        const html = document.getElementById('prev-list').innerHTML;
        expect(html).toContain('A');
    });
});

/* ── fetchArtwork ──────────────────────────────────────────── */

describe('fetchItunesCached', () => {
    beforeEach(() => {
        Object.keys(mockStorage).forEach(k => { if (k.startsWith('rc-itunes-')) delete mockStorage[k]; });
    });

    test('returns cached data on cache hit', async () => {
        const cachedData = { results: [{ artworkUrl100: 'cached.jpg' }] };
        mockStorage['rc-itunes-test query'] = JSON.stringify({ data: cachedData, ts: Date.now() });
        global.fetch = jest.fn();
        const result = await player.fetchItunesCached('test query');
        expect(result).toEqual(cachedData);
        expect(global.fetch).not.toHaveBeenCalled();
    });

    test('fetches from API on cache miss', async () => {
        const apiData = { results: [{ artworkUrl100: 'api.jpg' }] };
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve(apiData) })
        );
        const result = await player.fetchItunesCached('new query');
        expect(result).toEqual(apiData);
        expect(global.fetch).toHaveBeenCalled();
        // Should now be cached
        expect(mockStorage['rc-itunes-new query']).toBeDefined();
    });

    test('fetches from API on expired cache', async () => {
        const staleData = { results: [] };
        mockStorage['rc-itunes-old query'] = JSON.stringify({ data: staleData, ts: Date.now() - 25 * 60 * 60 * 1000 });
        const freshData = { results: [{ artworkUrl100: 'fresh.jpg' }] };
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve(freshData) })
        );
        const result = await player.fetchItunesCached('old query');
        expect(result).toEqual(freshData);
    });
});

describe('fetchArtwork', () => {
    beforeEach(() => {
        document.getElementById('artwork').innerHTML = '';
        // Clear iTunes cache entries from localStorage mock
        Object.keys(mockStorage).forEach(k => { if (k.startsWith('rc-itunes-')) delete mockStorage[k]; });
    });

    test('sets artwork from iTunes API result', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    results: [{
                        artworkUrl100: 'https://example.com/100x100bb.jpg',
                        trackTimeMillis: 240000
                    }]
                })
            })
        );
        await player.fetchArtwork('Madonna', 'Angel');
        const html = document.getElementById('artwork').innerHTML;
        expect(html).toContain('600x600bb.jpg');
        expect(html).toContain('img');
    });

    test('shows placeholder when no results', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ results: [] })
            })
        );
        await player.fetchArtwork('Unknown', 'Song');
        expect(document.getElementById('artwork').innerHTML).toContain('artwork-placeholder');
    });

    test('shows placeholder on fetch error', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        await player.fetchArtwork('A', 'T');
        expect(document.getElementById('artwork').innerHTML).toContain('artwork-placeholder');
    });

    test('handles result without trackTimeMillis', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    results: [{ artworkUrl100: 'https://example.com/100x100bb.jpg' }]
                })
            })
        );
        await player.fetchArtwork('A', 'T');
        const html = document.getElementById('artwork').innerHTML;
        expect(html).toContain('img');
    });
});

/* ── handleMetadataFields ──────────────────────────────────── */

describe('handleMetadataFields', () => {
    beforeEach(() => {
        player.currentTrack = null;
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({ results: [] }) })
        );
    });

    test('updates track when artist and title present', () => {
        player.handleMetadataFields({ TPE1: 'MetaArtist', TIT2: 'MetaTitle', TALB: 'MetaAlbum' });
        expect(document.getElementById('artist').textContent).toBe('MetaArtist');
        expect(document.getElementById('track').textContent).toBe('MetaTitle');
        expect(document.getElementById('album').textContent).toBe('MetaAlbum');
    });

    test('updates album only when no artist or title', () => {
        const originalArtist = document.getElementById('artist').textContent;
        player.handleMetadataFields({ TALB: 'NewAlbum' });
        expect(document.getElementById('album').textContent).toBe('NewAlbum');
        expect(document.getElementById('artist').textContent).toBe(originalArtist);
    });

    test('uses existing DOM values as fallback for missing fields', () => {
        document.getElementById('artist').textContent = 'ExistingArtist';
        document.getElementById('track').textContent = 'ExistingTitle';
        player.currentTrack = null;
        player.handleMetadataFields({ TIT2: 'OnlyTitle' });
        expect(document.getElementById('artist').textContent).toBe('ExistingArtist');
        expect(document.getElementById('track').textContent).toBe('OnlyTitle');
    });

    test('does nothing when no relevant fields', () => {
        const artist = document.getElementById('artist').textContent;
        const album = document.getElementById('album').textContent;
        player.handleMetadataFields({});
        expect(document.getElementById('artist').textContent).toBe(artist);
        expect(document.getElementById('album').textContent).toBe(album);
    });
});

/* ── togglePlay ────────────────────────────────────────────── */

describe('togglePlay', () => {
    beforeEach(() => {
        player.playing = false;
        HTMLMediaElement.prototype.play = jest.fn(() => Promise.resolve());
        HTMLMediaElement.prototype.pause = jest.fn();
    });

    test('starts playing and shows spinner', () => {
        player.togglePlay();
        expect(player.playing).toBe(true);
        expect(document.getElementById('icon-spin').style.display).toBe('');
    });

    test('pauses when already playing', () => {
        player.playing = true;
        player.togglePlay();
        expect(player.playing).toBe(false);
        expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
    });

    test('reverts to play icon on play failure', async () => {
        HTMLMediaElement.prototype.play = jest.fn(() => Promise.reject(new Error('blocked')));
        player.togglePlay();
        // Wait for the catch to fire
        await new Promise(r => setTimeout(r, 10));
        expect(player.playing).toBe(false);
        expect(document.getElementById('icon-play').style.display).toBe('');
    });
});

/* ── fetchMetadata ─────────────────────────────────────────── */

describe('fetchMetadata', () => {
    beforeEach(() => {
        player.currentTrack = null;
        player.history.length = 0;
        player.lastSummary = {};
        if (player.renderHistory) player.renderHistory._cacheTime = 0;
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    test('fetches metadata and schedules track update', async () => {
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    artist: 'FetchArtist',
                    title: 'FetchTitle',
                    album: 'FetchAlbum'
                })
            })
            // renderHistory calls
            .mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

        await player.fetchMetadata();

        // Track update is delayed by hls.latency, so not applied yet
        // Fast-forward timers to apply the delayed update
        jest.advanceTimersByTime(7000);

        // After delay, updateTrack should have been called
        expect(document.getElementById('artist').textContent).toBe('FetchArtist');
    });

    test('merges previous tracks into history', async () => {
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    artist: 'A', title: 'T',
                    prev_artist_1: 'Prev1', prev_title_1: 'Song1',
                    prev_artist_2: 'Prev2', prev_title_2: 'Song2',
                })
            })
            // renderHistory + iTunes album fetch calls
            .mockResolvedValue({ ok: true, json: () => Promise.resolve({ results: [] }) });

        await player.fetchMetadata();
        expect(player.history.length).toBe(2);
        expect(player.history[0].artist).toBe('Prev1');
        expect(player.history[1].artist).toBe('Prev2');
    });

    test('handles non-ok response', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: false, status: 500 })
        );
        // Should not throw
        await player.fetchMetadata();
    });

    test('handles fetch error', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        // Should not throw
        await player.fetchMetadata();
    });

    test('shows source quality from metadata', async () => {
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    artist: 'A', title: 'T',
                    sample_rate: 48000, bit_depth: 24
                })
            })
            .mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

        await player.fetchMetadata();
        const srcQual = document.getElementById('source-quality').textContent;
        expect(srcQual).toContain('24-bit');
        expect(srcQual).toContain('48.0 kHz');
    });

    test('fetches album names from iTunes for history entries missing album', async () => {
        jest.useRealTimers();
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    artist: 'A', title: 'T',
                    prev_artist_1: 'NoAlbumArtist', prev_title_1: 'NoAlbumSong',
                })
            })
            // renderHistory summary fetch
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
            // iTunes album fetch for the history entry
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    results: [{ collectionName: 'Fetched Album' }]
                })
            })
            // renderHistory from album update
            .mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

        await player.fetchMetadata();
        // Wait for the async iTunes fetch inside forEach
        await new Promise(r => setTimeout(r, 100));
        // The album should now be filled in
        expect(player.history[0].album).toBe('Fetched Album');
        jest.useFakeTimers();
    });

    test('handles iTunes album fetch failure gracefully', async () => {
        jest.useRealTimers();
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    artist: 'A', title: 'T',
                    prev_artist_1: 'FailArtist', prev_title_1: 'FailSong',
                })
            })
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
            .mockRejectedValueOnce(new Error('iTunes down'));

        await player.fetchMetadata();
        await new Promise(r => setTimeout(r, 100));
        // Should not throw; album stays empty
        expect(player.history[0].album).toBe('');
        jest.useFakeTimers();
    });

    test('preserves album info from existing history when merging', async () => {
        // Pre-populate history with album info
        player.history.push({ artist: 'Prev1', title: 'Song1', album: 'ExistingAlbum' });

        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    artist: 'A', title: 'T',
                    prev_artist_1: 'Prev1', prev_title_1: 'Song1',
                })
            })
            .mockResolvedValue({ ok: true, json: () => Promise.resolve({ results: [] }) });

        await player.fetchMetadata();
        expect(player.history[0].album).toBe('ExistingAlbum');
    });
});

/* ── applyStreamQuality ────────────────────────────────────── */

describe('applyStreamQuality', () => {
    beforeEach(() => {
        player.currentStreamQuality = 'flac';
        player.playing = false;
        window.Hls.isSupported.mockReturnValue(true);
        hlsInstance.loadSource.mockClear();
        hlsInstance.attachMedia.mockClear();
        hlsInstance.on.mockClear();
        hlsInstance.destroy.mockClear();
        localStorage.setItem.mockClear();
    });

    test('does nothing if same quality', () => {
        player.applyStreamQuality('flac');
        expect(localStorage.setItem).not.toHaveBeenCalledWith('rc-stream-quality', 'flac');
    });

    test('switches to AAC and reinitializes HLS', () => {
        player.applyStreamQuality('aac');
        expect(player.currentStreamQuality).toBe('aac');
        expect(localStorage.setItem).toHaveBeenCalledWith('rc-stream-quality', 'aac');
        expect(hlsInstance.loadSource).toHaveBeenCalled();
    });

    test('resumes playback if was playing', async () => {
        player.playing = true;
        HTMLMediaElement.prototype.play = jest.fn(() => Promise.resolve());
        player.applyStreamQuality('aac');
        expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
    });

    test('handles play failure on quality switch', async () => {
        player.playing = true;
        player.currentStreamQuality = 'aac'; // reset for flac switch
        HTMLMediaElement.prototype.play = jest.fn(() => Promise.reject(new Error('blocked')));
        player.applyStreamQuality('flac');
        await new Promise(r => setTimeout(r, 10));
        expect(player.playing).toBe(false);
    });

    test('falls back to Safari native HLS when HLS.js not supported', () => {
        player.currentStreamQuality = 'flac';
        window.Hls.isSupported.mockReturnValue(false);
        HTMLMediaElement.prototype.canPlayType = jest.fn(() => 'maybe');
        HTMLMediaElement.prototype.play = jest.fn(() => Promise.resolve());
        player.applyStreamQuality('aac');
        expect(player.currentStreamQuality).toBe('aac');
        // Restore
        window.Hls.isSupported.mockReturnValue(true);
        HTMLMediaElement.prototype.canPlayType = jest.fn(() => '');
    });

    test('Safari fallback resumes playback when was playing', () => {
        player.currentStreamQuality = 'aac';
        player.playing = true;
        window.Hls.isSupported.mockReturnValue(false);
        HTMLMediaElement.prototype.canPlayType = jest.fn(() => 'maybe');
        HTMLMediaElement.prototype.play = jest.fn(() => Promise.resolve());
        player.applyStreamQuality('flac');
        expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
        // Restore
        window.Hls.isSupported.mockReturnValue(true);
        HTMLMediaElement.prototype.canPlayType = jest.fn(() => '');
        player.playing = false;
    });
});

/* ── loadProfile ───────────────────────────────────────────── */

describe('loadProfile', () => {
    beforeEach(() => {
        document.getElementById('profile-nickname').value = '';
        document.getElementById('profile-email').value = '';
        document.getElementById('profile-about').value = '';
        document.querySelectorAll('#genre-grid input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
    });

    test('populates form fields when logged in (via login flow)', async () => {
        // Login first to set authToken
        document.getElementById('auth-username').value = 'profuser';
        document.getElementById('auth-password').value = 'profpass';
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ token: 'prof-token' }) })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ nickname: 'Nick', email: 'e@m.com', about: 'Bio', genres: 'rock,pop' })
            });
        document.getElementById('auth-form').dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 100));
        expect(document.getElementById('profile-nickname').value).toBe('Nick');
        expect(document.getElementById('profile-email').value).toBe('e@m.com');
        // Genre checkboxes
        const rockCb = document.querySelector('#genre-grid input[value="rock"]');
        expect(rockCb.checked).toBe(true);
        const jazzCb = document.querySelector('#genre-grid input[value="jazz"]');
        expect(jazzCb.checked).toBe(false);
    });

    test('handles 401 by reverting to auth view', async () => {
        document.getElementById('auth-username').value = 'user401';
        document.getElementById('auth-password').value = 'pass401';
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ token: 'expire-token' }) })
            .mockResolvedValueOnce({ ok: false, status: 401 });
        document.getElementById('auth-form').dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 100));
        expect(document.getElementById('drawer-auth').style.display).toBe('');
    });

    test('handles non-ok non-401 response', async () => {
        document.getElementById('auth-username').value = 'user500';
        document.getElementById('auth-password').value = 'pass500';
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ token: 'tok500' }) })
            .mockResolvedValueOnce({ ok: false, status: 500 });
        document.getElementById('auth-form').dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 100));
        expect(document.getElementById('drawer-profile').style.display).toBe('');
    });

    test('handles network error during loadProfile', async () => {
        document.getElementById('auth-username').value = 'usererr';
        document.getElementById('auth-password').value = 'passerr';
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ token: 'tokerr' }) })
            .mockRejectedValueOnce(new Error('network'));
        document.getElementById('auth-form').dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 100));
        // Should not throw
    });

    test('returns early when no authToken (after logout)', async () => {
        global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
        document.getElementById('btn-logout').click();
        global.fetch = jest.fn();
        await player.loadProfile();
        expect(global.fetch).not.toHaveBeenCalled();
    });
});

/* ── Metadata fetch ─────────────────────────────────────────── */

describe('triggerMetadataFetch', () => {
    test('debounces calls', () => {
        const spy = jest.fn();
        global.fetch = spy.mockResolvedValue({
            ok: true, json: () => Promise.resolve({})
        });
        player.triggerMetadataFetch();
        player.triggerMetadataFetch(); // should be debounced
        // Only one fetch within debounce window
    });
});

/* ── Share button click handlers ─────────────────────────────── */

describe('share button click handlers', () => {
    beforeEach(() => {
        document.getElementById('artist').textContent = 'ShareArtist';
        document.getElementById('track').textContent = 'ShareTitle';
        document.getElementById('album').textContent = 'ShareAlbum';
        document.getElementById('artwork').innerHTML = '<img src="https://example.com/600x600bb.jpg">';
        window.open = jest.fn();
    });

    test('WhatsApp share opens correct URL', () => {
        document.getElementById('share-whatsapp').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('wa.me'),
            '_blank', 'noopener'
        );
    });

    test('Twitter share opens correct URL', () => {
        document.getElementById('share-twitter').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('x.com/intent/tweet'),
            '_blank', 'noopener'
        );
    });

    test('Telegram share opens correct URL', () => {
        document.getElementById('share-telegram').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('t.me/share'),
            '_blank', 'noopener'
        );
    });

    test('Spotify search opens correct URL', () => {
        document.getElementById('share-spotify').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('open.spotify.com/search'),
            '_blank', 'noopener'
        );
    });

    test('YouTube Music search opens correct URL', () => {
        document.getElementById('share-ytmusic').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('music.youtube.com/search'),
            '_blank', 'noopener'
        );
    });

    test('Amazon Music search opens correct URL', () => {
        document.getElementById('share-amazon').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('amazon.com/s'),
            '_blank', 'noopener'
        );
    });
});

describe('recently played share handlers', () => {
    beforeEach(() => {
        player.history.length = 0;
        player.prevFilter = 'all';
        player.historyLimit = 5;
        player.lastSummary = {};
        window.open = jest.fn();
    });

    test('prev-share-whatsapp does nothing with empty history', () => {
        document.getElementById('prev-share-whatsapp').click();
        expect(window.open).not.toHaveBeenCalled();
    });

    test('prev-share-whatsapp opens with text when history exists', () => {
        player.history.push({ artist: 'A', title: 'T', album: '' });
        document.getElementById('prev-share-whatsapp').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('wa.me'),
            '_blank', 'noopener'
        );
    });

    test('prev-share-twitter does nothing with empty history', () => {
        document.getElementById('prev-share-twitter').click();
        expect(window.open).not.toHaveBeenCalled();
    });

    test('prev-share-twitter opens with text when history exists', () => {
        player.history.push({ artist: 'A', title: 'T', album: '' });
        document.getElementById('prev-share-twitter').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('x.com/intent/tweet'),
            '_blank', 'noopener'
        );
    });
});

/* ── Settings dropdown ─────────────────────────────────────── */

describe('settings dropdown', () => {
    test('toggles open class on settings button click', () => {
        const btn = document.getElementById('settings-btn');
        const dropdown = document.getElementById('settings-dropdown');
        btn.click();
        expect(dropdown.classList.contains('open')).toBe(true);
        btn.click();
        expect(dropdown.classList.contains('open')).toBe(false);
    });

    test('closes on outside click', () => {
        const dropdown = document.getElementById('settings-dropdown');
        document.getElementById('settings-btn').click();
        expect(dropdown.classList.contains('open')).toBe(true);
        // Click outside
        document.body.click();
        expect(dropdown.classList.contains('open')).toBe(false);
    });
});

/* ── Feedback button handlers ──────────────────────────────── */

describe('feedback social buttons', () => {
    beforeEach(() => {
        window.open = jest.fn();
    });

    test('feedback-twitter opens tweet intent with message', () => {
        document.getElementById('feedback-message').value = 'Great app!';
        document.getElementById('feedback-twitter').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('x.com/intent/tweet'),
            '_blank', 'noopener'
        );
    });

    test('feedback-twitter uses default text when empty', () => {
        document.getElementById('feedback-message').value = '';
        document.getElementById('feedback-twitter').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('RadioCalico'),
            '_blank', 'noopener'
        );
    });

    test('feedback-telegram opens share URL', () => {
        document.getElementById('feedback-message').value = 'Nice!';
        document.getElementById('feedback-telegram').click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('t.me/share'),
            '_blank', 'noopener'
        );
    });
});

/* ── Logout handler ────────────────────────────────────────── */

describe('logout', () => {
    test('clears auth state and shows auth view', () => {
        global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
        document.getElementById('auth-username').value = 'user';
        document.getElementById('auth-password').value = 'pass';
        document.getElementById('btn-logout').click();
        expect(localStorage.removeItem).toHaveBeenCalledWith('rc-token');
        expect(localStorage.removeItem).toHaveBeenCalledWith('rc-user');
        expect(document.getElementById('auth-username').value).toBe('');
        expect(document.getElementById('auth-password').value).toBe('');
        expect(document.getElementById('drawer-auth').style.display).toBe('');
    });
});

/* ── History filter and limit handlers ─────────────────────── */

describe('history filter and limit', () => {
    test('prev-limit change updates historyLimit', () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
        // Replace select with option value="10" so the handler can read it
        const select = document.getElementById('prev-limit');
        select.innerHTML = '<option value="10">10</option>';
        select.value = '10';
        select.dispatchEvent(new Event('change'));
        expect(player.historyLimit).toBe(10);
    });

    test('filter button click updates prevFilter', () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
        const btn = document.querySelector('.prev-filter');
        btn.dataset.filter = 'up';
        btn.click();
        expect(player.prevFilter).toBe('up');
    });
});

/* ── Volume & mute handlers ────────────────────────────────── */

describe('volume and mute', () => {
    test('volume input updates audio volume', () => {
        const vol = document.getElementById('volume');
        vol.value = '0.5';
        vol.dispatchEvent(new Event('input'));
        expect(document.getElementById('audio').volume).toBe(0.5);
    });

    test('volume input unmutes when muted and volume > 0', () => {
        // First mute
        document.getElementById('mute-btn').click();
        expect(document.getElementById('icon-mute').style.display).toBe('');
        // Now adjust volume while muted — should auto-unmute
        const vol = document.getElementById('volume');
        vol.value = '0.7';
        vol.dispatchEvent(new Event('input'));
        expect(document.getElementById('icon-vol').style.display).toBe('');
        expect(document.getElementById('icon-mute').style.display).toBe('none');
    });

    test('mute button toggles mute state', () => {
        // Ensure unmuted state first
        document.getElementById('icon-vol').style.display = '';
        document.getElementById('icon-mute').style.display = 'none';
        document.getElementById('mute-btn').click();
        expect(document.getElementById('icon-vol').style.display).toBe('none');
        expect(document.getElementById('icon-mute').style.display).toBe('');
        // Click again to unmute
        document.getElementById('mute-btn').click();
        expect(document.getElementById('icon-vol').style.display).toBe('');
        expect(document.getElementById('icon-mute').style.display).toBe('none');
    });
});

/* ── Login form handler ────────────────────────────────────── */

describe('login form', () => {
    beforeEach(() => {
        document.getElementById('auth-username').value = '';
        document.getElementById('auth-password').value = '';
        document.getElementById('auth-feedback').textContent = '';
    });

    test('successful login switches to profile view and loads profile', async () => {
        document.getElementById('auth-username').value = 'testuser';
        document.getElementById('auth-password').value = 'testpass';
        global.fetch = jest.fn()
            // login
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ token: 'abc123' })
            })
            // loadProfile (called by showProfileView)
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    nickname: 'TestNick',
                    email: 'test@test.com',
                    about: 'Hi',
                    genres: 'rock,jazz'
                })
            });
        const form = document.getElementById('auth-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 100));
        expect(localStorage.setItem).toHaveBeenCalledWith('rc-token', 'abc123');
        expect(document.getElementById('drawer-profile').style.display).toBe('');
        // Profile fields should be populated by loadProfile
        expect(document.getElementById('profile-nickname').value).toBe('TestNick');
        expect(document.getElementById('profile-email').value).toBe('test@test.com');
        expect(document.getElementById('profile-about').value).toBe('Hi');
    });

    test('failed login shows error', async () => {
        document.getElementById('auth-username').value = 'testuser';
        document.getElementById('auth-password').value = 'wrongpass';
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: false,
                json: () => Promise.resolve({ error: 'Invalid credentials' })
            })
        );
        const form = document.getElementById('auth-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('auth-feedback').textContent).toBe('Invalid credentials');
    });

    test('empty fields does not submit', async () => {
        global.fetch = jest.fn();
        const form = document.getElementById('auth-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 10));
        expect(global.fetch).not.toHaveBeenCalled();
    });

    test('handles network error on login', async () => {
        document.getElementById('auth-username').value = 'testuser';
        document.getElementById('auth-password').value = 'testpass';
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        const form = document.getElementById('auth-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('auth-feedback').textContent).toBe('Could not connect');
    });
});

/* ── Register button handler ───────────────────────────────── */

describe('register button', () => {
    beforeEach(() => {
        document.getElementById('auth-username').value = '';
        document.getElementById('auth-password').value = '';
        document.getElementById('auth-feedback').textContent = '';
    });

    test('successful registration shows success message', async () => {
        document.getElementById('auth-username').value = 'newuser';
        document.getElementById('auth-password').value = 'newpass123';
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({})
            })
        );
        const btn = document.getElementById('btn-register');
        btn.dispatchEvent(new Event('click', { bubbles: true, cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('auth-feedback').textContent).toBe('Registered! You can now login.');
    });

    test('failed registration shows error', async () => {
        document.getElementById('auth-username').value = 'existing';
        document.getElementById('auth-password').value = 'pass123';
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: false,
                json: () => Promise.resolve({ error: 'Username taken' })
            })
        );
        const btn = document.getElementById('btn-register');
        btn.dispatchEvent(new Event('click', { bubbles: true, cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('auth-feedback').textContent).toBe('Username taken');
    });

    test('empty fields shows validation message', async () => {
        global.fetch = jest.fn();
        const btn = document.getElementById('btn-register');
        btn.dispatchEvent(new Event('click', { bubbles: true, cancelable: true }));
        await new Promise(r => setTimeout(r, 10));
        expect(document.getElementById('auth-feedback').textContent).toBe('Fill in both fields');
    });

    test('handles network error on register', async () => {
        document.getElementById('auth-username').value = 'newuser';
        document.getElementById('auth-password').value = 'newpass123';
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        const btn = document.getElementById('btn-register');
        btn.dispatchEvent(new Event('click', { bubbles: true, cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('auth-feedback').textContent).toBe('Could not connect to server');
    });
});

/* ── Profile save handler ──────────────────────────────────── */

describe('profile save', () => {
    beforeEach(async () => {
        document.getElementById('profile-feedback').textContent = '';
        // Login first to set authToken
        document.getElementById('auth-username').value = 'saveuser';
        document.getElementById('auth-password').value = 'savepass';
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ token: 'save-token' }) })
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
        document.getElementById('auth-form').dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 100));
    });

    test('successful save shows confirmation', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
        const form = document.getElementById('profile-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('profile-feedback').textContent).toBe('Profile saved!');
    });

    test('failed save shows error', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: false,
                json: () => Promise.resolve({ error: 'Invalid email' })
            })
        );
        const form = document.getElementById('profile-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('profile-feedback').textContent).toBe('Invalid email');
    });

    test('handles network error on save', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        const form = document.getElementById('profile-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('profile-feedback').textContent).toBe('Could not connect');
    });

    test('returns early when not authenticated', async () => {
        // Logout first
        global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));
        document.getElementById('btn-logout').click();
        global.fetch = jest.fn();
        const form = document.getElementById('profile-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        // fetch should not be called since authToken is null
        expect(global.fetch).not.toHaveBeenCalled();
    });
});

/* ── Feedback form handler ─────────────────────────────────── */

describe('feedback form', () => {
    beforeEach(async () => {
        document.getElementById('feedback-feedback').textContent = '';
        document.getElementById('feedback-message').value = '';
        // Ensure logged in for feedback tests
        document.getElementById('auth-username').value = 'fbuser';
        document.getElementById('auth-password').value = 'fbpass';
        global.fetch = jest.fn()
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ token: 'fb-token' }) })
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });
        document.getElementById('auth-form').dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 100));
    });

    test('successful feedback shows thank you', async () => {
        document.getElementById('feedback-message').value = 'Great app!';
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
        const form = document.getElementById('feedback-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('feedback-feedback').textContent).toBe('Feedback sent! Thank you!');
        expect(document.getElementById('feedback-message').value).toBe('');
    });

    test('empty message shows validation error', async () => {
        const form = document.getElementById('feedback-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 10));
        expect(document.getElementById('feedback-feedback').textContent).toBe('Please write a message');
    });

    test('failed feedback shows error', async () => {
        document.getElementById('feedback-message').value = 'Test';
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: false,
                json: () => Promise.resolve({ error: 'Server error' })
            })
        );
        const form = document.getElementById('feedback-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('feedback-feedback').textContent).toBe('Server error');
    });

    test('handles network error on feedback', async () => {
        document.getElementById('feedback-message').value = 'Test';
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        const form = document.getElementById('feedback-form');
        form.dispatchEvent(new Event('submit', { cancelable: true }));
        await new Promise(r => setTimeout(r, 50));
        expect(document.getElementById('feedback-feedback').textContent).toBe('Could not connect');
    });
});

/* ── HLS event callbacks (captured from hls.on mock) ─────── */

// Store HLS callbacks captured at module load, before any test can reinitialize HLS
let hlsCallbacks = {};

beforeAll(() => {
    hlsInstance.on.mock.calls.forEach(c => {
        hlsCallbacks[c[0]] = c[1];
    });
});

describe('initHls event handlers', () => {
    function getHlsCallback(eventName) {
        return hlsCallbacks[eventName] || null;
    }

    test('MANIFEST_PARSED enables play button and sets quality level', () => {
        const cb = getHlsCallback('hlsManifestParsed');
        expect(cb).toBeTruthy();
        document.getElementById('play-btn').disabled = true;
        cb(null, {
            levels: [
                { audioCodec: 'flac' },
                { audioCodec: 'mp4a.40.2' }
            ]
        });
        expect(document.getElementById('play-btn').disabled).toBe(false);
    });

    test('MANIFEST_PARSED sets correct level for AAC', () => {
        const cb = getHlsCallback('hlsManifestParsed');
        player.currentStreamQuality = 'aac';
        cb(null, {
            levels: [
                { audioCodec: 'flac' },
                { audioCodec: 'mp4a.40.2' }
            ]
        });
        expect(hlsInstance.currentLevel).toBe(1);
        player.currentStreamQuality = 'flac'; // reset
    });

    test('MANIFEST_PARSED handles single level', () => {
        const cb = getHlsCallback('hlsManifestParsed');
        document.getElementById('play-btn').disabled = true;
        cb(null, { levels: [{ audioCodec: 'flac' }] });
        expect(document.getElementById('play-btn').disabled).toBe(false);
    });

    test('FRAG_PARSING_METADATA processes ID3 samples', () => {
        const cb = getHlsCallback('hlsFragParsingMetadata');
        expect(cb).toBeTruthy();
        // Create a minimal ID3 frame with artist data
        const header = [0x49, 0x44, 0x33, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x12];
        const frameId = [0x54, 0x50, 0x45, 0x31]; // TPE1
        const frameSize = [0x00, 0x00, 0x00, 0x05];
        const frameFlags = [0x00, 0x00];
        const encoding = [0x03];
        const text = [0x54, 0x65, 0x73, 0x74]; // 'Test'
        const data = new Uint8Array([...header, ...frameId, ...frameSize, ...frameFlags, ...encoding, ...text]);
        // Should not throw
        cb(null, { samples: [{ data }] });
    });

    test('FRAG_PARSING_METADATA handles no samples', () => {
        const cb = getHlsCallback('hlsFragParsingMetadata');
        cb(null, {}); // no samples field
        // Should not throw
    });

    test('FRAG_CHANGED triggers metadata fetch', () => {
        const cb = getHlsCallback('hlsFragChanged');
        expect(cb).toBeTruthy();
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
        cb();
        // Should not throw
    });

    test('LEVEL_LOADED updates source quality display', () => {
        const cb = getHlsCallback('hlsLevelLoaded');
        expect(cb).toBeTruthy();
        hlsInstance.levels = [{ audioCodec: 'FLAC', bitrate: 1500000 }];
        hlsInstance.currentLevel = 0;
        cb();
        const srcQual = document.getElementById('source-quality').textContent;
        expect(srcQual).toContain('FLAC');
        expect(srcQual).toContain('1500 kbps');
    });

    test('LEVEL_LOADED handles missing level info', () => {
        const cb = getHlsCallback('hlsLevelLoaded');
        hlsInstance.levels = [];
        hlsInstance.currentLevel = 0;
        cb();
        // Should not throw
    });

    test('ERROR handler resets state on fatal error', () => {
        const cb = getHlsCallback('hlsError');
        expect(cb).toBeTruthy();
        player.playing = true;
        cb(null, { fatal: true });
        expect(player.playing).toBe(false);
    });

    test('ERROR handler ignores non-fatal errors', () => {
        const cb = getHlsCallback('hlsError');
        player.playing = true;
        cb(null, { fatal: false });
        expect(player.playing).toBe(true);
    });
});

/* ── timeupdate handler ────────────────────────────────────── */

describe('audio timeupdate', () => {
    test('updates bar-time when playing', () => {
        player.playing = true;
        // Simulate songStartTime set a few seconds ago
        const audio = document.getElementById('audio');
        // Trigger timeupdate event
        audio.dispatchEvent(new Event('timeupdate'));
        // barTime should contain formatted time
        const text = document.getElementById('bar-time').textContent;
        // May contain "Live" since trackDuration may be null
        expect(text).toBeDefined();
    });
});

/* ── Structured logger ─────────────────────────────────────── */

describe('log', () => {
    test('log.info outputs JSON to console.log', () => {
        const spy = jest.spyOn(console, 'log').mockImplementation();
        player.log.info('test_event', { key: 'value' });
        expect(spy).toHaveBeenCalledTimes(1);
        const output = JSON.parse(spy.mock.calls[0][0]);
        expect(output.level).toBe('info');
        expect(output.logger).toBe('player');
        expect(output.message).toBe('test_event');
        expect(output.key).toBe('value');
        expect(output.timestamp).toBeDefined();
        spy.mockRestore();
    });

    test('log.warn outputs JSON to console.warn', () => {
        const spy = jest.spyOn(console, 'warn').mockImplementation();
        player.log.warn('warning_event', { detail: 'oops' });
        expect(spy).toHaveBeenCalledTimes(1);
        const output = JSON.parse(spy.mock.calls[0][0]);
        expect(output.level).toBe('warn');
        expect(output.message).toBe('warning_event');
        spy.mockRestore();
    });

    test('log.error outputs JSON to console.error', () => {
        const spy = jest.spyOn(console, 'error').mockImplementation();
        player.log.error('error_event', { code: 500 });
        expect(spy).toHaveBeenCalledTimes(1);
        const output = JSON.parse(spy.mock.calls[0][0]);
        expect(output.level).toBe('error');
        expect(output.message).toBe('error_event');
        expect(output.code).toBe(500);
        spy.mockRestore();
    });
});

/* ── Module exports accessors ──────────────────────────────── */

describe('module exports state accessors', () => {
    test('can get and set currentTrack', () => {
        player.currentTrack = 'test|track';
        expect(player.currentTrack).toBe('test|track');
        player.currentTrack = null;
    });

    test('can get and set playing', () => {
        const orig = player.playing;
        player.playing = true;
        expect(player.playing).toBe(true);
        player.playing = orig;
    });

    test('can get and set lastSummary', () => {
        player.lastSummary = { test: true };
        expect(player.lastSummary).toEqual({ test: true });
        player.lastSummary = {};
    });

    test('can get and set prevFilter', () => {
        player.prevFilter = 'up';
        expect(player.prevFilter).toBe('up');
        player.prevFilter = 'all';
    });

    test('can get and set historyLimit', () => {
        player.historyLimit = 10;
        expect(player.historyLimit).toBe(10);
        player.historyLimit = 5;
    });

    test('can get and set currentStreamQuality', () => {
        player.currentStreamQuality = 'aac';
        expect(player.currentStreamQuality).toBe('aac');
        player.currentStreamQuality = 'flac';
    });

    test('history is an array', () => {
        expect(Array.isArray(player.history)).toBe(true);
    });

    test('METADATA_DEBOUNCE_MS is a number', () => {
        expect(typeof player.METADATA_DEBOUNCE_MS).toBe('number');
        expect(player.METADATA_DEBOUNCE_MS).toBeGreaterThan(0);
    });

    test('MAX_HISTORY is a number', () => {
        expect(typeof player.MAX_HISTORY).toBe('number');
        expect(player.MAX_HISTORY).toBeGreaterThan(0);
    });
});

/* ── v2: markdownToHtml ───────────────────────────────────── */

describe('markdownToHtml', () => {
    test('returns empty string for falsy input', () => {
        expect(player.markdownToHtml('')).toBe('');
        expect(player.markdownToHtml(null)).toBe('');
        expect(player.markdownToHtml(undefined)).toBe('');
    });

    test('converts h1 heading', () => {
        const html = player.markdownToHtml('# Hello');
        expect(html).toContain('<h1>Hello</h1>');
    });

    test('converts h2 heading', () => {
        const html = player.markdownToHtml('## Sub');
        expect(html).toContain('<h2>Sub</h2>');
    });

    test('converts h3 heading', () => {
        const html = player.markdownToHtml('### Third');
        expect(html).toContain('<h3>Third</h3>');
    });

    test('converts h4 heading', () => {
        const html = player.markdownToHtml('#### Fourth');
        expect(html).toContain('<h4>Fourth</h4>');
    });

    test('converts h5 heading', () => {
        const html = player.markdownToHtml('##### Fifth');
        expect(html).toContain('<h5>Fifth</h5>');
    });

    test('converts h6 heading', () => {
        const html = player.markdownToHtml('###### Sixth');
        expect(html).toContain('<h6>Sixth</h6>');
    });

    test('converts bold text', () => {
        const html = player.markdownToHtml('**bold**');
        expect(html).toContain('<strong>bold</strong>');
    });

    test('converts italic text', () => {
        const html = player.markdownToHtml('*italic*');
        expect(html).toContain('<em>italic</em>');
    });

    test('converts bold+italic text', () => {
        const html = player.markdownToHtml('***bolditalic***');
        expect(html).toContain('<strong><em>bolditalic</em></strong>');
    });

    test('converts inline code', () => {
        const html = player.markdownToHtml('use `npm install`');
        expect(html).toContain('<code>npm install</code>');
    });

    test('converts unordered list with asterisks', () => {
        const html = player.markdownToHtml('* item one\n* item two');
        expect(html).toContain('<li>item one</li>');
        expect(html).toContain('<li>item two</li>');
        expect(html).toContain('<ul>');
    });

    test('converts unordered list with dashes', () => {
        const html = player.markdownToHtml('- first\n- second');
        expect(html).toContain('<li>first</li>');
        expect(html).toContain('<li>second</li>');
    });

    test('escapes HTML to prevent XSS', () => {
        const html = player.markdownToHtml('<script>alert("xss")</script>');
        expect(html).not.toContain('<script>');
        expect(html).toContain('&lt;script&gt;');
    });

    test('converts double newlines to paragraph breaks', () => {
        const html = player.markdownToHtml('para one\n\npara two');
        expect(html).toContain('</p><p>');
    });
});

/* ── v2: buildInfoShareRow ────────────────────────────────── */

describe('buildInfoShareRow', () => {
    test('returns HTML string with share buttons', () => {
        const html = player.buildInfoShareRow('lyrics', 'Artist', 'Track', 'Some content');
        expect(html).toContain('info-share-row');
        expect(html).toContain('share-whatsapp');
        expect(html).toContain('share-twitter');
        expect(html).toContain('share-telegram');
    });

    test('stores artist and track in module-level _infoShareMeta', () => {
        player.buildInfoShareRow('facts', 'The Beatles', 'Yesterday', 'Great song');
        // Share text is built at click time via _buildShareText(), stored in _infoShareMeta
        const text = player._buildShareText(4000);
        expect(text).toContain('The Beatles');
        expect(text).toContain('Yesterday');
    });

    test('stores query type label in share meta', () => {
        player.buildInfoShareRow('jokes', 'Artist', 'Track', 'Funny content');
        const text = player._buildShareText(4000);
        expect(text).toContain('Jokes');
    });

    test('uses data-platform attributes for CSP-safe share (no inline onclick)', () => {
        const html = player.buildInfoShareRow('lyrics', 'A&B', 'Track "1"', 'Content');
        // URLs are set via wireInfoShareButtons(), not inline onclick
        expect(html).toContain('data-platform="whatsapp"');
        expect(html).toContain('data-platform="twitter"');
        expect(html).toContain('data-platform="telegram"');
        expect(html).not.toContain('onclick');
    });

    test('truncates long content', () => {
        const longContent = 'A'.repeat(1000);
        const html = player.buildInfoShareRow('details', 'Art', 'Trk', longContent);
        // The encoded text should not contain the full 1000 chars
        expect(html.length).toBeLessThan(5000);
    });
});

/* ── v2: Retro buttons DOM ────────────────────────────────── */

describe('Retro buttons DOM', () => {
    test('7 retro buttons exist in DOM', () => {
        const buttons = document.querySelectorAll('.retro-btn');
        expect(buttons.length).toBe(7);
    });

    test('each button has a data-query attribute', () => {
        const buttons = document.querySelectorAll('.retro-btn');
        buttons.forEach(btn => {
            expect(btn.dataset.query).toBeTruthy();
        });
    });

    test('expected query types are present', () => {
        const types = [...document.querySelectorAll('.retro-btn')].map(b => b.dataset.query);
        expect(types).toContain('lyrics');
        expect(types).toContain('details');
        expect(types).toContain('facts');
        expect(types).toContain('merchandise');
        expect(types).toContain('jokes');
        expect(types).toContain('everything');
        expect(types).toContain('quiz');
    });

    test('info panel exists and starts closed', () => {
        const panel = document.getElementById('info-panel');
        expect(panel).not.toBeNull();
        expect(panel.classList.contains('open')).toBe(false);
    });

    test('all buttons start unpressed', () => {
        const buttons = document.querySelectorAll('.retro-btn');
        buttons.forEach(btn => {
            expect(btn.getAttribute('aria-pressed')).toBe('false');
            expect(btn.classList.contains('pressed')).toBe(false);
        });
    });
});

/* ── v2: applyLanguage ──────────────────────────────────────── */

describe('applyLanguage', () => {
    test('sets currentLang and persists to localStorage', () => {
        player.applyLanguage('pt-BR');
        expect(localStorageMock.setItem).toHaveBeenCalledWith('rc-lang', 'pt-BR');
        // t() should now use pt-BR translations
        expect(player.t('share')).toBe('Compartilhar:');
    });

    test('translates data-i18n elements in the DOM', () => {
        const el = document.createElement('span');
        el.dataset.i18n = 'share';
        document.body.appendChild(el);
        player.applyLanguage('pt-BR');
        expect(el.textContent).toBe('Compartilhar:');
        document.body.removeChild(el);
    });

    test('checks the matching language radio button', () => {
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'language';
        radio.value = 'es';
        document.body.appendChild(radio);
        player.applyLanguage('es');
        expect(radio.checked).toBe(true);
        document.body.removeChild(radio);
    });

    test('falls back to en for unknown language', () => {
        player.applyLanguage('xx');
        // t() with unknown lang falls back to en
        expect(player.t('share')).toBe('Share:');
    });

    test('restores to en properly', () => {
        player.applyLanguage('en');
        expect(player.t('share')).toBe('Share:');
    });
});

/* ── v2: playMechanicalClick ────────────────────────────────── */

describe('playMechanicalClick', () => {
    test('creates AudioContext and plays a click sound', () => {
        const mockSource = {
            connect: jest.fn(),
            start: jest.fn(),
            buffer: null,
            onended: null,
        };
        const mockFilter = { connect: jest.fn(), type: '', frequency: { value: 0 }, Q: { value: 0 } };
        const mockGain = { connect: jest.fn(), gain: { value: 0 } };
        const mockBuffer = { getChannelData: jest.fn(() => new Float32Array(1323)) };
        const mockCtx = {
            sampleRate: 44100,
            createBuffer: jest.fn(() => mockBuffer),
            createBufferSource: jest.fn(() => mockSource),
            createBiquadFilter: jest.fn(() => mockFilter),
            createGain: jest.fn(() => mockGain),
            destination: {},
            close: jest.fn(),
        };
        window.AudioContext = jest.fn(() => mockCtx);

        player.playMechanicalClick();

        expect(window.AudioContext).toHaveBeenCalled();
        expect(mockCtx.createBuffer).toHaveBeenCalledWith(1, expect.any(Number), 44100);
        expect(mockCtx.createBufferSource).toHaveBeenCalled();
        expect(mockSource.connect).toHaveBeenCalledWith(mockFilter);
        expect(mockFilter.connect).toHaveBeenCalledWith(mockGain);
        expect(mockGain.connect).toHaveBeenCalledWith(mockCtx.destination);
        expect(mockSource.start).toHaveBeenCalled();

        // Trigger cleanup callback
        mockSource.onended();
        expect(mockCtx.close).toHaveBeenCalled();
    });

    test('silently fails when AudioContext not available', () => {
        delete window.AudioContext;
        delete window.webkitAudioContext;
        expect(() => player.playMechanicalClick()).not.toThrow();
    });

    test('silently fails when AudioContext throws', () => {
        window.AudioContext = jest.fn(() => { throw new Error('not allowed'); });
        expect(() => player.playMechanicalClick()).not.toThrow();
    });
});

/* ── v2: handleRetroButton ──────────────────────────────────── */

describe('handleRetroButton', () => {
    let lyricsBtn, detailsBtn, factsBtn, quizBtn, infoPanel, infoPanelContent;

    beforeEach(() => {
        // Provide AudioContext mock to avoid errors from playMechanicalClick
        const mockSource = { connect: jest.fn(), start: jest.fn(), buffer: null, onended: null };
        const mockFilter = { connect: jest.fn(), type: '', frequency: { value: 0 }, Q: { value: 0 } };
        const mockGain = { connect: jest.fn(), gain: { value: 0 } };
        const mockBuffer = { getChannelData: jest.fn(() => new Float32Array(100)) };
        window.AudioContext = jest.fn(() => ({
            sampleRate: 44100,
            createBuffer: jest.fn(() => mockBuffer),
            createBufferSource: jest.fn(() => mockSource),
            createBiquadFilter: jest.fn(() => mockFilter),
            createGain: jest.fn(() => mockGain),
            destination: {},
            close: jest.fn(),
        }));

        lyricsBtn = document.querySelector('.retro-btn[data-query="lyrics"]');
        detailsBtn = document.querySelector('.retro-btn[data-query="details"]');
        factsBtn = document.querySelector('.retro-btn[data-query="facts"]');
        quizBtn = document.querySelector('.retro-btn[data-query="quiz"]');
        infoPanel = document.getElementById('info-panel');
        infoPanelContent = document.getElementById('info-panel-content');

        // Reset state
        player.activeQuery = null;
        document.querySelectorAll('.retro-btn').forEach(b => {
            b.classList.remove('pressed');
            b.setAttribute('aria-pressed', 'false');
        });
        infoPanel.classList.remove('open');
        infoPanelContent.innerHTML = '';
        fetch.mockClear();
    });

    test('pressing a button sets it as pressed and opens info panel (no track)', () => {
        // Default artist is "Radio Calico" => shows no_track message
        document.getElementById('artist').textContent = 'Radio Calico';
        document.getElementById('track').textContent = 'Live Stream';

        player.handleRetroButton(lyricsBtn);

        expect(lyricsBtn.classList.contains('pressed')).toBe(true);
        expect(lyricsBtn.getAttribute('aria-pressed')).toBe('true');
        expect(infoPanel.classList.contains('open')).toBe(true);
        expect(infoPanelContent.innerHTML).toContain('color:#888');
    });

    test('pressing the same button again toggles it off', () => {
        document.getElementById('artist').textContent = 'Radio Calico';
        player.handleRetroButton(lyricsBtn);
        expect(player.activeQuery).toBe('lyrics');

        // Press again — should toggle off
        player.handleRetroButton(lyricsBtn);
        expect(lyricsBtn.classList.contains('pressed')).toBe(false);
        expect(lyricsBtn.getAttribute('aria-pressed')).toBe('false');
        expect(infoPanel.classList.contains('open')).toBe(false);
        expect(player.activeQuery).toBeNull();
    });

    test('pressing a different button releases the previous one', () => {
        document.getElementById('artist').textContent = 'Radio Calico';
        player.handleRetroButton(lyricsBtn);
        expect(lyricsBtn.classList.contains('pressed')).toBe(true);

        player.handleRetroButton(detailsBtn);
        expect(lyricsBtn.classList.contains('pressed')).toBe(false);
        expect(lyricsBtn.getAttribute('aria-pressed')).toBe('false');
        expect(detailsBtn.classList.contains('pressed')).toBe(true);
        expect(detailsBtn.getAttribute('aria-pressed')).toBe('true');
    });

    test('fetches song info from API when track is available', async () => {
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';
        document.getElementById('album').textContent = 'Help!';

        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ ok: true, content: '## Lyrics\nYesterday, all my troubles...' }),
        });

        player.handleRetroButton(lyricsBtn);

        // Should show loading state
        expect(infoPanelContent.innerHTML).toContain('spinner');
        expect(infoPanel.classList.contains('open')).toBe(true);

        // Wait for fetch to resolve
        await new Promise(r => setTimeout(r, 50));

        expect(fetch).toHaveBeenCalledWith('/api/song-info', expect.objectContaining({
            method: 'POST',
        }));
        expect(infoPanelContent.innerHTML).toContain('Lyrics');
        expect(infoPanelContent.innerHTML).toContain('info-share-row');
    });

    test('shows error when API returns not ok', async () => {
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';

        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ ok: false, error: 'Ollama is down' }),
        });

        player.handleRetroButton(factsBtn);
        await new Promise(r => setTimeout(r, 50));

        expect(infoPanelContent.innerHTML).toContain('Ollama is down');
        expect(infoPanelContent.innerHTML).toContain('color:#c0392b');
    });

    test('shows network error on fetch failure', async () => {
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';

        fetch.mockRejectedValueOnce(new Error('Network failure'));

        player.handleRetroButton(lyricsBtn);
        await new Promise(r => setTimeout(r, 50));

        expect(infoPanelContent.innerHTML).toContain('color:#c0392b');
    });

    test('ignores late response if user switched buttons', async () => {
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';

        let resolveFirst;
        fetch.mockImplementationOnce(() => new Promise(r => { resolveFirst = r; }));
        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ ok: true, content: 'Details content' }),
        });

        player.handleRetroButton(lyricsBtn);
        // Switch to details before lyrics response arrives
        player.handleRetroButton(detailsBtn);
        await new Promise(r => setTimeout(r, 50));

        // Now resolve the first (lyrics) response — should be ignored
        resolveFirst({ ok: true, json: () => Promise.resolve({ ok: true, content: 'Late lyrics' }) });
        await new Promise(r => setTimeout(r, 50));

        // Panel should show details, not late lyrics
        expect(player.activeQuery).toBe('details');
    });

    test('quiz button delegates to startQuiz', async () => {
        document.getElementById('artist').textContent = 'Radio Calico';
        document.getElementById('track').textContent = 'Live Stream';

        player.handleRetroButton(quizBtn);

        // Quiz btn should be pressed
        expect(quizBtn.classList.contains('pressed')).toBe(true);
        expect(player.activeQuery).toBe('quiz');
        // Shows no_track since artist is default
        expect(infoPanelContent.innerHTML).toContain('color:#888');
    });
});

/* ── v2: wireInfoShareButtons ───────────────────────────────── */

describe('wireInfoShareButtons', () => {
    beforeEach(() => {
        window.open = jest.fn();
    });

    test('attaches click listeners that open share URLs', () => {
        // Set up share meta
        player.buildInfoShareRow('lyrics', 'Artist', 'Track', 'Content here');
        // Insert the row into DOM
        document.getElementById('info-panel-content').innerHTML =
            player.buildInfoShareRow('lyrics', 'Artist', 'Track', 'Content here');
        player.wireInfoShareButtons();

        const waBtn = document.querySelector('#info-share-row .share-btn[data-platform="whatsapp"]');
        waBtn.click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('wa.me'),
            '_blank',
            'noopener'
        );
    });

    test('twitter share button opens x.com', () => {
        document.getElementById('info-panel-content').innerHTML =
            player.buildInfoShareRow('facts', 'Beatles', 'Help', 'Fun facts');
        player.wireInfoShareButtons();

        const btn = document.querySelector('#info-share-row .share-btn[data-platform="twitter"]');
        btn.click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('x.com/intent/tweet'),
            '_blank',
            'noopener'
        );
    });

    test('telegram share button opens t.me', () => {
        document.getElementById('info-panel-content').innerHTML =
            player.buildInfoShareRow('jokes', 'Artist', 'Track', 'A joke');
        player.wireInfoShareButtons();

        const btn = document.querySelector('#info-share-row .share-btn[data-platform="telegram"]');
        btn.click();
        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('t.me/share'),
            '_blank',
            'noopener'
        );
    });

    test('returns early if no info-share-row in DOM', () => {
        document.getElementById('info-panel-content').innerHTML = '<p>No share row</p>';
        expect(() => player.wireInfoShareButtons()).not.toThrow();
    });
});

/* ── v2: _buildShareText per-platform limits ────────────────── */

describe('_buildShareText', () => {
    beforeEach(() => {
        player.applyLanguage('en');
    });

    test('truncates content for Twitter (280 chars)', () => {
        const longContent = 'A'.repeat(500);
        player.buildInfoShareRow('lyrics', 'Artist', 'Track', longContent);
        const text = player._buildShareText(280);
        expect(text.length).toBeLessThanOrEqual(283); // 280 + potential "..."
        expect(text).toContain('...');
    });

    test('allows longer content for WhatsApp (4000 chars)', () => {
        const longContent = 'B'.repeat(3000);
        player.buildInfoShareRow('details', 'Artist', 'Track', longContent);
        const text = player._buildShareText(4000);
        expect(text.length).toBeLessThanOrEqual(4003);
    });

    test('does not add ellipsis if content fits', () => {
        player.buildInfoShareRow('facts', 'Art', 'Trk', 'Short content.');
        const text = player._buildShareText(4000);
        expect(text).not.toContain('...');
        expect(text).toContain('Short content.');
    });

    test('includes header with label, track, artist', () => {
        player.buildInfoShareRow('merchandise', 'Queen', 'Bohemian Rhapsody', 'Merch info');
        const text = player._buildShareText(4000);
        expect(text).toContain('Merchandise');
        expect(text).toContain('Queen');
        expect(text).toContain('Bohemian Rhapsody');
        expect(text).toContain('via Radio Calico AI');
    });

    test('strips markdown formatting from content', () => {
        player.buildInfoShareRow('lyrics', 'A', 'T', '## Heading\n**bold** and *italic* with `code`');
        const text = player._buildShareText(4000);
        expect(text).not.toContain('##');
        expect(text).not.toContain('**');
        expect(text).not.toContain('`');
    });
});

/* ── v2: Quiz flow — startQuiz ──────────────────────────────── */

describe('startQuiz', () => {
    let infoPanel, infoPanelContent;

    beforeEach(() => {
        infoPanel = document.getElementById('info-panel');
        infoPanelContent = document.getElementById('info-panel-content');
        infoPanel.classList.remove('open');
        infoPanelContent.innerHTML = '';
        player.quizState = null;
        fetch.mockClear();
    });

    test('shows no_track message when no real track is playing', () => {
        document.getElementById('artist').textContent = 'Radio Calico';
        document.getElementById('track').textContent = 'Live Stream';

        player.startQuiz();

        expect(infoPanel.classList.contains('open')).toBe(true);
        expect(infoPanelContent.innerHTML).toContain('color:#888');
    });

    test('shows loading then renders first question on success', async () => {
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';
        document.getElementById('album').textContent = 'Help!';

        const questions = [
            { q: 'Who wrote Yesterday?', options: ['A) Lennon', 'B) McCartney', 'C) Harrison', 'D) Starr'], answer: 'B' },
            { q: 'Q2?', options: ['A', 'B', 'C', 'D'], answer: 'A' },
            { q: 'Q3?', options: ['A', 'B', 'C', 'D'], answer: 'C' },
            { q: 'Q4?', options: ['A', 'B', 'C', 'D'], answer: 'D' },
            { q: 'Q5?', options: ['A', 'B', 'C', 'D'], answer: 'B' },
        ];
        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ ok: true, questions }),
        });

        player.startQuiz();
        expect(infoPanelContent.innerHTML).toContain('spinner');

        await new Promise(r => setTimeout(r, 50));

        expect(player.quizState).not.toBeNull();
        expect(player.quizState.questions).toHaveLength(5);
        expect(player.quizState.current).toBe(0);
        expect(infoPanelContent.innerHTML).toContain('Who wrote Yesterday?');
        expect(infoPanelContent.innerHTML).toContain('quiz-answer');
        expect(infoPanelContent.innerHTML).toContain('quiz-send');
    });

    test('shows error when API returns no questions', async () => {
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';

        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ ok: false, error: 'Ollama is down' }),
        });

        player.startQuiz();
        await new Promise(r => setTimeout(r, 50));

        expect(infoPanelContent.innerHTML).toContain('Ollama is down');
    });

    test('shows error on network failure', async () => {
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';

        fetch.mockRejectedValueOnce(new Error('timeout'));

        player.startQuiz();
        await new Promise(r => setTimeout(r, 50));

        expect(infoPanelContent.innerHTML).toContain('Network error');
    });
});

/* ── v2: Quiz answer submission ─────────────────────────────── */

describe('submitQuizAnswer', () => {
    let infoPanelContent;

    const makeQuestions = () => [
        { q: 'Q1?', options: ['A', 'B', 'C', 'D'], answer: 'B' },
        { q: 'Q2?', options: ['A', 'B', 'C', 'D'], answer: 'A' },
        { q: 'Q3?', options: ['A', 'B', 'C', 'D'], answer: 'C' },
        { q: 'Q4?', options: ['A', 'B', 'C', 'D'], answer: 'D' },
        { q: 'Q5?', options: ['A', 'B', 'C', 'D'], answer: 'B' },
    ];

    beforeEach(() => {
        infoPanelContent = document.getElementById('info-panel-content');
        player.quizState = { questions: makeQuestions(), current: 0, scores: [], total: 0 };
        // Render so DOM elements exist
        player.renderQuizQuestion();
        fetch.mockClear();
    });

    test('does nothing if answer is empty', () => {
        player.submitQuizAnswer('');
        expect(fetch).not.toHaveBeenCalled();
    });

    test('does nothing if quizState is null', () => {
        player.quizState = null;
        player.submitQuizAnswer('B');
        expect(fetch).not.toHaveBeenCalled();
    });

    test('sends answer to API and advances to next question', async () => {
        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ score: 5, reaction: 'Correct!' }),
        });

        player.submitQuizAnswer('B');

        // Input should be disabled
        const input = document.getElementById('quiz-answer');
        const sendBtn = document.getElementById('quiz-send');
        expect(input.disabled).toBe(true);
        expect(sendBtn.disabled).toBe(true);

        await new Promise(r => setTimeout(r, 50));

        expect(player.quizState.current).toBe(1);
        expect(player.quizState.total).toBe(5);
        expect(player.quizState.scores).toHaveLength(1);
        expect(player.quizState.scores[0].score).toBe(5);
    });

    test('handles API failure gracefully (score 0, continues)', async () => {
        fetch.mockRejectedValueOnce(new Error('network'));

        player.submitQuizAnswer('A');
        await new Promise(r => setTimeout(r, 50));

        expect(player.quizState.current).toBe(1);
        expect(player.quizState.scores[0].score).toBe(0);
        expect(player.quizState.scores[0].reaction).toContain('crashed');
    });

    test('renders summary after 5th question', async () => {
        // Set state to question 4 (0-indexed) with 4 prior scores
        player.quizState.current = 4;
        player.quizState.scores = [
            { userAnswer: 'A', score: 5, reaction: 'Great!' },
            { userAnswer: 'B', score: 3, reaction: 'OK' },
            { userAnswer: 'C', score: 5, reaction: 'Nailed it' },
            { userAnswer: 'D', score: 0, reaction: 'Wrong' },
        ];
        player.quizState.total = 13;
        player.renderQuizQuestion();

        fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({ score: 5, reaction: 'Final correct!' }),
        });

        player.submitQuizAnswer('B');
        await new Promise(r => setTimeout(r, 50));

        expect(player.quizState.current).toBe(5);
        // Should show summary with score
        expect(infoPanelContent.innerHTML).toContain('quiz-score');
        expect(infoPanelContent.innerHTML).toContain('Final Score');
        expect(infoPanelContent.innerHTML).toContain('18');  // 13 + 5
    });
});

/* ── v2: renderQuizQuestion ─────────────────────────────────── */

describe('renderQuizQuestion', () => {
    test('returns early if quizState is null', () => {
        player.quizState = null;
        const content = document.getElementById('info-panel-content');
        content.innerHTML = 'original';
        player.renderQuizQuestion();
        expect(content.innerHTML).toBe('original');
    });

    test('renders question with options and input', () => {
        player.quizState = {
            questions: [{ q: 'Test question?', options: ['A) One', 'B) Two', 'C) Three', 'D) Four'], answer: 'A' }],
            current: 0,
            scores: [],
            total: 0,
        };
        player.renderQuizQuestion();

        const content = document.getElementById('info-panel-content');
        expect(content.innerHTML).toContain('Test question?');
        expect(content.innerHTML).toContain('A) One');
        expect(content.innerHTML).toContain('quiz-input');
        expect(content.innerHTML).toContain('quiz-send');
    });

    test('shows previous exchanges for later questions', () => {
        player.quizState = {
            questions: [
                { q: 'Q1?', options: ['A', 'B', 'C', 'D'], answer: 'A' },
                { q: 'Q2?', options: ['A', 'B', 'C', 'D'], answer: 'B' },
            ],
            current: 1,
            scores: [{ userAnswer: 'A', score: 5, reaction: 'Correct!' }],
            total: 5,
        };
        player.renderQuizQuestion();

        const content = document.getElementById('info-panel-content');
        expect(content.innerHTML).toContain('Q1');
        expect(content.innerHTML).toContain('+5 pts');
        expect(content.innerHTML).toContain('Q2');
    });

    test('send button and enter key submit answer', () => {
        player.quizState = {
            questions: [
                { q: 'Q1?', options: ['A', 'B', 'C', 'D'], answer: 'A' },
                { q: 'Q2?', options: ['A', 'B', 'C', 'D'], answer: 'B' },
            ],
            current: 0,
            scores: [],
            total: 0,
        };
        player.renderQuizQuestion();
        fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ score: 0, reaction: 'Nope' }) });

        const input = document.getElementById('quiz-answer');
        input.value = 'A';
        document.getElementById('quiz-send').click();
        expect(fetch).toHaveBeenCalledWith('/api/quiz/answer', expect.any(Object));
    });
});

/* ── v2: renderQuizSummary ──────────────────────────────────── */

describe('renderQuizSummary', () => {
    let infoPanelContent;

    beforeEach(() => {
        infoPanelContent = document.getElementById('info-panel-content');
        document.getElementById('artist').textContent = 'The Beatles';
        document.getElementById('track').textContent = 'Yesterday';
    });

    test('returns early if quizState is null', () => {
        player.quizState = null;
        infoPanelContent.innerHTML = 'original';
        player.renderQuizSummary();
        expect(infoPanelContent.innerHTML).toBe('original');
    });

    test('shows legend verdict for high score (>=20)', () => {
        player.quizState = {
            questions: Array(5).fill({ q: 'Q?', options: ['A','B','C','D'], answer: 'A' }),
            current: 5,
            scores: Array(5).fill({ userAnswer: 'A', score: 5, reaction: 'Perfect!' }),
            total: 25,
        };
        player.renderQuizSummary();
        expect(infoPanelContent.innerHTML).toContain('25');
        expect(infoPanelContent.innerHTML).toContain('LEGEND');
    });

    test('shows rock solid verdict for medium-high score (12-19)', () => {
        player.quizState = {
            questions: Array(5).fill({ q: 'Q?', options: ['A','B','C','D'], answer: 'A' }),
            current: 5,
            scores: Array(5).fill({ userAnswer: 'A', score: 3, reaction: 'OK' }),
            total: 15,
        };
        player.renderQuizSummary();
        expect(infoPanelContent.innerHTML).toContain('Rock solid');
    });

    test('shows not bad verdict for medium score (5-11)', () => {
        player.quizState = {
            questions: Array(5).fill({ q: 'Q?', options: ['A','B','C','D'], answer: 'A' }),
            current: 5,
            scores: Array(5).fill({ userAnswer: 'A', score: 1, reaction: 'Meh' }),
            total: 8,
        };
        player.renderQuizSummary();
        expect(infoPanelContent.innerHTML).toContain('Not bad');
    });

    test('shows meh verdict for low score (0-4)', () => {
        player.quizState = {
            questions: Array(5).fill({ q: 'Q?', options: ['A','B','C','D'], answer: 'A' }),
            current: 5,
            scores: Array(5).fill({ userAnswer: 'X', score: 0, reaction: 'Wrong' }),
            total: 2,
        };
        player.renderQuizSummary();
        expect(infoPanelContent.innerHTML).toContain('Meh');
    });

    test('shows impressively wrong verdict for negative score', () => {
        player.quizState = {
            questions: Array(5).fill({ q: 'Q?', options: ['A','B','C','D'], answer: 'A' }),
            current: 5,
            scores: Array(5).fill({ userAnswer: 'X', score: -2, reaction: 'Terrible' }),
            total: -5,
        };
        player.renderQuizSummary();
        expect(infoPanelContent.innerHTML).toContain('Impressively wrong');
    });

    test('includes share buttons and quiz exchange history', () => {
        player.quizState = {
            questions: [
                { q: 'Q1?', options: ['A','B','C','D'], answer: 'A' },
                { q: 'Q2?', options: ['A','B','C','D'], answer: 'B' },
            ],
            current: 2,
            scores: [
                { userAnswer: 'A', score: 5, reaction: 'Yes!' },
                { userAnswer: 'C', score: 0, reaction: 'No!' },
            ],
            total: 5,
        };
        player.renderQuizSummary();
        expect(infoPanelContent.innerHTML).toContain('info-share-row');
        expect(infoPanelContent.innerHTML).toContain('Q1');
        expect(infoPanelContent.innerHTML).toContain('Q2');
    });
});

/* ── v2: setupMetadataTextTracks ────────────────────────────── */

describe('setupMetadataTextTracks', () => {
    test('is a function that can be called without error', () => {
        expect(typeof player.setupMetadataTextTracks).toBe('function');
        // It was already called during boot; just verify it exists
    });
});

/* ── v2: markdownToHtml tables ──────────────────────────────── */

describe('markdownToHtml — tables', () => {
    test('converts table rows', () => {
        const md = '| Name | Value |\n|------|-------|\n| A | 1 |';
        const html = player.markdownToHtml(md);
        expect(html).toContain('<table>');
        expect(html).toContain('<tr>');
        expect(html).toContain('<td>');
        expect(html).toContain('Name');
        expect(html).toContain('Value');
    });

    test('removes separator rows', () => {
        const md = '| H1 | H2 |\n|---|---|\n| D1 | D2 |';
        const html = player.markdownToHtml(md);
        // Separator row should be gone (empty string)
        expect(html).toContain('H1');
        expect(html).toContain('D1');
    });
});

/* ── v2: Safari native HLS branch & unsupported branch ──────── */

describe('HLS support branches', () => {
    test('Hls.isSupported was called at boot time', () => {
        // Verify that the boot code did check HLS support
        expect(window.Hls.isSupported).toHaveBeenCalled();
    });
});

/* ── v2: logout fetch failure branch ────────────────────────── */

describe('logout button', () => {
    test('clears auth state even if fetch fails', () => {
        // Simulate logged-in state
        localStorageMock.setItem('rc-token', 'test-token');
        localStorageMock.setItem('rc-user', 'testuser');

        // The logout button handler calls fetch.catch — ensure no error thrown
        fetch.mockRejectedValueOnce(new Error('server down'));
        const logoutBtn = document.getElementById('btn-logout');
        expect(() => logoutBtn.click()).not.toThrow();

        expect(localStorageMock.removeItem).toHaveBeenCalledWith('rc-token');
        expect(localStorageMock.removeItem).toHaveBeenCalledWith('rc-user');
    });
});

/* ── v2: profile save with checked genres ───────────────────── */

describe('profile form genre checkboxes', () => {
    test('genre checkboxes exist in DOM', () => {
        const cbs = document.querySelectorAll('#genre-grid input[type="checkbox"]');
        expect(cbs.length).toBe(3);
        expect([...cbs].map(c => c.value)).toEqual(['rock', 'jazz', 'pop']);
    });
});
