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
function showPlayIcon(name) {
    iconPlay.style.display  = name === 'play'    ? '' : 'none';
    iconPause.style.display = name === 'pause'   ? '' : 'none';
    iconSpin.style.display  = name === 'spinner' ? '' : 'none';
}

// ── Artwork ──────────────────────────────────────────────────
async function fetchArtwork(artist, title) {
    try {
        const q = encodeURIComponent(`${artist} ${title}`);
        const res = await fetch(`https://itunes.apple.com/search?term=${q}&entity=song&limit=1`);
        const data = await res.json();
        if (data.results && data.results.length > 0) {
            const result = data.results[0];
            // Replace 100x100 thumbnail with 600x600
            const url = result.artworkUrl100.replace('100x100', ARTWORK_SIZE);
            artworkEl.innerHTML = `<img src="${escHtml(url)}" alt="${escHtml(title)}">`;
            // Store track duration from iTunes (milliseconds → seconds)
            trackDuration = result.trackTimeMillis ? result.trackTimeMillis / 1000 : null;
        } else {
            artworkEl.innerHTML = `<div class="artwork-placeholder">♪</div>`;
            trackDuration = null;
        }
    } catch (e) {
        console.warn('Artwork fetch failed:', e);
        artworkEl.innerHTML = `<div class="artwork-placeholder">♪</div>`;
        trackDuration = null;
    }
}

// ── Track metadata ──────────────────────────────────────────
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

function pushHistory(artist, title, album) {
    if (!artist && !title) return;
    history.unshift({ artist, title, album: album || '' });
    while (history.length > MAX_HISTORY) history.pop(); // keep up to max dropdown value
    renderHistory();
}

let prevFilter = 'all'; // 'all', 'up', 'down'
let historyLimit = 5;
let lastSummary = {};

async function renderHistory() {
    if (!history.length) {
        prevList.innerHTML = '<li class="prev-empty">No tracks yet</li>';
        return;
    }

    // Fetch ratings summary, fall back to cached
    try {
        const res = await fetch('/api/ratings/summary');
        if (res.ok) lastSummary = await res.json();
    } catch (e) { console.warn('Ratings summary fetch failed:', e); }

    const filtered = getFilteredHistory();

    if (!filtered.length) {
        prevList.innerHTML = '<li class="prev-empty">No matching tracks</li>';
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

function escHtml(str) {
    return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function getFilteredHistory() {
    return history.slice(0, historyLimit).filter(h => {
        if (prevFilter === 'all') return true;
        const key = `${h.artist} - ${h.title}`;
        const r = lastSummary[key];
        if (!r) return false;
        if (prevFilter === 'up') return r.likes > 0;
        if (prevFilter === 'down') return r.dislikes > 0;
        return true;
    });
}

// ── ID3 parser (decodes text frames from raw ID3v2 bytes) ───
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
            let txt = '';
            if (enc === 3)      txt = new TextDecoder('utf-8').decode(body);
            else if (enc === 1) txt = new TextDecoder('utf-16').decode(body);
            else if (enc === 2) txt = new TextDecoder('utf-16be').decode(body);
            else                txt = new TextDecoder('iso-8859-1').decode(body);
            txt = txt.replace(/\0/g, '').trim();
            if (txt) frames[id] = txt;
        }
        off += 10 + sz;
    }
    return frames;
}

// ── Process parsed metadata fields ──────────────────────────
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
async function fetchTrackRatings(station) {
    try {
        const res = await fetch('/api/ratings/summary');
        if (!res.ok) return;
        const summary = await res.json();
        const r = summary[station];
        rateUpCount.textContent   = r ? r.likes : 0;
        rateDownCount.textContent = r ? r.dislikes : 0;
    } catch (e) { console.warn('Track ratings fetch failed:', e); }
}

async function checkIfRated(station) {
    try {
        const res = await fetch(`/api/ratings/check?station=${encodeURIComponent(station)}`);
        if (!res.ok) return false;
        const data = await res.json();
        return data.rated;
    } catch (e) { console.warn('Rating check failed:', e); return false; }
}

async function updateRatingUI() {
    const station = `${artistEl.textContent} - ${trackEl.textContent}`;
    const alreadyRated = await checkIfRated(station);
    rateUp.classList.toggle('rated', alreadyRated);
    rateDown.classList.toggle('rated', alreadyRated);
    rateFb.textContent = alreadyRated ? 'You rated this track' : '';
    fetchTrackRatings(station);
}

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
        console.warn('Rating submit failed:', e);
        rateFb.textContent = 'Could not send rating';
    }
}

rateUp.addEventListener('click',   () => submitRating(1));
rateDown.addEventListener('click', () => submitRating(0));
playBtn.addEventListener('click', togglePlay);

// ── Share buttons ────────────────────────────────────────────
function getArtworkUrl() {
    const img = artworkEl.querySelector('img');
    if (!img) return '';
    // Use a smaller size (300x300) for better sharing previews
    return img.src.replace(ARTWORK_SIZE, SHARE_ARTWORK_SIZE);
}

function getShareText() {
    const artist = artistEl.textContent;
    const title  = trackEl.textContent;
    const album  = albumEl.textContent;
    const artUrl = getArtworkUrl();
    let text = `Listening to "${title}" by ${artist}`;
    if (album) text += ` (${album})`;
    text += ' on Radio Calico!';
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
function getRecentlyPlayedText() {
    const filtered = getFilteredHistory();
    if (!filtered.length) return '';
    const lines = filtered.map((h, i) => {
        let line = `${i + 1}. ${h.title} by ${h.artist}`;
        if (h.album) line += ` (${h.album})`;
        const key = `${h.artist} - ${h.title}`;
        const r = lastSummary[key];
        if (r && (r.likes > 0 || r.dislikes > 0)) {
            line += ` [${r.likes} likes / ${r.dislikes} unlikes]`;
        }
        return line;
    });
    return `Recently Played on Radio Calico:\n${lines.join('\n')}`;
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
                    const q = encodeURIComponent(`${t.artist} ${t.title}`);
                    const res = await fetch(`https://itunes.apple.com/search?term=${q}&entity=song&limit=1`);
                    const data = await res.json();
                    if (data.results && data.results.length > 0 && history[idx]) {
                        history[idx].album = data.results[0].collectionName || '';
                        renderHistory();
                    }
                } catch (e) { console.warn('Album fetch failed:', e); }
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
    } catch (err) { console.warn('Metadata fetch failed:', err); }
}

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

function openDrawer()  { drawer.classList.add('open'); drawerOverlay.classList.add('open'); }
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

function showAuthView() {
    drawerAuth.style.display     = '';
    drawerProfile.style.display  = 'none';
    drawerFeedback.style.display = 'none';
    authFeedback.textContent     = '';
}

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
    } catch (e) { console.warn('Login failed:', e); authFeedback.textContent = 'Could not connect'; }
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
        console.error('Register error:', err);
        authFeedback.textContent = 'Could not connect to server';
    }
});

// Logout
document.getElementById('btn-logout').addEventListener('click', () => {
    authToken = null;
    authUser  = null;
    localStorage.removeItem('rc-token');
    localStorage.removeItem('rc-user');
    document.getElementById('auth-username').value = '';
    document.getElementById('auth-password').value = '';
    showAuthView();
});

// Load profile
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
    } catch (e) { console.warn('Profile load failed:', e); }
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
    } catch (e) { console.warn('Profile save failed:', e); profileFb.textContent = 'Could not connect'; }
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
    } catch (e) { console.warn('Feedback submit failed:', e); feedbackFb.textContent = 'Could not connect'; feedbackFb.style.color = '#c0392b'; }
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
function updateStreamQualityDisplay() {
    const el = document.getElementById('stream-quality');
    if (el) el.textContent = `Stream quality: ${STREAM_LABELS[currentStreamQuality]}`;
}

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
