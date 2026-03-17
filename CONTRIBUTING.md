# Contributing to Radio Calico

## Quick Start

```bash
# Clone and setup
git clone https://github.com/mgmarques/radiocalico.git
cd radiocalico
make install   # Python + Node.js dependencies

# Local dev
brew services start mysql@5.7
cd api && source venv/bin/activate && python app.py   # http://127.0.0.1:5000

# Docker (no local setup needed)
cp .env.example .env   # edit passwords
make docker-dev        # http://127.0.0.1:5050
```

## Using Claude Code

This project is optimized for [Claude Code](https://claude.ai/claude-code). The AI assistant has full context of the codebase via:

- **CLAUDE.md** — project overview, endpoints, conventions, gotchas (128 lines)
- **`.claude/rules/`** — detailed rules loaded on relevant topics (architecture, testing, database, style)
- **`.claude/settings.json`** — auto-approved commands, denied destructive ops, lint hooks
- **`.claudeignore`** — excludes noise (node_modules, venv, coverage) from context

### Slash Commands (17 available)

Type `/` in Claude Code to see all commands. Key ones:

| Command | When to use |
|---------|-------------|
| `/start` | First time setup — launches dev environment |
| `/run-ci` | Before committing — runs lint + tests + security |
| `/create-pr` | When ready — branches, commits, pushes, creates PR |
| `/add-endpoint` | Adding a new API route — scaffolds route + tests + docs |
| `/docker-verify` | After Docker changes — rebuilds and runs E2E tests |
| `/security-audit` | Before releases — runs all 6 security scanning tools |
| `/troubleshoot` | When something's broken — runs debugging checklist |
| `/generate-diagrams` | Updating docs — generates 8 Mermaid architecture diagrams |
| `/generate-tech-spec` | Updating docs — generates 13-section technical spec |

### Tips for Claude Code sessions

1. **Start with context**: Claude reads CLAUDE.md automatically. For deep dives, it loads the relevant `.claude/rules/` file.
2. **Use skills**: `/run-ci` is faster and more reliable than typing out make commands manually.
3. **Let hooks work**: After you edit a file, the auto-lint hook runs Ruff/ESLint automatically.
4. **Check compaction**: If context gets compressed, Claude gets a reminder of critical rules.

## Development Workflow

### Before you start

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Check existing tests pass: `make ci`

### While developing

1. **Lint continuously**: `make lint` (or let the hook do it)
2. **Test frequently**: `make test` for unit tests, `make test-integration` for workflows
3. **Follow conventions** (see `.claude/rules/style-guide.md`):
   - Python: Ruff-formatted, structured JSON logging, parameterized SQL
   - JavaScript: ESLint-clean, `escHtml()` for DOM injection, `log.info/warn/error()` for logging
   - CSS: Stylelint-clean, use CSS custom properties for colors

### Before committing

```bash
make ci          # Lint + Python coverage (98%) + JS coverage (90%) + security
make lint        # Quick check: Ruff + ESLint + Stylelint + HTMLHint
```

### Adding a new API endpoint

Use `/add-endpoint` in Claude Code, or manually:

1. Add route in `api/app.py` (follow existing patterns)
2. Add unit tests in `api/test_app.py`
3. Add integration tests in `api/test_integration.py` if multi-step
4. Add E2E test in `tests/test_e2e.py` if it goes through nginx
5. Update `CLAUDE.md` endpoint section
6. Run `make ci`

### Adding a new slash command

1. Create `.claude/commands/your-command.md` with version header:
   ```markdown
   <!-- Radio Calico Skill v1.0.0 -->
   Description of what it does.
   ### Steps
   1. ...
   ```
2. Create `.claude/skills/your-command/SKILL.md` (copy of the command file)
3. Add to `EXPECTED_COMMANDS` list in `tests/test_skills.py`
4. Add command-specific tests in the same file
5. Update CLAUDE.md slash commands table
6. Run `make test-skills`

## Project Structure for Contributors

```
Key files to know:
├── CLAUDE.md                  # Start here — project overview (128 lines)
├── .claude/
│   ├── rules/                 # Deep-dive context (loaded on demand)
│   │   ├── architecture.md    # Player.js internals
│   │   ├── testing.md         # Test strategy, CI/CD
│   │   ├── database.md        # MySQL schema
│   │   └── style-guide.md     # CSS tokens, code conventions
│   ├── settings.json          # Permissions, hooks, denied ops
│   ├── commands/              # Slash commands (backward compat)
│   └── skills/                # Skills (modern format)
├── api/app.py                 # Flask API (all endpoints)
├── static/js/player.js        # Frontend (all client logic)
├── static/css/player.css      # Styles (light + dark themes)
├── docs/                      # Generated documentation
│   ├── architecture.md        # 8 Mermaid diagrams
│   ├── tech-spec.md           # 13-section technical spec
│   ├── requirements.md        # 91 requirements (FR/NFR)
│   └── vv-test-plan.md        # 52 test cases
└── VERSION                    # Semver (1.0.0)
```

## Test Suite

467 tests across 6 suites. All must pass before merging.

| Suite | Command | What it tests |
|-------|---------|---------------|
| Python unit (61) | `make test-py` | All API endpoints |
| Python integration (19) | `make test-integration` | Multi-step workflows |
| JavaScript (162) | `make test-js` | All player.js functions |
| E2E (19) | `make test-e2e` | Full stack through Docker |
| Browser (37) | `make test-browser` | UI, themes, auth, playback (Selenium) |
| Skills (169) | `make test-skills` | All 18 slash commands |

## Code Review Checklist

- [ ] `make ci` passes (lint + coverage + security)
- [ ] New endpoints have unit + integration tests
- [ ] New JS functions have Jest tests
- [ ] CLAUDE.md updated if endpoints/features changed
- [ ] No hardcoded secrets (use `.env`)
- [ ] Structured logging used (not `print()` or bare `console.log`)
- [ ] SQL uses parameterized queries (never f-strings)
- [ ] HTML injection uses `escHtml()`
