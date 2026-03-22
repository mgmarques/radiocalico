---
name: claude-qa
description: Audit all Claude Code components against best practices, fix violations, update tests and docs
context: fork
agent: claude-code-housekeeper
---
Run a full QA audit of all Claude Code configuration components.

## What It Does

1. **Audit** — checks all commands, agents, rules, hooks, and CLAUDE.md against best practices
2. **Fix** — auto-corrects YAML frontmatter, stale counts, missing test entries
3. **Test** — updates `tests/test_skills.py` with new components and runs the suite
4. **Document** — updates docs in dependency order: `rules/architecture.md` → `docs/architecture.md` → `docs/tech-spec.md` → `docs/Skills_vs_Agents.md` → `CLAUDE.md` → `README.md`
5. **Report** — outputs a QA report card with findings, fixes, and remaining manual items

## When to Run

- Before a release or version bump
- After adding new skills, agents, or rules
- After a rebase or merge that touches `.claude/` files
- Periodically as housekeeping (monthly recommended)

## Components Checked

| Component | Location | What's checked |
|---|---|---|
| Commands | `.claude/commands/*.md` | YAML frontmatter (name, description, context, agent) |
| Skills | `.claude/skills/*/SKILL.md` | Mirror of commands, identical frontmatter |
| Agents | `.claude/agents/*.md` | YAML frontmatter (name, description, tools, model) |
| Rules | `.claude/rules/*.md` | Heading, referenced in CLAUDE.md |
| Hooks | `.claude/settings.json` | PostToolUse linters, SessionStart reminders |
| CLAUDE.md | Root | Best practices from `.claude/README.MD` |
| Tests | `tests/test_skills.py` | EXPECTED_COMMANDS, EXPECTED_AGENTS, count assertions |
| Docs | `docs/*.md` | Cross-document count consistency |