<!-- Radio Calico Skill v2.0.0 -->
Add a new retro radio button for a new LLM query type.

The user will specify a query type name (e.g., "trivia"). Follow this process:

1. **HTML** (`static/index.html`): Add a `<button>` inside the `.radio-buttons-row` div, following the existing pattern for Lyrics, Details, Facts, Merch, Jokes, Everything buttons. Use class `retro-btn retro-btn-{name}` and `data-query="{name}"`.

2. **CSS** (`static/css/player.css`): Add a per-button gradient style in the Retro Buttons section. Follow the existing pattern of unique gradient colors per button (e.g., `.retro-btn-{name} { background: linear-gradient(to bottom, #COLOR1, #COLOR2); }`). Add dark mode override if needed.

3. **JS** (`static/js/player.js`): Add the query type to `handleRetroButton()` switch/mapping. The button should call `fetchSongInfo(queryType, artist, track)` with the new type.

4. **LLM prompt** (`api/llm_service.py`): Add a system prompt for the new query type in `LLMService`. Include `max_tokens` limit. The prompt MUST include "NEVER translate song titles, album names, or artist names".

5. **Translations** (`static/js/player.js`): Add `btn_{name}` key to all 3 languages in `_TRANSLATIONS` (en, pt, es). The button label in the HTML should use `data-i18n="btn_{name}"`.

6. **Tests**:
   - `static/js/player.test.js` — test the new button triggers `fetchSongInfo` with correct query type
   - `api/test_app.py` — test the new query type via `/api/song-info` endpoint

7. **Docs**: Update `CLAUDE.md` and `.claude/rules/llm.md` query type tables.

Remind the user to **Cmd+Shift+R** after changes.