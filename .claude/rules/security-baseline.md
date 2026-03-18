# Security Baseline

Universal security rules for all Radio Calico agents. Every agent's `## Security Checklist` references this file. If a change violates any rule here, escalate to confidence **LOW** and stop.

## Non-Negotiable Rules

| # | Rule | Violation |
|---|------|-----------|
| S-1 | All `innerHTML` insertions **must** use `escHtml()` | XSS — stop immediately |
| S-2 | All SQL queries **must** use parameterized `%s` placeholders — never f-strings or `.format()` | SQL injection — stop immediately |
| S-3 | Secrets, tokens, and API keys **must never** appear in code, commits, or config files tracked by git | Credential leak — stop immediately |
| S-4 | `.env` files **must** remain in `.gitignore` and never be committed | Credential leak |
| S-5 | Docker containers **must** run as non-root (`appuser`) | Privilege escalation |
| S-6 | MySQL port **must not** be exposed externally in production | Attack surface |
| S-7 | Rate limiting **must** be present on `/api/register` and `/api/login` (5 req/min) | Brute force |
| S-8 | IP addresses **must never** appear in API responses | Privacy leak |
| S-9 | Auth tokens use `secrets.token_hex(32)` and are stored only in `localStorage` (`rc-token`) — never in cookies or URLs | Session hijacking |
| S-10 | All `window.open()` calls **must** include `'noopener'` | Reverse tabnapping |

## OWASP Top 10 Mapping

| OWASP | Radio Calico control | Rules |
|-------|---------------------|-------|
| A01 Broken Access Control | Bearer token on all write endpoints; IP dedup on ratings | S-9 |
| A02 Cryptographic Failures | PBKDF2 260k iterations + random salt; `hmac.compare_digest` | S-3, S-4 |
| A03 Injection | Parameterized PyMySQL queries throughout `app.py` | S-2 |
| A07 XSS | `escHtml()` on all dynamic DOM insertions | S-1 |
| A05 Security Misconfiguration | Non-root Docker, no exposed MySQL, `FLASK_DEBUG=false` | S-5, S-6 |
| A06 Vulnerable Components | Safety (Python CVEs) + npm audit (JS CVEs) + Trivy (image) | — |
| A07 Auth Failures | Rate limiting on auth endpoints; timing-safe token comparison | S-7, S-9 |

## Secrets Management

- Credentials loaded from env vars via `python-dotenv` (`api/.env.example` is the template — no real values)
- `.mcp.json` is gitignored — MCP server API keys must never be committed
- GitHub Actions secrets managed via repository settings — never hardcoded in `.github/workflows/`
- `FLASK_SECRET_KEY` must be a strong random value in production (not the dev default)

## Security Tools (run via `make security` or `make security-all`)

| Tool | What it checks |
|------|---------------|
| `make bandit` | Python SAST — SQL injection, hardcoded secrets, unsafe calls |
| `make safety` | Python dependency CVEs |
| `make audit-npm` | JS dependency CVEs |
| `make hadolint` | Dockerfile best practices |
| `make trivy` | Docker image HIGH/CRITICAL vulnerabilities |
| `make zap` | DAST baseline scan (requires `make docker-prod` running) |