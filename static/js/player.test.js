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
        <div id="genre-grid"></div>
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

    test('parses valid ID3v2 TIT2 frame', () => {
        // Build minimal ID3v2 header + TIT2 frame
        const header = [
            0x49, 0x44, 0x33,   // 'ID3'
            0x03, 0x00,          // version 2.3
            0x00,                // flags
            0x00, 0x00, 0x00, 0x12, // tag size = 18 bytes (syncsafe)
        ];
        // TIT2 frame: id(4) + size(4) + flags(2) + encoding(1) + text
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
});

/* ── History & filtering ────────────────────────────────────── */

describe('getFilteredHistory', () => {
    beforeEach(() => {
        player.history.length = 0;
        player.prevFilter = 'all';
        player.historyLimit = 5;
        player.lastSummary = {};
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
        expect(text).toContain('Recently Played on Radio Calico:');
        expect(text).toContain('1. T1 by A (Album1)');
        expect(text).toContain('2. T2 by B');
    });

    test('includes ratings when available', () => {
        player.history.push({ artist: 'A', title: 'T1', album: '' });
        player.lastSummary = { 'A - T1': { likes: 3, dislikes: 1 } };
        const text = player.getRecentlyPlayedText();
        expect(text).toContain('[3 likes / 1 unlikes]');
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
    test('sends POST to /api/ratings', async () => {
        document.getElementById('artist').textContent = 'TestArtist';
        document.getElementById('track').textContent = 'TestTitle';
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
        );
        await player.submitRating(1);
        expect(global.fetch).toHaveBeenCalledWith('/api/ratings', expect.objectContaining({
            method: 'POST',
        }));
    });

    test('handles 409 duplicate rating', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
        );
        await player.submitRating(1);
        expect(document.getElementById('rating-feedback').textContent).toBe('Already rated this track');
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

    test('returns false on error', async () => {
        global.fetch = jest.fn(() => Promise.reject(new Error('network')));
        const result = await player.checkIfRated('A - T');
        expect(result).toBe(false);
    });
});

/* ── renderHistory ──────────────────────────────────────────── */

describe('renderHistory', () => {
    beforeEach(() => {
        player.history.length = 0;
        player.lastSummary = {};
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );
    });

    test('shows empty message when no history', async () => {
        await player.renderHistory();
        expect(document.getElementById('prev-list').innerHTML).toContain('No tracks yet');
    });

    test('renders history items', async () => {
        player.history.push({ artist: 'A', title: 'T', album: 'Al' });
        await player.renderHistory();
        const html = document.getElementById('prev-list').innerHTML;
        expect(html).toContain('A');
        expect(html).toContain('T');
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
        // (first call from boot + our call)
    });
});
