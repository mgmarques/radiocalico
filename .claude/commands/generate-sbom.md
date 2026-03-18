<!-- Radio Calico Skill v1.0.0 -->
# Generate SBOM

Generate `docs/SBOM.md` — a Software Bill of Materials listing every installed
Python and Node.js package with its version and known vulnerability status.

## What it produces

`docs/SBOM.md` with:

- **Summary table** — total packages, vulnerability count, scanner names, scan date
- **Python packages table** — all `pip list` packages with `pip-audit` CVE results
- **Node.js packages table** — all `npm list --depth=0` packages with `npm audit` results
- **Vulnerability details** — full detail rows with Published date (OSV.dev) and Fix Version
- **Impact Analysis** — per-vuln deployment assessment: whether the vulnerable code path is actually reachable in Radio Calico's production environment

## Steps

1. **Check prerequisites**
   - Verify `pip-audit` is installed: `pip show pip-audit`
   - If missing: `pip install pip-audit`
   - Verify npm is available: `npm --version`

2. **Run the generator**

   ```bash
   python scripts/generate_sbom.py
   ```

   This runs four scans in sequence:
   - `pip list --format=json` — collect Python package inventory
   - `pip-audit --format=json` — scan for Python CVEs (GHSA / OSV database)
   - `npm list --json --depth=0` — collect Node.js direct dependencies
   - `npm audit --json` — scan for Node.js CVEs (npm advisory database)

3. **Review the output** — open `docs/SBOM.md` and check:
   - Are any packages flagged with 🔴 Critical or 🟠 High vulnerabilities?
   - Are the package counts correct (Python and Node.js)?
   - Does the **Impact Analysis** section show any 🔴 High or 🟠 Moderate ratings?
   - Are any new vulns marked ⚪ Unknown (no impact entry yet)?

4. **Update impact analysis** (if new vulns appear)
   - Open `scripts/generate_sbom.py` and find the `_IMPACT` dict
   - Add an entry keyed by vuln ID (CVE/PYSEC) or package name (npm advisory slugs)
   - Rate it: 🟢 Not Applicable / 🟡 Low (build-time only) / 🟠 Moderate / 🔴 High
   - Explain whether the vulnerable code path is reachable in Radio Calico's production environment
   - Re-run `python scripts/generate_sbom.py` to confirm the entry renders correctly

5. **Remediation** (if vulnerabilities found with 🔴 High or 🟠 Moderate impact)
   - For Python: update the version in `api/requirements.txt` or `api/requirements-dev.txt`
   - For Node.js: run `npm update <package>` or update `package.json`
   - Re-run `python scripts/generate_sbom.py` to confirm the vulnerability is resolved
   - Escalate complex findings to the **Security Auditor** agent for triage

6. **Report** — summarise:
   - Total packages scanned (Python + Node.js)
   - Number of vulnerabilities found (by severity)
   - Impact ratings from the Impact Analysis section
   - Any packages needing immediate attention (🔴 High impact)

## Integration

| Context | How SBOM is used |
| --- | --- |
| **Security Auditor agent** | Reads `docs/SBOM.md` as the dependency inventory for triage |
| **Release Manager agent** | Reviews SBOM before approving any release |
| **`/security-audit` skill** | Complements SBOM: covers SAST + DAST + Docker image |
| **CI/CD** | `.github/workflows/update-sbom.yml` auto-updates `docs/SBOM.md` on every PR |

## Severity legend

| Icon | Level | Action |
| --- | --- | --- |
| 🔴 | Critical | Fix before merge — escalate to Security Auditor |
| 🟠 | High | Fix before merge |
| 🟡 | Medium / Moderate | Fix within sprint |
| 🔵 | Low | Track; fix at next dependency update |
| ✅ | None | No action needed |

## Rules

- Always run `pip install pip-audit` in the venv before generating — it is NOT in `requirements-dev.txt`
- Do NOT hardcode versions in `docs/SBOM.md` — always regenerate from the actual installed state
- Do NOT commit `docs/SBOM.md` with fabricated results — the script must run and produce real output
- If `pip-audit` is unavailable in CI, the script prints a warning and skips Python CVEs (packages are still listed)
- When a new vuln appears with ⚪ Unknown impact, add an entry to the `_IMPACT` dict in `scripts/generate_sbom.py` before merging
