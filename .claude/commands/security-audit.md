<!-- Radio Calico Skill v2.0.0 -->
Run all 6 security scanning tools and report findings with fix suggestions.

## Agent
Delegate this entire skill to the **Security Auditor** subagent (`security-auditor`).
The Security Auditor has specialized knowledge of all 6 security tools, OWASP Top 10, and vulnerability triage. It will run all steps in an isolated context window and return only a summary to the main conversation.

### Steps

1. **Run all scans** (in parallel where possible):
   - `make bandit` — Python SAST (expected: 0 issues)
   - `make safety` — Python dependency CVEs
   - `make audit-npm` — JavaScript dependency CVEs (expected: 0 vulnerabilities)
   - `make hadolint` — Dockerfile best practices (expected: 0 issues)
   - `make trivy` — Docker image scan for HIGH/CRITICAL CVEs (requires built image)
   - `make zap` — OWASP ZAP DAST baseline (requires running Docker prod stack)

2. **For each tool**, report:
   - Pass/fail status
   - Number of findings by severity
   - Specific CVEs or rule violations found

3. **For each finding**, suggest a fix:
   - Dependency CVEs: pin to fixed version or upgrade
   - SAST issues: code change with before/after
   - Dockerfile issues: specific line fix
   - ZAP warnings: nginx config or CSP header changes
   - Image CVEs: base image upgrade or package pin

4. **If all pass**, confirm clean status and report scan durations

### Prerequisites

- Docker prod stack running for ZAP scan (`make docker-prod`)
- Docker image built for Trivy scan (`docker build -t radiocalico-app:latest --target prod .`)
- Python venv activated for Bandit/Safety
- npm dependencies installed for npm audit

### Quick mode

If user says "quick" or "fast", skip Trivy and ZAP (they require Docker) and run only:
`make security` (Bandit + Safety + npm audit)