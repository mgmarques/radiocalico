---
name: update-claude-md
description: Refresh CLAUDE.md from current codebase state
---
Refresh CLAUDE.md to match the current state of the Radio Calico codebase.

Steps:

1. **Read all key files** in parallel:
   - `static/index.html` — check for new/removed UI sections
   - `static/js/player.js` — check for new functions, state variables, event listeners
   - `static/css/player.css` — check for new component styles, dark mode overrides
   - `api/app.py` — check for new/changed API routes
   - List the full file tree (excluding venv, node_modules, .git, __pycache__)

2. **Compare** each section of CLAUDE.md against the actual code:
   - File Tree — does it match the real directory structure?
   - Key Files table — any new files to add?
   - Key URLs & Endpoints — any new routes?
   - Code Conventions — any new patterns?
   - Player.js Architecture — do all subsections reflect current code?
   - Known Gotchas — any new gotchas discovered?
   - Style Guide — any new tokens or breakpoints?
   - Display formats — do they match the actual rendering/share code?

3. **Update** CLAUDE.md with any differences found. Do NOT remove existing content unless it's outdated/wrong — prefer updating in place.

4. Report what was changed.
