# Skills vs Agents in Claude Code

## Overview

Radio Calico uses two complementary Claude Code extension mechanisms: **18 slash commands (skills)** for task automation and **9 custom agents** for persistent expert personas. This document explains the differences, current implementation, and future improvement roadmap.

---

## Comparison

| Aspect | **Skills** (`.claude/commands/`) | **Agents** (`.claude/agents/`) |
|--------|--------------------------------|-------------------------------|
| **Purpose** | Execute a specific task with defined steps | Provide ongoing expertise as an AI persona |
| **Invocation** | `/command-name` (slash command) | Referenced in conversation or agent mode |
| **Scope** | One-off: runs steps, produces output, done | Persistent: advises across the entire session |
| **Structure** | Steps → Actions → Report | Persona → Knowledge → Workflow → Rules → Examples |
| **Analogy** | A recipe card you follow once | A team member you consult repeatedly |
| **Statefulness** | Stateless — each run is independent | Context-aware — remembers conversation history |
| **Best for** | Repeatable automation (CI, PR, scaffolding) | Judgment calls (code review, architecture, triage) |
| **Count** | 18 skills | 9 agents |
| **Tests** | 247 tests (structure, versions, references) | 37 tests (structure, versions, content, domain) |
| **Version header** | `<!-- Radio Calico Skill v1.0.0 -->` | `<!-- Radio Calico Agent v1.0.0 -->` |

### When to Use Which

| Scenario | Use |
|----------|-----|
| "Run all tests and report results" | Skill (`/run-ci`) |
| "Review this code for XSS vulnerabilities" | Agent (Frontend Reviewer) |
| "Generate architecture diagrams" | Skill (`/generate-diagrams`) |
| "Is this schema change safe for production?" | Agent (DBA) |
| "Create a PR with summary" | Skill (`/create-pr`) |
| "Is this PR ready to merge?" | Agent (Release Manager) |
| "Scaffold a new API endpoint" | Skill (`/add-endpoint`) |
| "Does this endpoint follow our REST conventions?" | Agent (API Designer) |

---

## Current Skills (18)

| Category | Skills | What they automate |
|----------|--------|--------------------|
| **Dev Environment** | `/start`, `/check-stream`, `/troubleshoot` | Launch, verify, diagnose |
| **Testing** | `/run-ci`, `/test-ratings`, `/test-browser` | Run test suites, report results |
| **Deployment** | `/docker-verify`, `/create-pr` | Build, verify, ship |
| **Scaffolding** | `/add-endpoint`, `/add-share-button`, `/add-dark-style` | Generate boilerplate + tests |
| **Security** | `/security-audit` | Run 6 security scanning tools |
| **Documentation** | `/generate-diagrams`, `/generate-tech-spec`, `/generate-requirements`, `/generate-vv-plan`, `/update-readme-diagrams`, `/update-claude-md` | Generate/sync all docs |

### Future Improvements for Skills

1. **Chained skill pipelines** — Skills that invoke other skills in sequence (e.g., `/release` = `/run-ci` + `/generate-diagrams` + `/update-readme-diagrams` + `/create-pr`). Reduces manual orchestration for complex workflows.

2. **Parameterized skills with validation** — Skills that accept typed arguments with validation rules (e.g., `/add-endpoint POST /api/favorites --auth bearer --rate-limit 10/min`). Currently arguments are free-text; structured params would reduce errors.

3. **Skill output artifacts** — Skills that produce structured output files (JSON reports, coverage summaries) that other skills or agents can consume. Enables data flow between skills.

4. **Conditional steps** — Skills that branch based on project state (e.g., `/run-ci` skips Docker tests if no `docker-compose.yml` exists). Makes skills more portable across projects.

5. **Skill dependency graph** — Declare that `/update-readme-diagrams` requires `/generate-diagrams` to have run first. Claude Code could auto-run prerequisites or warn if stale.

6. **Security-hardened skills** — Skills that validate their own output before writing (e.g., `/add-endpoint` verifies the generated route uses parameterized SQL, not f-strings). Shift-left security into the scaffolding layer.

7. **Dry-run mode** — Skills that preview what they would do without executing (e.g., `/create-pr --dry-run` shows the branch name, commit message, and PR body without pushing). Reduces risk for destructive operations.

---

## Current Agents (9)

| Agent | File | Domain | Key Strength |
|-------|------|--------|--------------|
| **QA Engineer** | `qa-engineer.md` | Testing | Knows all 6 test suites, coverage thresholds, CI pipeline |
| **DBA** | `dba.md` | Database | MySQL 5.7/8.0, schema design, query optimization, migration safety |
| **Frontend Reviewer** | `frontend-reviewer.md` | UI/UX | XSS prevention, theme consistency, responsive design, a11y |
| **DevOps** | `devops.md` | Infrastructure | Docker, nginx, CI/CD, deployment troubleshooting |
| **API Designer** | `api-designer.md` | REST API | Endpoint consistency, auth patterns, status codes, rate limiting |
| **Release Manager** | `release-manager.md` | Releases | PR readiness, CI validation, changelogs, semver |
| **Security Auditor** | `security-auditor.md` | Security | 6 scanning tools, OWASP top 10, vulnerability triage |
| **Performance Analyst** | `performance-analyst.md` | Performance | Caching, CDN, debounce, pagination, resource optimization |
| **Documentation Writer** | `documentation-writer.md` | Docs | Cross-doc consistency, Mermaid diagrams, doc generation |

### Current Agent Structure

Each agent follows a consistent format:

```markdown
<!-- Radio Calico Agent v1.0.0 -->
# Agent Name

## Description          — One-line summary
## Instructions         — Persona definition ("You are a...")
## Domain Tables        — Reference data (endpoints, tools, files)
## Workflow             — Step-by-step process (5-6 steps)
## Key Files            — Files this agent works with
## Rules                — Hard constraints and conventions
## Examples             — 2 input/output pairs with realistic scenarios
```

### Future Improvements for Agents

#### 1. Inter-Agent Collaboration

**Current**: Agents work in isolation — the Security Auditor doesn't know what the DBA recommends.

**Future**: Agents that reference each other's expertise:
- Security Auditor flags a SQL query → delegates to DBA for the parameterized rewrite
- API Designer proposes a new endpoint → QA Engineer auto-generates test cases
- Performance Analyst identifies a slow query → DBA provides the `EXPLAIN` analysis

**How**: Add a `## Delegates To` section listing which agents to consult for specific sub-tasks.

#### 2. Tool-Aware Agents

**Current**: Agents describe tools in prose ("run `make security`") but don't formally declare them.

**Future**: Agents with explicit tool definitions following the Agent SDK format:

```markdown
## Tools
### run_make
Executes Makefile targets and returns results.
Input: target (string) — e.g., "test", "coverage", "security"

### query_db
Runs read-only SQL queries against the test database.
Input: sql (string) — parameterized query only
```

**Why**: Formal tool definitions enable future integration with the Claude Agent SDK for programmatic agent orchestration.

#### 3. Memory-Enabled Agents

**Current**: Agents have no memory between sessions — every conversation starts fresh.

**Future**: Agents that build up project knowledge over time:
- DBA remembers past schema migrations and their outcomes
- QA Engineer tracks flaky tests and their root causes
- Release Manager knows the cadence and patterns of past releases

**How**: Agents write findings to `.claude/memory/` files that are loaded in future sessions.

#### 4. Confidence Scoring

**Current**: Agents give recommendations without indicating certainty level.

**Future**: Agents that distinguish between:
- **High confidence**: "This is a SQL injection — fix immediately" (based on clear pattern match)
- **Medium confidence**: "This query may be slow with >10k rows — profile to confirm"
- **Low confidence**: "Consider adding an index, but benchmark first"

**How**: Add a `## Confidence Framework` section with criteria for each level.

#### 5. Security-First Agent Defaults

**Current**: Security rules are scattered across agents (XSS in Frontend, SQL injection in DBA, secrets in DevOps).

**Future**: A shared security baseline that ALL agents enforce:
- Every agent checks for hardcoded secrets in code they review
- Every agent verifies parameterized queries in SQL they encounter
- Every agent flags `innerHTML` without `escHtml()` in JS they see
- Security Auditor becomes the escalation point, not the only line of defense

**How**: Add a `.claude/rules/security-baseline.md` that all agents reference, plus a `## Security Checklist` section in each agent.

#### 6. Automated Agent Selection

**Current**: Users must know which agent to consult for a given question.

**Future**: Claude Code automatically routes questions to the right agent:
- "Why is this query slow?" → Performance Analyst + DBA
- "Is this PR ready?" → Release Manager + QA Engineer
- "Review this CSS change" → Frontend Reviewer

**How**: Add keyword triggers in agent `## Description` fields that Claude Code uses for routing.

#### 7. Agent Self-Testing

**Current**: Tests validate agent file structure (headings, versions, key sections).

**Future**: Tests that validate agent **behavior quality**:
- Given a known-vulnerable code snippet, does the Security Auditor flag it?
- Given a schema change, does the DBA mention backward compatibility?
- Given a failing test, does the QA Engineer suggest reading the source code first?

**How**: Add `tests/test_agent_behavior.py` with prompt-response pairs that validate agent reasoning patterns.

#### 8. Domain-Specific Glossaries

**Current**: Agents use project terms (e.g., "station", "pendingTrackUpdate") without defining them.

**Future**: Each agent includes a `## Glossary` section with domain terms:

```markdown
## Glossary
- **station**: `"Artist - Title"` string used as the unique key for ratings
- **pendingTrackUpdate**: setTimeout ID that delays UI updates by hls.latency
- **fetchItunesCached**: localStorage wrapper with 24h TTL for iTunes API calls
```

**Why**: Prevents misinterpretation when agents encounter project-specific terminology.

---

## Roadmap Priority

| Priority | Improvement | Impact | Effort |
|----------|-------------|--------|--------|
| **P0** | Security-first agent defaults | All agents enforce security baseline | Medium |
| **P0** | Domain-specific glossaries | Reduces misinterpretation errors | Low |
| **P1** | Inter-agent collaboration | Agents produce richer, cross-domain advice | High |
| **P1** | Chained skill pipelines | Complex workflows in one command | Medium |
| **P1** | Agent self-testing | Validates reasoning quality, not just structure | High |
| **P2** | Tool-aware agents | Enables Agent SDK integration | Medium |
| **P2** | Parameterized skills | Reduces scaffolding errors | Medium |
| **P2** | Automated agent selection | Better UX — no need to know agent names | Medium |
| **P3** | Memory-enabled agents | Agents learn from project history | High |
| **P3** | Confidence scoring | Users know when to trust vs verify | Low |
| **P3** | Skill output artifacts | Data flow between skills | Medium |
| **P3** | Dry-run mode | Safe previews before execution | Low |

---

## References

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/agents)
- Project agents: `.claude/agents/*.md` (9 files)
- Project skills: `.claude/commands/*.md` (18 files) + `.claude/skills/*/SKILL.md` (mirrors)
- Agent tests: `tests/test_skills.py` (284 tests)
- Bootstrap script: `scripts/init-claude-code.sh` (creates 3 starter agents + 3 skills)