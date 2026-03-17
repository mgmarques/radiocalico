# Radio Calico — Skill Catalog

> All skills are v1.0.0. Type `/skill-name` in Claude Code to invoke.

## Development

| Skill | Description | Requires |
|-------|-------------|----------|
| [/start](start/SKILL.md) | Launch dev environment (local Flask + MySQL or Docker) | MySQL or Docker |
| [/add-endpoint](add-endpoint/SKILL.md) | Scaffold a new Flask API route with tests and docs | MySQL for tests |
| [/add-share-button](add-share-button/SKILL.md) | Add a new social share or music search button | — |
| [/add-dark-style](add-dark-style/SKILL.md) | Add dark mode styling for a new CSS component | — |

## Testing & CI

| Skill | Description | Requires |
|-------|-------------|----------|
| [/run-ci](run-ci/SKILL.md) | Run full CI pipeline: lint + coverage + security | MySQL, Node.js |
| [/test-ratings](test-ratings/SKILL.md) | Test the ratings API end-to-end with curl | Running server |
| [/test-browser](test-browser/SKILL.md) | Run 37 Selenium browser tests (headless Chrome) | Docker + Chrome |
| [/docker-verify](docker-verify/SKILL.md) | Rebuild Docker prod stack and run E2E + health checks | Docker |
| [/security-audit](security-audit/SKILL.md) | Run all 6 security tools and suggest fixes | Docker (for Trivy/ZAP) |

## Operations

| Skill | Description | Requires |
|-------|-------------|----------|
| [/check-stream](check-stream/SKILL.md) | Check HLS stream and metadata status | — |
| [/troubleshoot](troubleshoot/SKILL.md) | Diagnose common issues (ports, cache, MySQL, etc.) | — |
| [/create-pr](create-pr/SKILL.md) | Branch, commit, push, and create a GitHub PR | Git + GitHub CLI |

## Documentation

| Skill | Description | Output |
|-------|-------------|--------|
| [/generate-diagrams](generate-diagrams/SKILL.md) | Generate 8 Mermaid architecture diagrams | `docs/architecture.md` |
| [/generate-tech-spec](generate-tech-spec/SKILL.md) | Generate 13-section technical specification | `docs/tech-spec.md` |
| [/generate-requirements](generate-requirements/SKILL.md) | Generate requirements documentation (91 FR/NFR) | `docs/requirements.md` |
| [/generate-vv-plan](generate-vv-plan/SKILL.md) | Generate V&V test plan (52 test cases) | `docs/vv-test-plan.md` |
| [/update-readme-diagrams](update-readme-diagrams/SKILL.md) | Sync 6 Mermaid diagrams from architecture.md to README | Updates `README.md` |
| [/update-claude-md](update-claude-md/SKILL.md) | Refresh CLAUDE.md to match current codebase | Updates `CLAUDE.md` |

## Skill Dependencies

```
/generate-diagrams ──> /generate-tech-spec (references diagrams)
                  ├──> /update-readme-diagrams (syncs diagrams to README)
                  └──> /generate-vv-plan (references architecture)

/generate-requirements ──> /generate-vv-plan (references requirement IDs)
```

Run `/generate-diagrams` first, then the others can reference it.

## Creating New Skills

1. Create `.claude/commands/your-skill.md` with version header
2. Create `.claude/skills/your-skill/SKILL.md` (copy of command)
3. Add to `EXPECTED_COMMANDS` in `tests/test_skills.py`
4. Add skill-specific tests
5. Update this catalog
6. Run `make test-skills` to verify