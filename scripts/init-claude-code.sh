#!/usr/bin/env bash
#
# init-claude-code.sh — Bootstrap Claude Code best practices for any project
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/mgmarques/radiocalico/main/scripts/init-claude-code.sh | bash
#   # or
#   ./scripts/init-claude-code.sh [project-dir]
#
# What it creates:
#   CLAUDE.md              — Project overview template (<200 lines)
#   CONTRIBUTING.md        — Onboarding guide for developers + Claude Code
#   VERSION                — Semver version file (1.0.0)
#   .claudeignore          — Exclude noise from Claude context
#   .claude/settings.json  — Permissions, hooks, denied destructive ops
#   .claude/rules/         — Topic-specific rule files
#   .claude/skills/        — Skill catalog README
#   .claude/commands/      — Example slash commands (3 starter)
#   .claude/agents/        — Example custom agents (3 starter)
#   tests/test_skills.py   — Skill + agent validation test framework
#
# Safe to run on existing projects — never overwrites existing files.

set -euo pipefail

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

PROJECT_NAME=$(basename "$(pwd)")
DATE=$(date +%Y-%m-%d)

info()  { echo "  ✓ $1"; }
skip()  { echo "  · $1 (already exists, skipped)"; }
create_if_missing() {
    local file="$1"
    local dir
    dir=$(dirname "$file")
    [ -d "$dir" ] || mkdir -p "$dir"
    if [ -f "$file" ]; then
        skip "$file"
        return 1
    fi
    return 0
}

echo ""
echo "🔧 Initializing Claude Code for: $PROJECT_NAME"
echo "   Directory: $(pwd)"
echo ""

# ── VERSION ──────────────────────────────────────────────────
if create_if_missing "VERSION"; then
    echo "1.0.0" > VERSION
    info "VERSION (1.0.0)"
fi

# ── .claudeignore ────────────────────────────────────────────
if create_if_missing ".claudeignore"; then
    cat > .claudeignore << 'IGNORE'
# Dependencies
node_modules/
venv/
.venv/
__pycache__/
*.pyc

# Build artifacts
build/
dist/
*.egg-info/
.ruff_cache/
.pytest_cache/

# Coverage
coverage/
htmlcov/
.coverage

# IDE & OS
.DS_Store
*.swp
.idea/
.vscode/

# Logs & temp
*.log
tmp/

# Lock files (large)
package-lock.json
IGNORE
    info ".claudeignore"
fi

# ── .claude/settings.json ────────────────────────────────────
if create_if_missing ".claude/settings.json"; then
    cat > .claude/settings.json << 'SETTINGS'
{
  "permissions": {
    "allow": [
      "Bash(make *)",
      "Bash(npm *)",
      "Bash(npx *)",
      "Bash(pytest *)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git checkout*)",
      "Bash(git branch*)",
      "Bash(git add*)",
      "Bash(git commit*)",
      "Bash(git push*)",
      "Bash(gh pr*)",
      "Bash(gh run*)",
      "Bash(curl *)",
      "Bash(ls *)",
      "Bash(wc *)",
      "Bash(mkdir *)",
      "Bash(docker compose*)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git reset --hard*)",
      "Bash(git push --force*)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Context compacted. Reminders: (1) Run tests before committing. (2) Check CLAUDE.md for conventions. (3) Detailed rules in .claude/rules/'"
          }
        ]
      }
    ]
  }
}
SETTINGS
    info ".claude/settings.json (permissions + hooks)"
fi

# ── .claude/rules/ ───────────────────────────────────────────
if create_if_missing ".claude/rules/testing.md"; then
    cat > .claude/rules/testing.md << 'RULES'
# Testing Rules

## Test Strategy

- All new features must have tests
- Run `make test` (or equivalent) before committing
- Coverage thresholds are enforced in CI

## Test Files

| Suite | Location | Tool |
|-------|----------|------|
| Unit tests | `tests/` | pytest / jest |
| Integration | `tests/` | pytest |

## CI/CD

- Tests run automatically on push/PR via GitHub Actions
- Lint → Test → Security scan pipeline
RULES
    info ".claude/rules/testing.md"
fi

if create_if_missing ".claude/rules/code-style.md"; then
    cat > .claude/rules/code-style.md << 'RULES'
# Code Style Rules

## General

- Follow existing patterns in the codebase
- Use structured logging (not print/console.log)
- Parameterize all SQL queries (never use f-strings)
- Escape user input before DOM insertion

## Linting

- Run `make lint` before committing
- Auto-fix available where supported
RULES
    info ".claude/rules/code-style.md"
fi

# ── .claude/skills/README.md ────────────────────────────────
if create_if_missing ".claude/skills/README.md"; then
    cat > .claude/skills/README.md << CATALOG
# $PROJECT_NAME — Skill Catalog

> Type \`/skill-name\` in Claude Code to invoke.

## Available Skills

| Skill | Description |
|-------|-------------|
| /start | Launch development environment |
| /run-ci | Run full CI pipeline |
| /create-pr | Branch, commit, push, create PR |

## Custom Agents

Task-specific AI personalities in \`.claude/agents/\`:

| Agent | Focus |
|-------|-------|
| code-reviewer | PR review, conventions, security |
| qa-engineer | Run tests, triage failures |
| devops | CI/CD, Docker, deployment |

## Creating New Skills

1. Create \`.claude/commands/your-skill.md\` with version header
2. Create \`.claude/skills/your-skill/SKILL.md\` (copy)
3. Add tests in \`tests/test_skills.py\`
4. Update this catalog

## Creating New Agents

1. Create \`.claude/agents/your-agent.md\` with version header
2. Include: heading, Workflow section, Key Files section, Rules section
3. Add to \`EXPECTED_AGENTS\` in \`tests/test_skills.py\`
4. Update this catalog and CLAUDE.md
CATALOG
    info ".claude/skills/README.md (catalog)"
fi

# ── Example slash commands ───────────────────────────────────
if create_if_missing ".claude/commands/start.md"; then
    cat > .claude/commands/start.md << 'CMD'
<!-- Skill v1.0.0 -->
Start the development environment.

### Steps

1. Install dependencies if needed
2. Start any required services (database, etc.)
3. Start the application server
4. Verify it's responding
5. Report the URL to the user

IMPORTANT: Run the server in the background. Never block the terminal.
CMD
    mkdir -p ".claude/skills/start"
    cp ".claude/commands/start.md" ".claude/skills/start/SKILL.md"
    info ".claude/commands/start.md + skill"
fi

if create_if_missing ".claude/commands/run-ci.md"; then
    cat > .claude/commands/run-ci.md << 'CMD'
<!-- Skill v1.0.0 -->
Run the full CI pipeline.

### Steps

1. Run linting
2. Run all tests with coverage
3. Run security scans (if configured)
4. Report results: pass/fail for each step
5. If anything fails, investigate and suggest fixes
CMD
    mkdir -p ".claude/skills/run-ci"
    cp ".claude/commands/run-ci.md" ".claude/skills/run-ci/SKILL.md"
    info ".claude/commands/run-ci.md + skill"
fi

if create_if_missing ".claude/commands/create-pr.md"; then
    cat > .claude/commands/create-pr.md << 'CMD'
<!-- Skill v1.0.0 -->
Create a pull request for the current changes.

### Steps

1. Check `git status` and `git diff --stat`
2. Create a descriptive branch if on main
3. Stage relevant files (never .env or secrets)
4. Commit with descriptive message + Co-Authored-By
5. Push with `-u origin`
6. Create PR via `gh pr create` with summary + test plan
7. Report the PR URL

### Rules

- PR title under 70 characters
- Always include a test plan
- Never force-push or push to main directly
CMD
    mkdir -p ".claude/skills/create-pr"
    cp ".claude/commands/create-pr.md" ".claude/skills/create-pr/SKILL.md"
    info ".claude/commands/create-pr.md + skill"
fi

# ── .claude/agents/ ─────────────────────────────────────────
if create_if_missing ".claude/agents/code-reviewer.md"; then
    cat > .claude/agents/code-reviewer.md << 'AGENT'
<!-- Agent v1.0.0 -->
# Code Reviewer Agent

You are a Code Reviewer for this project. You review pull requests and code changes for quality, correctness, and adherence to project conventions.

## Workflow

1. **Read the diff** — understand what changed and why
2. **Check conventions** — verify code follows `.claude/rules/` guidelines
3. **Verify tests** — ensure new code has tests, existing tests still pass
4. **Security review** — check for injection, XSS, hardcoded secrets
5. **Suggest improvements** — provide specific, actionable feedback

## Key Files

- `CLAUDE.md` — project conventions and architecture
- `.claude/rules/` — detailed coding rules
- `tests/` — test suite

## Rules

- Always read the code before commenting
- Be specific — include file paths and line numbers
- Distinguish between blocking issues and suggestions
- Check that tests cover the new functionality
- Flag any hardcoded secrets or credentials
AGENT
    info ".claude/agents/code-reviewer.md"
fi

if create_if_missing ".claude/agents/qa-engineer.md"; then
    cat > .claude/agents/qa-engineer.md << 'AGENT'
<!-- Agent v1.0.0 -->
# QA Engineer Agent

You are a QA Engineer for this project. You run tests, analyze failures, and ensure code quality.

## Workflow

1. **Identify scope** — determine which tests are relevant to the change
2. **Run tests** — execute the appropriate test commands
3. **Analyze failures** — read both the test and the source code
4. **Diagnose root cause** — distinguish between test bugs, source bugs, and environment issues
5. **Suggest fixes** — provide specific code changes with file paths
6. **Verify** — re-run after fixes to confirm all tests pass

## Key Files

- `tests/` — test suite
- `Makefile` — test and CI targets (if present)

## Rules

- Never skip or disable tests without explaining why
- When a test fails, always read the source code it tests before suggesting changes
- Report results as: `PASS (N/N)` or `FAIL (N/N) — [list of failures]`
AGENT
    info ".claude/agents/qa-engineer.md"
fi

if create_if_missing ".claude/agents/devops.md"; then
    cat > .claude/agents/devops.md << 'AGENT'
<!-- Agent v1.0.0 -->
# DevOps Agent

You are a DevOps Engineer for this project. You manage CI/CD, Docker, deployment, and infrastructure configuration.

## Workflow

1. **Diagnose** — identify if issue is CI, Docker, deployment, or configuration
2. **Inspect configs** — read Dockerfiles, compose files, CI YAML, Makefile
3. **Check logs** — review build output, container logs, CI job results
4. **Fix** — provide specific config changes with explanations
5. **Verify** — suggest commands to confirm the fix works

## Key Files

- `Dockerfile` — container build (if present)
- `docker-compose.yml` — service orchestration (if present)
- `.github/workflows/` — CI/CD pipeline (if present)
- `Makefile` — build and deploy targets (if present)

## Rules

- Never expose secrets in CI logs or Docker layers
- Always use non-root users in containers when possible
- Keep CI pipelines fast — parallelize independent jobs
- Use specific version tags for base images, not `latest`
AGENT
    info ".claude/agents/devops.md"
fi

# ── CLAUDE.md ────────────────────────────────────────────────
if create_if_missing "CLAUDE.md"; then
    cat > CLAUDE.md << CLAUDE
# $PROJECT_NAME — Claude Code Guidelines

> Detailed rules in \`.claude/rules/\`: testing.md, code-style.md

## Project Overview

<!-- One paragraph: what this project does, who it's for, key tech choices -->
TODO: Describe your project here.

## Architecture

<!-- Bullet points: frontend, backend, database, external services -->
- **Frontend**: TODO
- **Backend**: TODO
- **Database**: TODO

## Key Endpoints

<!-- List your API routes -->
- \`GET /\` — TODO
- \`POST /api/example\` — TODO

## Common Tasks

\`\`\`bash
# Development
make install   # Install dependencies
make dev       # Start dev server

# Testing
make test      # Run all tests
make lint      # Run all linters
make ci        # Full CI pipeline
\`\`\`

## Important Notes

- TODO: Add project-specific gotchas and conventions
- Run \`make ci\` before merging
- Check \`.claude/rules/\` for detailed conventions

## Slash Commands

| Command | Purpose |
|---------|---------|
| \`/start\` | Launch dev environment |
| \`/run-ci\` | Run full CI pipeline |
| \`/create-pr\` | Branch, commit, push, create PR |

## Custom Agents

Task-specific AI personalities in \`.claude/agents/\` with specialized workflows.

| Agent | File | Focus |
|-------|------|-------|
| Code Reviewer | \`code-reviewer.md\` | PR review, conventions, security |
| QA Engineer | \`qa-engineer.md\` | Run tests, triage failures |
| DevOps | \`devops.md\` | CI/CD, Docker, deployment |

## Claude Code Configuration

- **Rules**: \`.claude/rules/\` — topic-specific context (loaded on demand)
- **Settings**: \`.claude/settings.json\` — auto-approved commands, hooks
- **Skills**: \`.claude/skills/\` — slash command directories
- **Agents**: \`.claude/agents/\` — task-specific AI personalities
- **Ignore**: \`.claudeignore\` — excludes noise from context
CLAUDE
    info "CLAUDE.md (template — edit to match your project)"
fi

# ── CONTRIBUTING.md ──────────────────────────────────────────
if create_if_missing "CONTRIBUTING.md"; then
    cat > CONTRIBUTING.md << CONTRIB
# Contributing to $PROJECT_NAME

## Quick Start

\`\`\`bash
git clone <repo-url>
cd $PROJECT_NAME
make install
\`\`\`

## Using Claude Code

This project is configured for [Claude Code](https://claude.ai/claude-code):

- **CLAUDE.md** — Project overview and conventions
- **\`.claude/rules/\`** — Detailed rules loaded on relevant topics
- **\`.claude/agents/\`** — Task-specific AI personalities (code-reviewer, qa-engineer, devops)
- **\`.claude/settings.json\`** — Auto-approved commands and hooks
- **\`.claudeignore\`** — Keeps context focused

### Key Commands

| Command | When to use |
|---------|-------------|
| \`/start\` | First time — launch dev environment |
| \`/run-ci\` | Before committing — lint + tests + security |
| \`/create-pr\` | When ready — branch, commit, push, PR |

## Development Workflow

1. Create a feature branch
2. Make changes
3. Run \`make ci\` (or \`/run-ci\`)
4. Create PR (\`/create-pr\`)

## Code Review Checklist

- [ ] Tests pass
- [ ] Linting clean
- [ ] No hardcoded secrets
- [ ] CLAUDE.md updated if needed
CONTRIB
    info "CONTRIBUTING.md"
fi

# ── tests/test_skills.py ────────────────────────────────────
if create_if_missing "tests/test_skills.py"; then
    cat > tests/test_skills.py << 'TESTS'
"""Tests for Claude Code slash commands (skills) and custom agents.

Validates that all command files and agent files exist with correct
structure, version headers, and meaningful content.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = ROOT / ".claude" / "commands"
SKILLS_DIR = ROOT / ".claude" / "skills"
AGENTS_DIR = ROOT / ".claude" / "agents"

EXPECTED_COMMANDS = [
    "start.md",
    "run-ci.md",
    "create-pr.md",
]

EXPECTED_AGENTS = [
    "code-reviewer.md",
    "qa-engineer.md",
    "devops.md",
]


# ── Command Tests ─────────────────────────────────────────────


class TestCommandFilesExist:
    """All expected command files must exist."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_command_file_exists(self, filename):
        assert (COMMANDS_DIR / filename).exists(), f"Missing: {filename}"

    def test_no_unexpected_commands(self):
        actual = {f.name for f in COMMANDS_DIR.glob("*.md")}
        expected = set(EXPECTED_COMMANDS)
        extra = actual - expected
        assert not extra, f"Unexpected command files: {extra}"


class TestVersionHeaders:
    """All commands must have a version header."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_has_version_header(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        assert "<!-- " in content and " v" in content

    def test_all_versions_consistent(self):
        versions = set()
        for f in EXPECTED_COMMANDS:
            match = re.search(r"v(\d+\.\d+\.\d+)", (COMMANDS_DIR / f).read_text())
            if match:
                versions.add(match.group(1))
        assert len(versions) == 1, f"Inconsistent versions: {versions}"


class TestSkillDirectories:
    """Each command should have a matching skill directory."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_skill_has_skill_md(self, filename):
        name = filename.replace(".md", "")
        assert (SKILLS_DIR / name / "SKILL.md").exists()


class TestProjectVersionFile:
    """VERSION file must exist and be valid semver."""

    def test_version_file_exists(self):
        assert (ROOT / "VERSION").exists()

    def test_version_is_semver(self):
        version = (ROOT / "VERSION").read_text().strip()
        assert re.match(r"^\d+\.\d+\.\d+$", version)


# ── Agent Tests ───────────────────────────────────────────────


class TestAgentFilesExist:
    """All expected agent files must exist."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_agent_file_exists(self, filename):
        path = AGENTS_DIR / filename
        assert path.exists(), f"Missing agent file: {path}"

    def test_no_unexpected_agents(self):
        actual = {f.name for f in AGENTS_DIR.glob("*.md")}
        expected = set(EXPECTED_AGENTS)
        extra = actual - expected
        assert not extra, f"Unexpected agent files: {extra}"

    def test_agents_directory_exists(self):
        assert AGENTS_DIR.is_dir()


class TestAgentVersionHeaders:
    """All agents must have a version header."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_version_header(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        assert "<!-- Agent v" in content, f"{filename} missing version header"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_version_is_semver(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        match = re.search(r"v(\d+\.\d+\.\d+)", content)
        assert match, f"{filename} has no semver version"

    def test_all_agent_versions_consistent(self):
        versions = set()
        for filename in EXPECTED_AGENTS:
            content = (AGENTS_DIR / filename).read_text()
            match = re.search(r"v(\d+\.\d+\.\d+)", content)
            if match:
                versions.add(match.group(1))
        assert len(versions) == 1, f"Inconsistent agent versions: {versions}"


class TestAgentContent:
    """Agents must have meaningful content."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_heading(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        assert "# " in content, f"{filename} missing heading"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_substantial_content(self, filename):
        content = (AGENTS_DIR / filename).read_text().strip()
        lines = [l for l in content.splitlines() if not l.startswith("<!--")]
        assert len(lines) >= 10, f"{filename} too short ({len(lines)} lines)"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_workflow_or_rules(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        has_section = "## Workflow" in content or "## Rules" in content
        assert has_section, f"{filename} missing Workflow or Rules section"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_key_files_section(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        assert "## Key Files" in content or "## Available" in content, (
            f"{filename} missing Key Files section"
        )
TESTS
    info "tests/test_skills.py (skill + agent validation framework)"
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
echo "✅ Claude Code initialized for $PROJECT_NAME"
echo ""
echo "   Created:"
echo "   • 3 slash commands (/start, /run-ci, /create-pr)"
echo "   • 3 custom agents (code-reviewer, qa-engineer, devops)"
echo "   • Rules, settings, .claudeignore, tests"
echo ""
echo "   Next steps:"
echo "   1. Edit CLAUDE.md — describe your project"
echo "   2. Edit .claude/rules/ — add project-specific rules"
echo "   3. Edit .claude/agents/ — customize or add agents"
echo "   4. Run: pytest tests/test_skills.py -v"
echo "   5. Add more skills/agents (see .claude/skills/README.md)"
echo ""
