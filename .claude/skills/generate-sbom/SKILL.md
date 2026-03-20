<!-- Radio Calico Skill v1.0.0 -->
# Generate SBOM

## Agent
Delegate this entire skill to the **Security Auditor** subagent (`security-auditor`).
The Security Auditor has specialized knowledge of all 6 security tools, OWASP Top 10, and vulnerability triage. It will run all steps in an isolated context window and return only a summary to the main conversation.

Generate `docs/SBOM.md` — a Software Bill of Materials listing every installed
Python, Node.js, .NET (NuGet), and Java (Maven/Gradle) package with its version
and known vulnerability status. Each ecosystem section is auto-detected from
project files — sections are silently skipped for ecosystems not present.

## What it produces

`docs/SBOM.md` with:

- **Summary table** — total packages, vulnerability count, scanner names, scan date
- **Python packages table** — all `pip list` packages with `pip-audit` CVE results
- **Node.js packages table** — all `npm list --depth=0` packages with `npm audit` results
- **`.NET` packages table** (if `*.csproj`/`*.sln` detected) — NuGet packages with `dotnet list package --vulnerable` CVE results
- **Java/Maven packages table** (if `pom.xml` detected) — dependencies from `mvn dependency:list` with OWASP Dependency-Check CVEs
- **Java/Gradle packages table** (if `build.gradle` detected) — dependencies from `gradle dependencies` with OWASP Dependency-Check CVEs
- **Vulnerability details** — enriched rows with CVSS scores, CVSS vectors, created/modified dates, and reference links (OSV.dev)
- **Policy Compliance section** — checked against `sbom-policy.json` thresholds (max critical/high vulns, blocked licenses, minimum scan age)
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

   Optional flags:
   - `--project NAME` — set a project name for multi-project support (default: auto-detected from directory)
   - `--save-db` — persist scan results to MySQL (requires SBOM tables from `api/migrations/sbom_tables.sql`)

   This runs scans for all auto-detected ecosystems in sequence:
   - `pip list --format=json` — collect Python package inventory
   - `pip-audit --format=json` — scan for Python CVEs (GHSA / OSV database)
   - `npm list --json --depth=0` — collect Node.js direct dependencies
   - `npm audit --json` — scan for Node.js CVEs (npm advisory database)
   - `dotnet list package --format json` — collect NuGet packages (if `*.csproj`/`*.sln` found)
   - `dotnet list package --vulnerable --include-transitive` — scan .NET CVEs (built-in CLI)
   - `mvn dependency:list -q` — collect Maven dependencies (if `pom.xml` found)
   - `mvn org.owasp:dependency-check-maven:check` — scan Maven CVEs via OWASP plugin
   - `gradle dependencies --configuration runtimeClasspath` — collect Gradle dependencies (if `build.gradle` found)
   - `gradle dependencyCheckAnalyze` — scan Gradle CVEs via OWASP plugin

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
- `.NET`, Maven, and Gradle sections are only generated if the corresponding project files exist — Radio Calico has none, so these sections are skipped
- For Java CVE scanning, the OWASP Dependency-Check plugin must be configured in `pom.xml` or `build.gradle`; otherwise packages are listed without CVE data
- Policy thresholds are configured in `sbom-policy.json` (max critical/high vulns, blocked licenses, minimum scan age) — edit this file to adjust compliance rules
- To enable `--save-db`, first run `mysql -u root -p radiocalico < api/migrations/sbom_tables.sql` to create the 4 SBOM history tables (sbom_scans, sbom_packages, sbom_vulnerabilities, sbom_impact_analysis)