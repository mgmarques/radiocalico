# Style Guide & Code Conventions

## CSS Design Tokens

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--mint` | `#D8F2D5` | `#1a3a1c` | Backgrounds, accents |
| `--forest` | `#1F4E23` | `#7ecf84` | Primary buttons, headings |
| `--teal` | `#38A29D` | `#245e5b` | Navbar, footer, hover states |
| `--orange` | `#EFA63C` | `#EFA63C` | Call-to-action |
| `--charcoal` | `#231F20` | `#e0e0e0` | Body text, player bar |

- Breakpoint: 700px (single column below)
- Max width: 1200px, 24px gutters, 8px baseline grid
- Global zoom: 85% (`html { zoom: 0.85 }`)
- Typography: Montserrat (headings), Open Sans (body)

## Code Conventions

- **No frameworks** — vanilla JS, no build step, no bundler
- **HTML escaping**: Always use `escHtml()` when inserting text into DOM via innerHTML
- **Backend**: Pure Flask with PyMySQL. No ORM. Parameterized queries for SQL
- **Auth**: Token-based. `localStorage` keys `rc-token`, `rc-user`. `Authorization: Bearer <token>`
- **Logging**: Python `logger.info/warning/error()` with structured JSON. JS `log.info/warn/error(message, context)`. Business events use descriptive names: `user_registered`, `rating_created`
- **Linting**: `make lint` must pass before committing. `make fix-py` auto-fixes Python
- **Testing**: All new API routes need tests in `test_app.py`. New JS functions need tests in `player.test.js`

## Retro Radio Buttons

- 7 vintage-styled 3D buttons: Lyrics, Details, Interesting Facts, Merchandise, Jokes, Everything About, Quiz
- Per-button color gradients (warm earth tones — beige, cream, gold, red, teal, olive, crimson)
- Pressed state: `translateY(3px)` + inverted gradient + `color: var(--orange)`
- Dark mode: `filter: brightness()` adjustments
- Single row: `flex-wrap: nowrap` with `overflow-x: auto` on mobile
- Quiz button: circular, crimson, fixed label "Quiz" (never translated)

## Info Panel

- Expanding panel below retro buttons: `display: none` → `display: block` on `.open`
- Max height: `60vh` with `overflow-y: auto` (scrollable, never hides behind Recently Played)
- Content rendered from LLM Markdown → HTML via `markdownToHtml()`
- Share row at bottom: WhatsApp (4000 chars), X (280 chars), Telegram (4000 chars)
- Quiz chat: bubble-style messages, user answers right-aligned (teal), AI responses left-aligned

## i18n

- 3 languages: English (default), Brazilian Portuguese (`pt-BR`), Spanish (`es`)
- Translate UI labels via `data-i18n` attributes + `t(key)` helper
- **Never translate**: song titles, artist names, album names, any music metadata
- Quiz button label is always "Quiz" in all languages
- Language change re-fetches active AI content in the new language

## Recently Played Display Format

- List: `"Title" by Artist (Album) 👍 N 👎 N` (emoji via HTML entities)
- Share: `"N. Title by Artist (Album) [N likes / N unlikes]"` (plain text, no emoji)
- Now Playing share includes artwork URL: `Album cover: https://...300x300bb.jpg`