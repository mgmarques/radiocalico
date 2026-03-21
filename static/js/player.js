/**
 * Radio Calico — Live Audio Streaming Web Player
 *
 * Client-side module that handles HLS audio playback, track metadata display,
 * album artwork fetching (iTunes API), user ratings, authentication, profile
 * management, feedback submission, social sharing, and theme/quality settings.
 *
 * The player streams lossless audio via HLS from AWS CloudFront, displays
 * track metadata from a CloudFront JSON endpoint, and stores ratings and
 * user data through a local Flask API on port 5000.
 *
 * @module player
 */

// ── Structured logger ────────────────────────────────────────
/**
 * Lightweight structured logger for client-side events. Outputs JSON to
 * the browser console with timestamp, level, message, and context.
 */
const log = {
    _emit(level, message, context) {
        const entry = {
            timestamp: new Date().toISOString(),
            level,
            logger: 'player',
            message,
            ...context,
        };
        if (level === 'error') console.error(JSON.stringify(entry));
        else if (level === 'warn') console.warn(JSON.stringify(entry));
        else console.log(JSON.stringify(entry));
    },
    info(message, context = {}) { this._emit('info', message, context); },
    warn(message, context = {}) { this._emit('warn', message, context); },
    error(message, context = {}) { this._emit('error', message, context); },
};

const STREAM_URL = 'https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8';
const STREAM_LABELS = {
    flac: 'FLAC Hi-Res (Lossless)',
    aac:  'AAC Hi-Fi (211 kbps)',
};
let currentStreamQuality = localStorage.getItem('rc-stream-quality') || 'flac';
const METADATA_URL = 'https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json';
const METADATA_DEBOUNCE_MS = 3000; // min interval between metadata fetches
const MAX_HISTORY = 20;
const HLS_RETRY_BASE_MS = 4000;
const HLS_RETRY_MAX_MS = 60000;
const HLS_MAX_RETRIES = 10;
const ARTWORK_SIZE = '600x600';
const SHARE_ARTWORK_SIZE = '300x300';
const LATENCY_FALLBACK_SEC = 6;
const LATENCY_MAX_SEC = 15;

// ── i18n — Internationalization ─────────────────────────────
const _TRANSLATIONS = {
    en: {
        now_playing: 'Now Playing',
        recently_played: 'Recently Played',
        rate_track: 'Rate this track:',
        share: 'Share:',
        share_list: 'Share list:',
        filter_all: 'All',
        filter_liked: 'Liked',
        filter_disliked: 'Disliked',
        btn_lyrics: 'Lyrics',
        btn_details: 'Details',
        btn_facts: 'Interesting Facts',
        btn_merchandise: 'Merchandise',
        btn_jokes: 'Jokes',
        btn_everything: 'Everything About',
        btn_quiz: 'Quiz',
        settings_language: 'Language',
        loading_ai: 'Asking the AI about this track\u2026',
        loading_quiz: 'Generating your quiz\u2026 This might take a moment.',
        no_track: 'No track is currently playing. Start the stream first!',
        network_error: 'Network error. Check that the server and Ollama are running.',
        quiz_score_legend: 'Final Score',
        quiz_your_answer: 'Your answer',
        quiz_send: 'Send',
        waiting_track: 'Waiting for track data\u2026',
        no_tracks_yet: 'No tracks yet',
        no_matching: 'No matching tracks',
        listening_to: 'Listening to',
        on_radio: 'on Radio Calico!',
        likes: 'likes',
        unlikes: 'unlikes',
        stream_quality: 'Stream quality',
        via_ai: 'via Radio Calico AI',
        scored_quiz: 'I scored',
        on_quiz: 'on the Radio Calico Song Quiz for',
    },
    'pt-BR': {
        now_playing: 'Tocando Agora',
        recently_played: 'Tocadas Recentemente',
        rate_track: 'Avalie esta faixa:',
        share: 'Compartilhar:',
        share_list: 'Compartilhar lista:',
        filter_all: 'Todas',
        filter_liked: 'Curtidas',
        filter_disliked: 'N\u00e3o Curtidas',
        btn_lyrics: 'Letras',
        btn_details: 'Detalhes',
        btn_facts: 'Curiosidades',
        btn_merchandise: 'Produtos',
        btn_jokes: 'Piadas',
        btn_everything: 'Tudo Sobre',
        btn_quiz: 'Quiz',
        settings_language: 'Idioma',
        loading_ai: 'Perguntando \u00e0 IA sobre esta faixa\u2026',
        loading_quiz: 'Gerando seu quiz\u2026 Isso pode levar um momento.',
        no_track: 'Nenhuma faixa tocando. Inicie o stream primeiro!',
        network_error: 'Erro de rede. Verifique se o servidor e o Ollama est\u00e3o rodando.',
        quiz_score_legend: 'Pontua\u00e7\u00e3o Final',
        quiz_your_answer: 'Sua resposta',
        quiz_send: 'Enviar',
        waiting_track: 'Aguardando dados da faixa\u2026',
        no_tracks_yet: 'Nenhuma faixa ainda',
        no_matching: 'Nenhuma faixa correspondente',
        listening_to: 'Ouvindo',
        on_radio: 'na Radio Calico!',
        likes: 'curtidas',
        unlikes: 'n\u00e3o curtidas',
        stream_quality: 'Qualidade do stream',
        via_ai: 'via Radio Calico AI',
        scored_quiz: 'Fiz',
        on_quiz: 'no Quiz Musical da Radio Calico para',
    },
    es: {
        now_playing: 'Reproduciendo Ahora',
        recently_played: 'Reproducidas Recientemente',
        rate_track: 'Califica esta pista:',
        share: 'Compartir:',
        share_list: 'Compartir lista:',
        filter_all: 'Todas',
        filter_liked: 'Gustadas',
        filter_disliked: 'No Gustadas',
        btn_lyrics: 'Letras',
        btn_details: 'Detalles',
        btn_facts: 'Datos Curiosos',
        btn_merchandise: 'Mercanc\u00eda',
        btn_jokes: 'Chistes',
        btn_everything: 'Todo Sobre',
        btn_quiz: 'Quiz',
        settings_language: 'Idioma',
        loading_ai: 'Preguntando a la IA sobre esta pista\u2026',
        loading_quiz: 'Generando tu quiz\u2026 Esto puede tomar un momento.',
        no_track: '\u00a1Ninguna pista reproduci\u00e9ndose! Inicia el stream primero.',
        network_error: 'Error de red. Verifica que el servidor y Ollama est\u00e9n funcionando.',
        quiz_score_legend: 'Puntuaci\u00f3n Final',
        quiz_your_answer: 'Tu respuesta',
        quiz_send: 'Enviar',
        waiting_track: 'Esperando datos de la pista\u2026',
        no_tracks_yet: 'Ninguna pista a\u00fan',
        no_matching: 'Ninguna pista coincidente',
        listening_to: 'Escuchando',
        on_radio: 'en Radio Calico!',
        likes: 'me gusta',
        unlikes: 'no me gusta',
        stream_quality: 'Calidad del stream',
        via_ai: 'v\u00eda Radio Calico AI',
        scored_quiz: 'Obtuve',
        on_quiz: 'en el Quiz Musical de Radio Calico para',
    },
};

// Map language codes to LLM language names
const _LANG_TO_LLM = { en: 'English', 'pt-BR': 'Brazilian Portuguese', es: 'Spanish' };

let currentLang = localStorage.getItem('rc-lang') || 'en';

function t(key) {
    return (_TRANSLATIONS[currentLang] || _TRANSLATIONS.en)[key]
        || _TRANSLATIONS.en[key] || key;
}

function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('rc-lang', lang);
    // Translate all static data-i18n elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        const text = t(key);
        if (text) el.textContent = text;
    });
    // Update the radio button in settings
    const radio = document.querySelector(`input[name="language"][value="${lang}"]`);
    if (radio) radio.checked = true;
    // Refresh dynamic content that contains translatable strings
    if (typeof updateStreamQualityDisplay === 'function') updateStreamQualityDisplay();
    if (typeof renderHistory === 'function') renderHistory();
}

// ── Elements ────────────────────────────────────────────────
const audio      = document.getElementById('audio');
const playBtn    = document.getElementById('play-btn');
const muteBtn    = document.getElementById('mute-btn');
const volumeEl   = document.getElementById('volume');
const barTime    = document.getElementById('bar-time');
const artistEl   = document.getElementById('artist');
const trackEl    = document.getElementById('track');
const albumEl    = document.getElementById('album');
const artworkEl  = document.getElementById('artwork');
const prevList   = document.getElementById('prev-list');
const rateUp     = document.getElementById('rate-up');
const rateDown   = document.getElementById('rate-down');
const rateFb     = document.getElementById('rating-feedback');
const rateUpCount   = document.getElementById('rate-up-count');
const rateDownCount = document.getElementById('rate-down-count');

const iconPlay   = document.getElementById('icon-play');
const iconPause  = document.getElementById('icon-pause');
const iconSpin   = document.getElementById('icon-spin');
const iconVol    = document.getElementById('icon-vol');
const iconMute   = document.getElementById('icon-mute');

// ── State ───────────────────────────────────────────────────
let playing    = false;
let muted      = false;
let hls        = null;
let currentTrack = null;
let trackDuration = null;
let songStartTime = null; // wall-clock ms when current song was detected
let pendingTrackUpdate = null; // timer for delayed track update
let pendingTrackKey = null;    // key of the track waiting to be applied
let hlsRetryCount = 0;
const history  = [];

// ── Icons ───────────────────────────────────────────────────
/**
 * Toggles visibility of the play, pause, and spinner icons on the play button.
 * @param {string} name - Icon to display: 'play', 'pause', or 'spinner'.
 */
function showPlayIcon(name) {
    iconPlay.style.display  = name === 'play'    ? '' : 'none';
    iconPause.style.display = name === 'pause'   ? '' : 'none';
    iconSpin.style.display  = name === 'spinner' ? '' : 'none';
}

// ── iTunes API cache ─────────────────────────────────────────
const ITUNES_CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

/**
 * Fetches iTunes search results with localStorage caching (24h TTL).
 * @param {string} query - The search query string.
 * @returns {Promise<Object>} The iTunes API response data.
 */
async function fetchItunesCached(query) {
    const cacheKey = `rc-itunes-${query}`;
    try {
        const cached = localStorage.getItem(cacheKey);
        if (cached) {
            const { data, ts } = JSON.parse(cached);
            if (Date.now() - ts < ITUNES_CACHE_TTL_MS) return data;
        }
    } catch (_) { /* ignore parse errors */ }
    const res = await fetch(`https://itunes.apple.com/search?term=${encodeURIComponent(query)}&entity=song&limit=1`);
    const data = await res.json();
    try { localStorage.setItem(cacheKey, JSON.stringify({ data, ts: Date.now() })); } catch (e) { log.warn('localstorage_quota', { error: e.message }); }
    return data;
}

// ── Artwork ──────────────────────────────────────────────────
/**
 * Fetches album artwork and track duration from the iTunes Search API.
 * Uses localStorage cache (24h TTL) to reduce duplicate API calls.
 * Updates the artwork element with the retrieved image (or a placeholder on failure)
 * and sets the global trackDuration from iTunes trackTimeMillis.
 * @async
 * @param {string} artist - The artist name to search for.
 * @param {string} title - The track title to search for.
 */
async function fetchArtwork(artist, title) {
    try {
        const data = await fetchItunesCached(`${artist} ${title}`);
        if (data.results && data.results.length > 0) {
            const result = data.results[0];
            // Replace 100x100 thumbnail with 600x600
            const url = result.artworkUrl100.replace('100x100', ARTWORK_SIZE);
            artworkEl.innerHTML = `<img src="${escHtml(url)}" alt="${escHtml(title)}" decoding="async">`;
            // Store track duration from iTunes (milliseconds → seconds)
            trackDuration = result.trackTimeMillis ? result.trackTimeMillis / 1000 : null;
        } else {
            artworkEl.innerHTML = `<div class="artwork-placeholder">♪</div>`;
            trackDuration = null;
        }
    } catch (e) {
        log.warn('artwork_fetch_failed', { error: e.message });
        artworkEl.innerHTML = `<div class="artwork-placeholder">♪</div>`;
        trackDuration = null;
    }
}

// ── Track metadata ──────────────────────────────────────────
/**
 * Updates the Now Playing display with new track information. If the track
 * has changed, pushes the previous track into history, resets the song timer,
 * fetches new artwork, and refreshes the rating UI.
 * @param {string} artist - The artist name.
 * @param {string} title - The track title.
 * @param {string} album - The album name.
 */
function updateTrack(artist, title, album) {
    const key = `${artist}|${title}`;
    if (key === currentTrack) return;

    // Push previous to history (including album)
    if (currentTrack) {
        const pipeIdx = currentTrack.indexOf('|');
        const a = currentTrack.substring(0, pipeIdx);
        const t = currentTrack.substring(pipeIdx + 1);
        pushHistory(a, t, albumEl.textContent || '');
    }

    currentTrack = key;
    songStartTime = Date.now();
    artistEl.textContent = artist || 'Radio Calico';
    trackEl.textContent  = title  || 'Live Stream';
    albumEl.textContent  = album  || '';

    fetchArtwork(artist, title);

    // Update rating UI for the new track
    updateRatingUI();
}

/**
 * Adds a track to the front of the history array and re-renders the list.
 * Caps the history at MAX_HISTORY entries.
 * @param {string} artist - The artist name.
 * @param {string} title - The track title.
 * @param {string} album - The album name.
 */
function pushHistory(artist, title, album) {
    if (!artist && !title) return;
    history.unshift({ artist, title, album: album || '' });
    while (history.length > MAX_HISTORY) history.pop(); // keep up to max dropdown value
    renderHistory();
}

let prevFilter = 'all'; // 'all', 'up', 'down'
let historyLimit = 5;
let lastSummary = {};

/**
 * Renders the Recently Played list in the DOM. Fetches the latest ratings
 * summary from the API, applies the active filter, and builds the HTML list
 * with track info and rating badges.
 * @async
 */
async function renderHistory() {
    if (!history.length) {
        prevList.innerHTML = '<li class="prev-empty">' + t('no_tracks_yet') + '</li>';
        return;
    }

    // Fetch ratings summary, fall back to cached
    try {
        const res = await fetch('/api/ratings/summary');
        if (res.ok) lastSummary = await res.json();
    } catch (e) { log.warn('ratings_summary_failed', { error: e.message }); }

    const filtered = getFilteredHistory();

    if (!filtered.length) {
        prevList.innerHTML = '<li class="prev-empty">' + t('no_matching') + '</li>';
        return;
    }

    prevList.innerHTML = filtered.map(h => {
        const key = `${h.artist} - ${h.title}`;
        const r = lastSummary[key];
        const badge = r
            ? `<span class="prev-ratings">${r.likes} &#x1F44D; ${r.dislikes} &#x1F44E;</span>`
            : '';
        const albumPart = h.album
            ? ` <span class="prev-album">(${escHtml(h.album)})</span>`
            : '';
        return `<li><span class="prev-track">${escHtml(h.title)}</span> by <span class="prev-artist">${escHtml(h.artist)}</span>${albumPart} ${badge}</li>`;
    }).join('');
}

/**
 * Escapes a string for safe insertion into HTML, replacing &, <, >, ", and '.
 * @param {string} str - The raw string to escape.
 * @returns {string} The HTML-escaped string.
 */
function escHtml(str) {
    return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

/**
 * Returns the history array filtered by the active filter (all/up/down)
 * and sliced to the current historyLimit.
 * @returns {Array<{artist: string, title: string, album: string}>} Filtered track entries.
 */
function getFilteredHistory() {
    return history.filter(h => {
        if (prevFilter === 'all') return true;
        const key = `${h.artist} - ${h.title}`;
        const r = lastSummary[key];
        if (!r) return false;
        if (prevFilter === 'up') return r.likes > 0;
        if (prevFilter === 'down') return r.dislikes > 0;
        return true;
    }).slice(0, historyLimit);
}

// ── ID3 parser (decodes text frames from raw ID3v2 bytes) ───
/**
 * Parses raw ID3v2 tag bytes and extracts text frames (TPE1, TIT2, TALB, etc.).
 * Supports UTF-8, UTF-16, UTF-16BE, and ISO-8859-1 text encodings.
 * @param {Uint8Array} raw - The raw ID3v2 tag bytes.
 * @returns {Object.<string, string>} Map of frame IDs to their decoded text values.
 */
function parseID3Frames(raw) {
    const frames = {};
    if (raw.length < 10) return frames;
    const hdr = String.fromCharCode(raw[0], raw[1], raw[2]);
    if (hdr !== 'ID3') return frames;

    const tagSize = (raw[6] << 21) | (raw[7] << 14) | (raw[8] << 7) | raw[9];
    let off = 10;
    const end = Math.min(off + tagSize, raw.length);

    while (off + 10 < end) {
        const id = String.fromCharCode(raw[off], raw[off+1], raw[off+2], raw[off+3]);
        const sz = (raw[off+4] << 24) | (raw[off+5] << 16) | (raw[off+6] << 8) | raw[off+7];
        if (sz <= 0 || off + 10 + sz > end) break;

        if (id.startsWith('T') && id !== 'TXXX') {
            const enc = raw[off + 10];
            const body = raw.slice(off + 11, off + 10 + sz);
            const encoding = enc === 3 ? 'utf-8' : enc === 1 ? 'utf-16' : enc === 2 ? 'utf-16be' : 'iso-8859-1';
            let txt = new TextDecoder(encoding).decode(body);
            txt = txt.replace(/\0/g, '').trim();
            if (txt) frames[id] = txt;
        }
        off += 10 + sz;
    }
    return frames;
}

// ── Process parsed metadata fields ──────────────────────────
/**
 * Processes parsed ID3 metadata fields and updates the track display.
 * Extracts TPE1 (artist), TIT2 (title), and TALB (album) fields and
 * delegates to updateTrack if artist or title are present.
 * @param {Object.<string, string>} fields - Map of ID3 frame IDs to text values.
 */
function handleMetadataFields(fields) {
    const artist = fields['TPE1'] || null;
    const title  = fields['TIT2'] || null;
    const album  = fields['TALB'] || null;

    if (artist || title) {
        updateTrack(
            artist || artistEl.textContent,
            title  || trackEl.textContent,
            album  || albumEl.textContent
        );
    } else if (album) {
        albumEl.textContent = album;
    }
}

// ── Timed-metadata text-track listener (works for both HLS.js & Safari) ──
/**
 * Sets up listeners on the audio element's metadata text tracks to capture
 * timed metadata cues (works for both HLS.js and Safari native HLS).
 * Attaches cuechange handlers to existing and future metadata tracks.
 */
function setupMetadataTextTracks() {
    function onCueChange() {
        const cues = this.activeCues;
        if (!cues || !cues.length) return;
        const fields = {};
        for (let i = 0; i < cues.length; i++) {
            const v = cues[i].value;
            if (v && v.key) fields[v.key] = v.data || v.text || '';
        }
        handleMetadataFields(fields);
    }

    function attachTrack(track) {
        if (track.kind === 'metadata') {
            track.mode = 'hidden';
            track.addEventListener('cuechange', onCueChange);
        }
    }

    audio.textTracks.addEventListener('addtrack', e => attachTrack(e.track));
    for (let i = 0; i < audio.textTracks.length; i++) {
        attachTrack(audio.textTracks[i]);
    }
}

// ── HLS setup ───────────────────────────────────────────────
/**
 * Initializes (or reinitializes) the HLS.js player instance. Destroys any
 * existing instance, loads the stream source, and registers event handlers
 * for manifest parsing, ID3 metadata, fragment changes, level loading,
 * and fatal errors with exponential backoff retry.
 */
function initHls() {
    if (hls) { hls.destroy(); hls = null; }

    hls = new Hls({ lowLatencyMode: true, enableID3MetadataCues: true });
    hls.loadSource(STREAM_URL);
    hls.attachMedia(audio);

    hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
        hlsRetryCount = 0;
        playBtn.disabled = false;
        showPlayIcon('play');
        // Force HLS level based on user's quality choice
        // Master playlist: level 0 = FLAC, level 1 = AAC
        if (data.levels && data.levels.length > 1) {
            const targetCodec = currentStreamQuality === 'flac' ? 'flac' : 'mp4a';
            const idx = data.levels.findIndex(l =>
                l.audioCodec && l.audioCodec.toLowerCase().includes(targetCodec)
            );
            if (idx >= 0) {
                hls.currentLevel = idx;
                hls.loadLevel = idx;
                hls.nextLevel = idx; // lock to prevent auto-switching
            }
        }
    });

    // Parse raw ID3 data from HLS fragments as fallback
    hls.on(Hls.Events.FRAG_PARSING_METADATA, (_, data) => {
        if (!data.samples) return;
        data.samples.forEach(sample => {
            if (sample.data) {
                const fields = parseID3Frames(sample.data);
                handleMetadataFields(fields);
            }
        });
    });

    // Fetch metadata when a new fragment starts playing (song change detection)
    hls.on(Hls.Events.FRAG_CHANGED, () => {
        triggerMetadataFetch();
    });

    // Show source quality from HLS level info
    hls.on(Hls.Events.LEVEL_LOADED, () => {
        const level = hls.levels && hls.levels[hls.currentLevel];
        if (level) {
            const parts = [];
            if (level.audioCodec) parts.push(level.audioCodec.toUpperCase());
            if (level.bitrate)    parts.push(`${Math.round(level.bitrate / 1000)} kbps`);
            if (parts.length) {
                const srcQual = document.getElementById('source-quality');
                if (srcQual) srcQual.textContent = `Source quality: ${parts.join(', ')}`;
            }
        }
    });

    hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
            showPlayIcon('play');
            playing = false;
            hlsRetryCount++;
            const delay = Math.min(HLS_RETRY_BASE_MS * Math.pow(2, hlsRetryCount - 1), HLS_RETRY_MAX_MS);
            if (hlsRetryCount <= HLS_MAX_RETRIES) {
                setTimeout(initHls, delay);
            }
        }
    });
}

// ── Playback ─────────────────────────────────────────────────
/**
 * Toggles audio playback between playing and paused states.
 * Shows a spinner while buffering, switches to pause icon on play,
 * and reverts to play icon on pause or failure.
 */
function togglePlay() {
    if (!playing) {
        playing = true;
        showPlayIcon('spinner');
        audio.volume = parseFloat(volumeEl.value);
        audio.muted  = muted;
        audio.play().catch(() => {
            playing = false;
            showPlayIcon('play');
        });
    } else {
        playing = false;
        audio.pause();
        showPlayIcon('play');
    }
}

// ── Time display ─────────────────────────────────────────────
/**
 * Formats a number of seconds into a "m:ss" time string.
 * @param {number} s - Seconds to format.
 * @returns {string} Formatted time string (e.g. "3:05"), or "0:00" if invalid.
 */
function formatTime(s) {
    if (!isFinite(s) || s < 0) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
}

audio.addEventListener('playing', () => showPlayIcon('pause'));
audio.addEventListener('waiting', () => { if (playing) showPlayIcon('spinner'); });
audio.addEventListener('timeupdate', () => {
    if (playing && songStartTime) {
        const elapsed = (Date.now() - songStartTime) / 1000;
        const total = trackDuration ? formatTime(trackDuration) : 'Live';
        barTime.textContent = `${formatTime(elapsed)} / ${total}`;
    }
});

// ── Volume & mute ─────────────────────────────────────────────
volumeEl.addEventListener('input', () => {
    audio.volume = parseFloat(volumeEl.value);
    if (audio.volume > 0 && muted) {
        muted = false;
        audio.muted = false;
        iconVol.style.display  = '';
        iconMute.style.display = 'none';
    }
});

muteBtn.addEventListener('click', () => {
    muted = !muted;
    audio.muted = muted;
    iconVol.style.display  = muted ? 'none' : '';
    iconMute.style.display = muted ? ''     : 'none';
});

// ── Ratings ───────────────────────────────────────────────────
/**
 * Fetches the ratings summary from the API and updates the like/dislike
 * count badges for the given station (track).
 * @async
 * @param {string} station - The station key ("Artist - Title").
 */
async function fetchTrackRatings(station) {
    try {
        const res = await fetch('/api/ratings/summary');
        if (!res.ok) return;
        const summary = await res.json();
        const r = summary[station];
        rateUpCount.textContent   = r ? r.likes : 0;
        rateDownCount.textContent = r ? r.dislikes : 0;
    } catch (e) { log.warn('track_ratings_failed', { error: e.message }); }
}

/**
 * Checks whether the current user (by IP) has already rated a given station.
 * @async
 * @param {string} station - The station key ("Artist - Title").
 * @returns {Promise<boolean>} True if the user has already rated this track.
 */
async function checkIfRated(station) {
    try {
        const res = await fetch(`/api/ratings/check?station=${encodeURIComponent(station)}`);
        if (!res.ok) return false;
        const data = await res.json();
        return data.rated;
    } catch (e) { log.warn('rating_check_failed', { error: e.message }); return false; }
}

/**
 * Refreshes the rating buttons and feedback text for the currently displayed track.
 * Checks if the user has already rated and fetches the latest counts.
 * @async
 */
async function updateRatingUI() {
    // Immediately clear previous song's rated state so buttons are clickable.
    // Keep counts visible until new ones arrive (avoids 0-flash).
    rateUp.classList.remove('rated');
    rateDown.classList.remove('rated');
    rateFb.textContent = '';

    const station = `${artistEl.textContent} - ${trackEl.textContent}`;
    const alreadyRated = await checkIfRated(station);
    rateUp.classList.toggle('rated', alreadyRated);
    rateDown.classList.toggle('rated', alreadyRated);
    rateFb.textContent = alreadyRated ? 'You rated this track' : '';
    fetchTrackRatings(station);
}

/**
 * Submits a thumbs-up or thumbs-down rating for the current track to the API.
 * Disables rating buttons after a successful submission or duplicate detection.
 * @async
 * @param {number} score - 1 for thumbs up, 0 for thumbs down.
 */
async function submitRating(score) {
    const station = `${artistEl.textContent} - ${trackEl.textContent}`;
    try {
        const res = await fetch('/api/ratings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ station, score })
        });
        if (res.ok) {
            rateUp.classList.add('rated');
            rateDown.classList.add('rated');
            rateFb.textContent = score === 1 ? 'Thanks!' : 'Noted!';
            fetchTrackRatings(station);
        } else if (res.status === 409) {
            rateUp.classList.add('rated');
            rateDown.classList.add('rated');
            rateFb.textContent = 'Already rated this track';
        }
    } catch (e) {
        log.warn('rating_submit_failed', { error: e.message });
        rateFb.textContent = t('network_error');
    }
}

rateUp.addEventListener('click',   () => submitRating(1));
rateDown.addEventListener('click', () => submitRating(0));
playBtn.addEventListener('click', togglePlay);

// ── Share buttons ────────────────────────────────────────────
/**
 * Retrieves the current artwork image URL sized for sharing (300x300).
 * @returns {string} The sharing-sized artwork URL, or an empty string if no artwork is loaded.
 */
function getArtworkUrl() {
    const img = artworkEl.querySelector('img');
    if (!img) return '';
    // Use a smaller size (300x300) for better sharing previews
    return img.src.replace(ARTWORK_SIZE, SHARE_ARTWORK_SIZE);
}

/**
 * Builds the share text for the Now Playing track, including artist, title,
 * album, and artwork URL.
 * @returns {string} Formatted share text for social platforms.
 */
function getShareText() {
    const artist = artistEl.textContent;
    const title  = trackEl.textContent;
    const album  = albumEl.textContent;
    const artUrl = getArtworkUrl();
    let text = `${t('listening_to')} "${title}" by ${artist}`;
    if (album) text += ` (${album})`;
    text += ` ${t('on_radio')}`;
    if (artUrl) text += `\n\nAlbum cover: ${artUrl}`;
    return text;
}

document.getElementById('share-whatsapp').addEventListener('click', () => {
    const text = encodeURIComponent(getShareText());
    window.open(`https://wa.me/?text=${text}`, '_blank', 'noopener');
});

document.getElementById('share-twitter').addEventListener('click', () => {
    const text = encodeURIComponent(getShareText());
    window.open(`https://x.com/intent/tweet?text=${text}`, '_blank', 'noopener');
});

document.getElementById('share-telegram').addEventListener('click', () => {
    const text = encodeURIComponent(getShareText());
    window.open(`https://t.me/share/url?text=${text}`, '_blank', 'noopener');
});

document.getElementById('share-spotify').addEventListener('click', () => {
    const query = encodeURIComponent(`${artistEl.textContent} ${trackEl.textContent}`);
    window.open(`https://open.spotify.com/search/${query}`, '_blank', 'noopener');
});

document.getElementById('share-ytmusic').addEventListener('click', () => {
    const query = encodeURIComponent(`${artistEl.textContent} ${trackEl.textContent}`);
    window.open(`https://music.youtube.com/search?q=${query}`, '_blank', 'noopener');
});

document.getElementById('share-amazon').addEventListener('click', () => {
    const query = encodeURIComponent(`${artistEl.textContent} ${trackEl.textContent}`);
    window.open(`https://www.amazon.com/s?k=${query}&i=digital-music`, '_blank', 'noopener');
});

// ── Recently Played share buttons ────────────────────────────
/**
 * Builds a numbered text list of recently played tracks for sharing.
 * Respects the active filter and track limit, and includes rating counts
 * in plain text format (no emoji, for URL encoding compatibility).
 * @returns {string} Formatted recently played list, or empty string if no tracks.
 */
function getRecentlyPlayedText() {
    const filtered = getFilteredHistory();
    if (!filtered.length) return '';
    const lines = filtered.map((h, i) => {
        let line = `${i + 1}. ${h.title} by ${h.artist}`;
        if (h.album) line += ` (${h.album})`;
        const key = `${h.artist} - ${h.title}`;
        const r = lastSummary[key];
        if (r && (r.likes > 0 || r.dislikes > 0)) {
            line += ` [${r.likes} ${t('likes')} / ${r.dislikes} ${t('unlikes')}]`;
        }
        return line;
    });
    return `${t('recently_played')} - Radio Calico:\n${lines.join('\n')}`;
}

document.getElementById('prev-share-whatsapp').addEventListener('click', () => {
    const text = getRecentlyPlayedText();
    if (!text) return;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener');
});

document.getElementById('prev-share-twitter').addEventListener('click', () => {
    const text = getRecentlyPlayedText();
    if (!text) return;
    window.open(`https://x.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank', 'noopener');
});

// ── History filter buttons ───────────────────────────────────
document.querySelectorAll('.prev-filter').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.prev-filter').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        prevFilter = btn.dataset.filter;
        fetchMetadata(); // re-fetch from host then re-render
    });
});

document.getElementById('prev-limit').addEventListener('change', (e) => {
    historyLimit = parseInt(e.target.value, 10);
    fetchMetadata(); // re-fetch from host then re-render
});

// ── Metadata fetching ────────────────────────────────────────
let lastMetadataFetch = 0;

/**
 * Fetches track metadata from the CloudFront JSON endpoint. Schedules a
 * delayed track update (using HLS latency) so the UI changes when the
 * listener hears the new song. Also merges previous tracks into the history
 * array and fetches missing album names from iTunes.
 * @async
 */
async function fetchMetadata() {
    try {
        const res = await fetch(METADATA_URL, { cache: 'no-store' });
        if (!res.ok) return;
        const m = await res.json();
        const artist = m.artist || null;
        const title  = m.title  || null;
        const album  = m.album  || null;

        if (artist || title) {
            // Delay the UI update to match HLS stream latency so the
            // metadata change appears when the listener actually hears the
            // new song, not when CloudFront publishes it.
            const newArtist = artist || 'Radio Calico';
            const newTitle  = title  || 'Live Stream';
            const newAlbum  = album  || '';
            const newKey = `${newArtist}|${newTitle}`;

            // Only schedule if this is a different track AND not already pending
            if (newKey !== currentTrack && newKey !== pendingTrackKey) {
                // Cancel any previously scheduled update for a different track
                if (pendingTrackUpdate) clearTimeout(pendingTrackUpdate);

                pendingTrackKey = newKey;

                // Estimate delay: use HLS latency if available, else fallback ~6s
                let delaySec = LATENCY_FALLBACK_SEC;
                if (hls && typeof hls.latency === 'number' && hls.latency > 0) {
                    delaySec = Math.min(hls.latency, LATENCY_MAX_SEC);
                }

                pendingTrackUpdate = setTimeout(() => {
                    pendingTrackUpdate = null;
                    pendingTrackKey = null;
                    updateTrack(newArtist, newTitle, newAlbum);
                }, delaySec * 1000);
            }
        }

        // Build history from prev tracks in the metadata
        // The JSON only has 5 prev tracks; merge with existing history to keep older entries
        const freshTracks = [];
        for (let i = 1; i <= 5; i++) {
            const pa = m[`prev_artist_${i}`];
            const pt = m[`prev_title_${i}`];
            if (pa || pt) freshTracks.push({ artist: pa || '', title: pt || '', album: '' });
        }
        if (freshTracks.length) {
            // Merge: fresh tracks go first, then keep ALL existing entries not in fresh set
            const freshKeys = new Set(freshTracks.map(t => `${t.artist}|${t.title}`));
            const kept = history.filter(t => !freshKeys.has(`${t.artist}|${t.title}`));
            // Preserve album info from existing history for fresh tracks
            const albumMap = {};
            history.forEach(t => { if (t.album) albumMap[`${t.artist}|${t.title}`] = t.album; });
            freshTracks.forEach(t => { if (!t.album && albumMap[`${t.artist}|${t.title}`]) t.album = albumMap[`${t.artist}|${t.title}`]; });
            history.length = 0;
            freshTracks.forEach(t => history.push(t));
            kept.forEach(t => history.push(t));
            while (history.length > MAX_HISTORY) history.pop();
            renderHistory();
            // Fetch album names from iTunes for entries missing album
            history.forEach(async (t, idx) => {
                if (t.album) return;
                try {
                    const data = await fetchItunesCached(`${t.artist} ${t.title}`);
                    if (data.results && data.results.length > 0 && history[idx]) {
                        history[idx].album = data.results[0].collectionName || '';
                        renderHistory();
                    }
                } catch (e) { log.warn('album_fetch_failed', { error: e.message }); }
            });
        }

        // Show audio quality from metadata
        if (m.sample_rate || m.bit_depth) {
            const parts = [];
            if (m.bit_depth)    parts.push(`${m.bit_depth}-bit`);
            if (m.sample_rate)  parts.push(`${(m.sample_rate / 1000).toFixed(1)} kHz`);
            const srcQual = document.getElementById('source-quality');
            if (srcQual) srcQual.textContent = `Source: ${parts.join(' / ')}`;
        }
    } catch (err) { log.warn('metadata_fetch_failed', { error: err.message }); }
}

/**
 * Debounced wrapper around fetchMetadata. Ensures metadata is not fetched
 * more frequently than METADATA_DEBOUNCE_MS (3 seconds).
 */
function triggerMetadataFetch() {
    const now = Date.now();
    if (now - lastMetadataFetch < METADATA_DEBOUNCE_MS) return;
    lastMetadataFetch = now;
    fetchMetadata();
}

// ── Drawer (hamburger menu) ──────────────────────────────────
const menuBtn       = document.getElementById('menu-btn');
const drawer        = document.getElementById('drawer');
const drawerOverlay = document.getElementById('drawer-overlay');
const drawerClose   = document.getElementById('drawer-close');

/**
 * Opens the side drawer (hamburger menu) and its overlay.
 */
function openDrawer()  { drawer.classList.add('open'); drawerOverlay.classList.add('open'); }

/**
 * Closes the side drawer and its overlay.
 */
function closeDrawer() { drawer.classList.remove('open'); drawerOverlay.classList.remove('open'); }

menuBtn.addEventListener('click', openDrawer);
drawerClose.addEventListener('click', closeDrawer);
drawerOverlay.addEventListener('click', closeDrawer);

// ── Auth state ───────────────────────────────────────────────
let authToken  = localStorage.getItem('rc-token') || null;
let authUser   = localStorage.getItem('rc-user')  || null;

const drawerAuth    = document.getElementById('drawer-auth');
const drawerProfile = document.getElementById('drawer-profile');
const authForm      = document.getElementById('auth-form');
const authFeedback  = document.getElementById('auth-feedback');
const profileForm   = document.getElementById('profile-form');
const profileFb     = document.getElementById('profile-feedback');
const profileWelcome = document.getElementById('profile-welcome');

const drawerFeedback = document.getElementById('drawer-feedback');

/**
 * Switches the drawer to the authentication (login/register) view,
 * hiding the profile and feedback sections.
 */
function showAuthView() {
    drawerAuth.style.display     = '';
    drawerProfile.style.display  = 'none';
    drawerFeedback.style.display = 'none';
    authFeedback.textContent     = '';
}

/**
 * Switches the drawer to the profile view (with feedback section visible),
 * displays the logged-in username, and loads the user's profile data.
 */
function showProfileView() {
    drawerAuth.style.display     = 'none';
    drawerProfile.style.display  = '';
    drawerFeedback.style.display = '';
    profileWelcome.textContent   = `Logged in as ${authUser}`;
    loadProfile();
}

// Login
authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;
    if (!username || !password) return;
    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            authToken = data.token;
            authUser  = username;
            localStorage.setItem('rc-token', authToken);
            localStorage.setItem('rc-user', authUser);
            showProfileView();
        } else {
            authFeedback.textContent = data.error || 'Login failed';
        }
    } catch (e) { log.warn('login_failed', { error: e.message }); authFeedback.textContent = 'Could not connect'; }
});

// Register
document.getElementById('btn-register').addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;
    if (!username || !password) { authFeedback.textContent = 'Fill in both fields'; return; }
    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            authFeedback.textContent = 'Registered! You can now login.';
            authFeedback.style.color = 'var(--forest)';
        } else {
            authFeedback.textContent = data.error || 'Registration failed';
            authFeedback.style.color = '#c0392b';
        }
    } catch (err) {
        log.error('register_failed', { error: err.message });
        authFeedback.textContent = 'Could not connect to server';
    }
});

// Logout
document.getElementById('btn-logout').addEventListener('click', () => {
    if (authToken) {
        fetch('/api/logout', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` } })
            .catch(e => log.warn('logout_failed', { error: e.message }));
    }
    authToken = null;
    authUser  = null;
    localStorage.removeItem('rc-token');
    localStorage.removeItem('rc-user');
    document.getElementById('auth-username').value = '';
    document.getElementById('auth-password').value = '';
    showAuthView();
});

// Load profile
/**
 * Fetches the authenticated user's profile from the API and populates
 * the profile form fields (nickname, email, about, genre checkboxes).
 * Reverts to auth view on 401 (expired/invalid token).
 * @async
 */
async function loadProfile() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/profile', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) {
            if (res.status === 401) { showAuthView(); return; }
            return;
        }
        const p = await res.json();
        document.getElementById('profile-nickname').value = p.nickname || '';
        document.getElementById('profile-email').value    = p.email || '';
        document.getElementById('profile-about').value    = p.about || '';
        // Set genre checkboxes
        const genres = (p.genres || '').split(',').map(g => g.trim()).filter(Boolean);
        document.querySelectorAll('#genre-grid input[type="checkbox"]').forEach(cb => {
            cb.checked = genres.includes(cb.value);
        });
    } catch (e) { log.warn('profile_load_failed', { error: e.message }); }
}

// Save profile
profileForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!authToken) return;
    const genres = [];
    document.querySelectorAll('#genre-grid input[type="checkbox"]:checked').forEach(cb => {
        genres.push(cb.value);
    });
    const body = {
        nickname: document.getElementById('profile-nickname').value.trim(),
        email:    document.getElementById('profile-email').value.trim(),
        genres:   genres.join(','),
        about:    document.getElementById('profile-about').value.trim()
    };
    try {
        const res = await fetch('/api/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(body)
        });
        if (res.ok) {
            profileFb.textContent = 'Profile saved!';
            profileFb.style.color = 'var(--forest)';
        } else {
            const data = await res.json();
            profileFb.textContent = data.error || 'Could not save';
            profileFb.style.color = '#c0392b';
        }
    } catch (e) { log.warn('profile_save_failed', { error: e.message }); profileFb.textContent = 'Could not connect'; }
});

// Feedback form (requires login)
document.getElementById('feedback-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const feedbackFb = document.getElementById('feedback-feedback');
    const message = document.getElementById('feedback-message').value.trim();
    if (!message) { feedbackFb.textContent = 'Please write a message'; feedbackFb.style.color = '#c0392b'; return; }
    if (!authToken) { feedbackFb.textContent = 'Please login first'; feedbackFb.style.color = '#c0392b'; return; }
    try {
        const res = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ message })
        });
        if (res.ok) {
            feedbackFb.textContent = 'Feedback sent! Thank you!';
            feedbackFb.style.color = 'var(--forest)';
            document.getElementById('feedback-message').value = '';
        } else {
            const data = await res.json();
            feedbackFb.textContent = data.error || 'Could not send feedback';
            feedbackFb.style.color = '#c0392b';
        }
    } catch (e) { log.warn('feedback_submit_failed', { error: e.message }); feedbackFb.textContent = 'Could not connect'; feedbackFb.style.color = '#c0392b'; }
});

// Feedback on Twitter
document.getElementById('feedback-twitter').addEventListener('click', () => {
    const msg = document.getElementById('feedback-message').value.trim();
    const text = encodeURIComponent(msg ? `Hey @RadioCalico, ${msg}` : 'Hey @RadioCalico, here\'s my feedback: ');
    window.open(`https://x.com/intent/tweet?text=${text}`, '_blank', 'noopener');
});

document.getElementById('feedback-telegram').addEventListener('click', () => {
    const msg = document.getElementById('feedback-message').value.trim();
    const text = encodeURIComponent(msg ? `Radio Calico feedback: ${msg}` : 'Radio Calico feedback: ');
    window.open(`https://t.me/share/url?text=${text}`, '_blank', 'noopener');
});

// Restore session on load
if (authToken && authUser) {
    showProfileView();
} else {
    showAuthView();
}

// ── Boot ──────────────────────────────────────────────────────
setupMetadataTextTracks();
fetchMetadata(); // one-time fetch so UI shows current track before playing

// ── Theme toggle ──────────────────────────────────────────────
const settingsBtn = document.getElementById('settings-btn');
const settingsDropdown = document.getElementById('settings-dropdown');

settingsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    settingsDropdown.classList.toggle('open');
});

document.addEventListener('click', (e) => {
    if (!settingsDropdown.contains(e.target)) {
        settingsDropdown.classList.remove('open');
    }
});

/**
 * Applies the given theme by setting the data-theme attribute on the document
 * element, persisting the choice to localStorage, and checking the matching radio button.
 * @param {string} theme - The theme to apply: 'light' or 'dark'.
 */
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('rc-theme', theme);
    const radio = document.querySelector(`input[name="theme"][value="${theme}"]`);
    if (radio) radio.checked = true;
}

document.querySelectorAll('input[name="theme"]').forEach(radio => {
    radio.addEventListener('change', (e) => applyTheme(e.target.value));
});

// Restore saved theme
const savedTheme = localStorage.getItem('rc-theme') || 'dark';
applyTheme(savedTheme);

// ── Stream quality toggle ─────────────────────────────────────
/**
 * Updates the stream quality label in the UI to reflect the current selection.
 */
function updateStreamQualityDisplay() {
    const el = document.getElementById('stream-quality');
    if (el) el.textContent = `${t('stream_quality')}: ${STREAM_LABELS[currentStreamQuality]}`;
}

/**
 * Switches the stream to the specified audio quality. Persists the choice,
 * reinitializes the HLS player with the new level, and resumes playback
 * if the stream was already playing.
 * @param {string} quality - The quality key: 'flac' or 'aac'.
 */
function applyStreamQuality(quality) {
    if (quality === currentStreamQuality) return;
    currentStreamQuality = quality;
    localStorage.setItem('rc-stream-quality', quality);
    updateStreamQualityDisplay();
    const wasPlaying = playing;
    if (Hls.isSupported()) {
        initHls();
        if (wasPlaying) {
            audio.play().catch(() => { playing = false; showPlayIcon('play'); });
        }
    } else if (audio.canPlayType('application/vnd.apple.mpegurl')) {
        audio.src = STREAM_URL;
        if (wasPlaying) audio.play();
    }
}

document.querySelectorAll('input[name="stream-quality"]').forEach(radio => {
    radio.addEventListener('change', (e) => applyStreamQuality(e.target.value));
});

// Restore saved stream quality
const sqRadio = document.querySelector(`input[name="stream-quality"][value="${currentStreamQuality}"]`);
if (sqRadio) sqRadio.checked = true;
updateStreamQualityDisplay();

// Language selector
document.querySelectorAll('input[name="language"]').forEach(radio => {
    radio.addEventListener('change', (e) => applyLanguage(e.target.value));
});
applyLanguage(currentLang);

if (Hls.isSupported()) {
    initHls();
} else if (audio.canPlayType('application/vnd.apple.mpegurl')) {
    // Safari native HLS — metadata comes via text tracks
    audio.src = STREAM_URL;
    audio.addEventListener('loadedmetadata', () => {
        playBtn.disabled = false;
        showPlayIcon('play');
    });
} else {
    playBtn.disabled = true;
    barTime.textContent = 'HLS not supported';
}

// ── Retro Radio Buttons (Song Info) ─────────────────────────
const retroButtons = document.querySelectorAll('.retro-btn');
const infoPanel = document.getElementById('info-panel');
const infoPanelContent = document.getElementById('info-panel-content');
let activeQuery = null;

/**
 * Synthesize a mechanical click sound using the Web Audio API.
 * No external audio file needed — generates a short percussive "click".
 */
function playMechanicalClick() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        // Short noise burst for the "click"
        const bufferSize = ctx.sampleRate * 0.03; // 30ms
        const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            // Decaying white noise
            data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / bufferSize, 8);
        }

        const source = ctx.createBufferSource();
        source.buffer = buffer;

        // Band-pass filter for that mechanical feel
        const filter = ctx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.value = 2500;
        filter.Q.value = 1.2;

        const gain = ctx.createGain();
        gain.gain.value = 0.4;

        source.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);
        source.start();

        // Cleanup
        source.onended = () => ctx.close();
    } catch (e) {
        // Web Audio API not available — silent fallback
    }
}

/**
 * Convert a basic Markdown string to safe HTML.
 * Handles headings, bold, italic, code blocks, tables, lists, and links.
 */
function markdownToHtml(md) {
    if (!md) return '';
    let html = escHtml(md);

    // Code blocks (``` ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Headings (h6 → h1, longest prefix first)
    html = html.replace(/^###### (.+)$/gm, '<h6>$1</h6>');
    html = html.replace(/^##### (.+)$/gm, '<h5>$1</h5>');
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Bold + italic
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Tables
    html = html.replace(/^\|(.+)\|$/gm, (match) => {
        const cells = match.split('|').filter(c => c.trim());
        if (cells.every(c => /^[\s-:]+$/.test(c))) return ''; // separator row
        const tag = 'td';
        return '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
    });
    html = html.replace(/(<tr>[\s\S]*?<\/tr>)/g, (block) => {
        if (!block.includes('<table>')) return '<table>' + block + '</table>';
        return block;
    });
    // Unordered lists
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    // Clean up nested <ul>
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = '<p>' + html + '</p>';
    // Clean empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');

    return html;
}

/**
 * Build a share-buttons row for the info panel results.
 * Truncates content to fit URL limits (~500 chars preview).
 */
// Module-level: store raw content for per-platform share text generation
let _infoShareMeta = { label: '', track: '', artist: '', content: '' };

function _buildShareText(maxChars) {
    const { label, track, artist, content } = _infoShareMeta;
    const cleaned = content
        .replace(/#{1,6}\s/g, '')
        .replace(/\*\*/g, '')
        .replace(/\*/g, '')
        .replace(/`/g, '')
        .replace(/\|/g, ' ')
        .replace(/\n+/g, '\n');
    const header = `${label} — "${track}" by ${artist} (${t('via_ai')})\n\n`;
    const available = maxChars - header.length - 3; // 3 for "..."
    const preview = cleaned.substring(0, Math.max(available, 100));
    return header + preview + (cleaned.length > available ? '...' : '');
}

function buildInfoShareRow(queryType, artist, track, content) {
    const label = { lyrics: 'Lyrics', details: 'Details', facts: 'Facts', merchandise: 'Merchandise', jokes: 'Jokes', everything: 'Everything', quiz: 'Quiz' }[queryType] || queryType;
    _infoShareMeta = { label, track, artist, content };

    return '<div class="info-share-row" id="info-share-row">'
        + '<span class="share-label">' + t('share') + '</span>'
        + '<button class="share-btn share-whatsapp" data-platform="whatsapp" title="Share on WhatsApp" aria-label="Share on WhatsApp">'
        + '<svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>'
        + '</button>'
        + '<button class="share-btn share-twitter" data-platform="twitter" title="Share on X" aria-label="Share on X">'
        + '<svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'
        + '</button>'
        + '<button class="share-btn share-telegram" data-platform="telegram" title="Share on Telegram" aria-label="Share on Telegram">'
        + '<svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.492-1.302.48-.428-.013-1.252-.242-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>'
        + '</button>'
        + '</div>';
}

/**
 * Attach click listeners to info-panel share buttons (CSP-safe, no inline onclick).
 * Call this after inserting buildInfoShareRow HTML into the DOM.
 */
function wireInfoShareButtons() {
    const row = document.getElementById('info-share-row');
    if (!row) return;
    // Per-platform char limits: X=280, WhatsApp~4000, Telegram~4096
    const limits = { whatsapp: 4000, twitter: 280, telegram: 4000 };
    row.querySelectorAll('.share-btn[data-platform]').forEach(btn => {
        const platform = btn.dataset.platform;
        btn.addEventListener('click', () => {
            const text = _buildShareText(limits[platform] || 2000);
            const encoded = encodeURIComponent(text);
            const urls = {
                whatsapp: 'https://wa.me/?text=' + encoded,
                twitter: 'https://x.com/intent/tweet?text=' + encoded,
                telegram: 'https://t.me/share/url?text=' + encoded,
            };
            if (urls[platform]) {
                window.open(urls[platform], '_blank', 'noopener');
            }
        });
    });
}

/**
 * Handle retro button press — toggle, exclusive selection, fetch song info.
 */
function handleRetroButton(btn) {
    const queryType = btn.dataset.query;
    playMechanicalClick();

    // If same button pressed again — release it
    if (activeQuery === queryType) {
        btn.classList.remove('pressed');
        btn.setAttribute('aria-pressed', 'false');
        infoPanel.classList.remove('open');
        activeQuery = null;
        return;
    }

    // Release all other buttons
    retroButtons.forEach(b => {
        b.classList.remove('pressed');
        b.setAttribute('aria-pressed', 'false');
    });

    // Press this button
    btn.classList.add('pressed');
    btn.setAttribute('aria-pressed', 'true');
    activeQuery = queryType;

    // Quiz gets its own handler
    if (queryType === 'quiz') {
        startQuiz();
        return;
    }

    // Get current track info
    const artist = artistEl ? artistEl.textContent : '';
    const track = trackEl ? trackEl.textContent : '';
    const album = albumEl ? albumEl.textContent : '';
    const artworkImg = artworkEl ? artworkEl.querySelector('img') : null;
    const artworkUrl = artworkImg ? artworkImg.src : '';

    if (!artist || artist === 'Radio Calico' || !track || track === 'Live Stream') {
        infoPanelContent.innerHTML = '<p style="text-align:center;color:#888">' + t('no_track') + '</p>';
        infoPanel.classList.add('open');
        return;
    }

    // Show loading state
    infoPanelContent.innerHTML = '<div class="info-panel-loading"><span class="spinner"></span>' + t('loading_ai') + '</div>';
    infoPanel.classList.add('open');

    // Call the API
    fetch('/api/song-info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            query_type: queryType,
            artist: artist,
            track: track,
            album: album,
            artwork_url: artworkUrl,
            language: _LANG_TO_LLM[currentLang] || 'English',
        }),
    })
    .then(r => r.json())
    .then(data => {
        if (activeQuery !== queryType) return; // user switched buttons
        if (data.ok) {
            infoPanelContent.innerHTML = '<div class="info-panel-content">' + markdownToHtml(data.content) + '</div>'
                + buildInfoShareRow(queryType, artist, track, data.content);
            wireInfoShareButtons();
        } else {
            infoPanelContent.innerHTML = '<p style="text-align:center;color:#c0392b">' +
                escHtml(data.error || 'Failed to get song info. Is Ollama running?') + '</p>';
        }
    })
    .catch(err => {
        if (activeQuery !== queryType) return;
        infoPanelContent.innerHTML = '<p style="text-align:center;color:#c0392b">' + t('network_error') + '</p>';
        log.error('song_info_fetch_error', { error: err.message });
    });
}

// ── Quiz Interactive Game ────────────────────────────────────
let quizState = null; // { questions, current, scores, total }

function startQuiz() {
    const artist = artistEl ? artistEl.textContent : '';
    const track = trackEl ? trackEl.textContent : '';
    const album = albumEl ? albumEl.textContent : '';

    if (!artist || artist === 'Radio Calico' || !track || track === 'Live Stream') {
        infoPanelContent.innerHTML = '<p style="text-align:center;color:#888">' + t('no_track') + '</p>';
        infoPanel.classList.add('open');
        return;
    }

    infoPanelContent.innerHTML = '<div class="info-panel-loading"><span class="spinner"></span>' + t('loading_quiz') + '</div>';
    infoPanel.classList.add('open');

    fetch('/api/quiz/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artist, track, album, language: _LANG_TO_LLM[currentLang] || 'English' }),
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok || !data.questions || data.questions.length === 0) {
            infoPanelContent.innerHTML = '<p style="text-align:center;color:#c0392b">' +
                escHtml(data.error || 'Could not generate quiz. Is Ollama running?') + '</p>';
            return;
        }
        quizState = { questions: data.questions, current: 0, scores: [], total: 0 };
        renderQuizQuestion();
    })
    .catch(() => {
        infoPanelContent.innerHTML = '<p style="text-align:center;color:#c0392b">Network error. Check that the server and Ollama are running.</p>';
    });
}

function renderQuizQuestion() {
    if (!quizState) return;
    const q = quizState.questions[quizState.current];
    const num = quizState.current + 1;

    let html = '<div class="quiz-chat" id="quiz-chat">';
    // Show previous exchanges
    for (let i = 0; i < quizState.scores.length; i++) {
        const prev = quizState.questions[i];
        const sc = quizState.scores[i];
        html += `<div class="quiz-bubble system"><strong>Q${i + 1}:</strong> ${escHtml(prev.q)}<br>${prev.options.map(o => escHtml(o)).join('<br>')}</div>`;
        html += `<div class="quiz-bubble user">${escHtml(sc.userAnswer)}</div>`;
        html += `<div class="quiz-bubble system"><strong>${sc.score > 0 ? '+' : ''}${sc.score} pts</strong> — ${escHtml(sc.reaction)}</div>`;
    }
    // Current question
    html += `<div class="quiz-bubble system"><strong>Q${num}/5:</strong> ${escHtml(q.q)}<br><br>${q.options.map(o => escHtml(o)).join('<br>')}</div>`;
    html += '</div>';
    html += '<div class="quiz-input-row"><input type="text" class="quiz-input" id="quiz-answer" placeholder="' + t('quiz_your_answer') + ' (A, B, C, D)..." autofocus>';
    html += '<button class="quiz-send-btn" id="quiz-send">' + t('quiz_send') + '</button></div>';

    infoPanelContent.innerHTML = html;

    // Scroll chat to bottom
    const chat = document.getElementById('quiz-chat');
    if (chat) chat.scrollTop = chat.scrollHeight;

    // Wire up send
    const sendBtn = document.getElementById('quiz-send');
    const input = document.getElementById('quiz-answer');
    const submit = () => submitQuizAnswer(input.value);
    sendBtn.addEventListener('click', submit);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });
    input.focus();
}

function submitQuizAnswer(answer) {
    if (!quizState || !answer.trim()) return;
    const q = quizState.questions[quizState.current];

    // Disable input
    const sendBtn = document.getElementById('quiz-send');
    const input = document.getElementById('quiz-answer');
    if (sendBtn) sendBtn.disabled = true;
    if (input) input.disabled = true;

    // Show user bubble immediately
    const chat = document.getElementById('quiz-chat');
    if (chat) {
        chat.innerHTML += `<div class="quiz-bubble user">${escHtml(answer)}</div>`;
        chat.innerHTML += '<div class="quiz-bubble system"><em>Evaluating&hellip;</em></div>';
        chat.scrollTop = chat.scrollHeight;
    }

    fetch('/api/quiz/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            question: q.q,
            correct: q.answer,
            user_answer: answer.trim(),
            options: q.options,
        }),
    })
    .then(r => r.json())
    .then(data => {
        const score = data.score || 0;
        const reaction = data.reaction || (score > 0 ? 'Not bad!' : 'Ouch!');

        quizState.scores.push({ userAnswer: answer.trim(), score, reaction });
        quizState.total += score;
        quizState.current++;

        if (quizState.current >= 5) {
            renderQuizSummary();
        } else {
            renderQuizQuestion();
        }
    })
    .catch(() => {
        quizState.scores.push({ userAnswer: answer.trim(), score: 0, reaction: 'I crashed. Let\'s call this one a draw.' });
        quizState.current++;
        if (quizState.current >= 5) renderQuizSummary();
        else renderQuizQuestion();
    });
}

function renderQuizSummary() {
    if (!quizState) return;
    const total = quizState.total;
    const max = 25;
    let emoji, verdict;
    if (total >= 20) { emoji = '🏆'; verdict = 'You are a LEGEND! Are you the artist themselves?!'; }
    else if (total >= 12) { emoji = '🎸'; verdict = 'Rock solid! You clearly know your stuff.'; }
    else if (total >= 5) { emoji = '🎵'; verdict = 'Not bad! You\'ve got some music cred.'; }
    else if (total >= 0) { emoji = '🤷'; verdict = 'Meh. Maybe stick to listening, not trivia.'; }
    else { emoji = '💀'; verdict = 'Impressively wrong. That takes talent, honestly.'; }

    let html = '<div class="quiz-chat" id="quiz-chat">';
    for (let i = 0; i < quizState.scores.length; i++) {
        const q = quizState.questions[i];
        const sc = quizState.scores[i];
        html += `<div class="quiz-bubble system"><strong>Q${i + 1}:</strong> ${escHtml(q.q)}</div>`;
        html += `<div class="quiz-bubble user">${escHtml(sc.userAnswer)}</div>`;
        html += `<div class="quiz-bubble system"><strong>${sc.score > 0 ? '+' : ''}${sc.score}</strong> — ${escHtml(sc.reaction)}</div>`;
    }
    html += '</div>';
    html += `<div class="quiz-score">${emoji} Final Score: ${total} / ${max} — ${verdict}</div>`;

    // Share quiz results
    const artist = artistEl ? artistEl.textContent : '';
    const track = trackEl ? trackEl.textContent : '';
    const quizShareText = `${emoji} ${t('scored_quiz')} ${total}/${max} ${t('on_quiz')} "${track}" by ${artist}! ${verdict}`;
    html += buildInfoShareRow('quiz', artist, track, quizShareText);

    infoPanelContent.innerHTML = html;
    wireInfoShareButtons();

    const chat = document.getElementById('quiz-chat');
    if (chat) chat.scrollTop = chat.scrollHeight;
}

retroButtons.forEach(btn => {
    btn.addEventListener('click', () => handleRetroButton(btn));
});

// ── Test exports (Node.js only) ──────────────────────────────
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        log, fetchItunesCached, escHtml, formatTime, parseID3Frames, getFilteredHistory, markdownToHtml, buildInfoShareRow, handleRetroButton, playMechanicalClick, applyLanguage, t, _TRANSLATIONS,
        getShareText, getRecentlyPlayedText, getArtworkUrl,
        showPlayIcon, updateTrack, pushHistory, renderHistory,
        fetchArtwork, handleMetadataFields, togglePlay,
        fetchTrackRatings, checkIfRated, updateRatingUI, submitRating,
        fetchMetadata, triggerMetadataFetch, applyTheme,
        updateStreamQualityDisplay, applyStreamQuality,
        openDrawer, closeDrawer, showAuthView, showProfileView, loadProfile,
        // Expose state for testing
        get history() { return history; },
        get currentTrack() { return currentTrack; },
        set currentTrack(v) { currentTrack = v; },
        get playing() { return playing; },
        set playing(v) { playing = v; },
        get lastSummary() { return lastSummary; },
        set lastSummary(v) { lastSummary = v; },
        get prevFilter() { return prevFilter; },
        set prevFilter(v) { prevFilter = v; },
        get historyLimit() { return historyLimit; },
        set historyLimit(v) { historyLimit = v; },
        get currentStreamQuality() { return currentStreamQuality; },
        set currentStreamQuality(v) { currentStreamQuality = v; },
        STREAM_LABELS, METADATA_DEBOUNCE_MS, MAX_HISTORY,
    };
}
