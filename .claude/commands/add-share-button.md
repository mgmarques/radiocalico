---
name: add-share-button
description: Add a new share/search button to the player
---
Add a new share/search button to the Radio Calico player.

The user will specify a platform name. Follow this pattern used by existing buttons:

1. **HTML** (`static/index.html`): Add a `<button class="share-btn share-{name}" id="share-{name}">` with an SVG icon inside the `.share-row` div
2. **CSS** (`static/css/player.css`): Add `.share-{name} { color: #BRAND_COLOR; }` and hover style in the Share Row section
3. **JS** (`static/js/player.js`): Add a click listener that builds a query from `artistEl.textContent` and `trackEl.textContent`, then opens the platform URL via `window.open(url, '_blank', 'noopener')`

For social sharing platforms, use `getShareText()` for the message.
For music search platforms, use `encodeURIComponent(artist + " " + title)` as the search query.

Existing platforms for reference:
- WhatsApp: `https://wa.me/?text={text}`
- X/Twitter: `https://x.com/intent/tweet?text={text}`
- Telegram: `https://t.me/share/url?text={text}`
- Spotify: `https://open.spotify.com/search/{query}`
- YouTube Music: `https://music.youtube.com/search?q={query}`
- Amazon Music: `https://www.amazon.com/s?k={query}&i=digital-music`

NOTE: Shazam and Amazon Music web app search URLs do NOT work (SPAs). Facebook sharer doesn't support plain text sharing. Avoid these platforms.

IMPORTANT: Emoji characters get corrupted in URL-encoded share text (especially WhatsApp). Use plain text labels for ratings/badges in shared messages.

There are TWO share rows:

- **Now Playing** (`.share-row` in `.info-col`): shares current track (social + music search)
- **Recently Played** (`.prev-share-row` in `.recently-played-widget`): shares filtered track list (social only: WhatsApp, X)

Remind the user to Cmd+Shift+R after changes.
