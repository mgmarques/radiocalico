# Player.js Architecture

## Metadata Lifecycle

- **Not timer-based** — metadata fetches are triggered by HLS.js `FRAG_CHANGED` event
- `triggerMetadataFetch()` debounces calls (3s minimum interval via `METADATA_DEBOUNCE_MS`)
- One initial `fetchMetadata()` at boot so UI shows current track before playing
- Filter buttons and dropdown also trigger `fetchMetadata()` for fresh data

## History Accumulation

- CloudFront JSON only provides 5 previous tracks (`prev_artist_1` through `prev_artist_5`)
- History array accumulates up to 20 entries over time (merges fresh + older, deduped)
- Album names fetched from iTunes API for entries missing album info
- `renderHistory()` slices to `historyLimit` for display (dropdown: 5/10/15/20)

## Time Display

- Uses wall-clock time: `Date.now() - songStartTime` (not `audio.currentTime` which is HLS buffer position)
- Total duration from iTunes `trackTimeMillis`
- Format: `elapsed / total` or `elapsed / Live` if no duration

## Rating System

- IP-based deduplication (server-side unique constraint on `station + ip`)
- `station` key = `"Artist - Title"` string
- Frontend checks `/api/ratings/check` on track change, disables buttons if already rated
- Ratings summary shown as badges in Recently Played list

## Metadata Latency Compensation

- CloudFront metadata JSON updates **before** the HLS stream delivers the new song audio
- `fetchMetadata()` schedules track updates via `setTimeout` using `hls.latency` (fallback 6s)
- `pendingTrackKey` prevents repeated fetches from resetting the timer for the same track
- The delay ensures the UI (artist, title, artwork) changes when the listener actually hears the new song

## Dark/Light Theme

- Settings gear icon in navbar top-right opens a dropdown with Light / Dark (default) theme radio buttons and Stream Quality (FLAC / AAC) radio buttons
- Theme applied via `data-theme="dark"` attribute on `<html>`
- Dark mode overrides CSS custom properties (`--mint`, `--forest`, `--teal`, etc.)
- User choice persisted in `localStorage` key `rc-theme`

## Hamburger Menu & Side Drawer

- Hamburger icon (top-left navbar) opens a slide-out drawer from the left
- **Login/Register section**: username + password form
- **Profile section** (shown when logged in): nickname, email, 16 genre tags, "About You"
- **Feedback section** (shown when logged in): message textarea + X/Twitter + Telegram
- Auth state stored in `localStorage`: `rc-token`, `rc-user`

## Social Share & Music Search Buttons

- **Now Playing**: WhatsApp, X/Twitter, Telegram share + Spotify, YouTube Music, Amazon Music search
- **Recently Played**: WhatsApp, X/Twitter share of numbered track list
- Ratings shown as plain text `[N likes / N unlikes]` in shared messages (emoji break in URL encoding)
- All links open via `window.open(..., '_blank', 'noopener')`

## Sticky Navbar & Footer

- Navbar (`position: sticky; top: 0`), Footer (`position: sticky; bottom: 0`)
- Global zoom: `html { zoom: 0.85; }` scales all UI to 85%