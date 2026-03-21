#!/usr/bin/env python3
"""Generate SBOM.md — Software Bill of Materials with vulnerability data.

Collects all installed Python, Node.js, .NET (NuGet), and Java (Maven/Gradle)
packages, scans each for known vulnerabilities, enriches with CVSS scores and
dates from OSV.dev, checks policy compliance, and writes a Markdown summary
to docs/SBOM.md. Each ecosystem section is auto-detected — it only appears
if the corresponding project file exists.

Usage (from repo root, with api venv active or in CI after pip install):
    python scripts/generate_sbom.py [--project NAME] [--date YYYY-MM-DD] [--save-db]

--save-db also enables outdated-package checks (pip list --outdated, npm outdated)
for storing latest-version data in the database.

Scanners:
    Python  — pip-audit (GHSA / OSV database)
    Node.js — npm audit (npm advisory database)
    .NET    — dotnet list package --vulnerable --include-transitive (built-in, requires .NET 7+)
    Maven   — OWASP Dependency-Check Maven plugin (mvn org.owasp:dependency-check-maven:check)
    Gradle  — OWASP Dependency-Check Gradle plugin (gradle dependencyCheckAnalyze)

pip-audit must be installed:
    pip install pip-audit
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd, **kwargs):
    """Run *cmd* and return (stdout_str, returncode). Never raises."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, **kwargs
        )
        return result.stdout, result.returncode
    except FileNotFoundError:
        return "", 127


def _run_json(cmd, **kwargs):
    """Run *cmd*, parse stdout as JSON. Returns (data, success_bool)."""
    stdout, rc = _run(cmd, **kwargs)
    try:
        return json.loads(stdout), True
    except json.JSONDecodeError:
        return {}, False


# ── CVSS v3 Base Score Calculator ────────────────────────────────────────────
# Pure-Python implementation of the CVSS v3.0/v3.1 base score formula.
# Reference: https://www.first.org/cvss/v3.1/specification-document

_CVSS_AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_CVSS_AC = {"L": 0.77, "H": 0.44}
_CVSS_PR_U = {"N": 0.85, "L": 0.62, "H": 0.27}
_CVSS_PR_C = {"N": 0.85, "L": 0.68, "H": 0.50}
_CVSS_UI = {"N": 0.85, "R": 0.62}
_CVSS_CIA = {"H": 0.56, "L": 0.22, "N": 0.0}


def _cvss_roundup(x):
    """CVSS v3 Roundup: smallest number ≥ x with 1 decimal digit."""
    return math.ceil(x * 10) / 10


def _parse_cvss_base_score(vector):
    """Parse a CVSS v3 vector string and return (base_score, severity_label).

    Returns (None, "—") if the vector cannot be parsed.
    Example: "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H" → (8.8, "High")
    """
    if not vector or not vector.startswith("CVSS:3"):
        return None, "—"
    metrics = {}
    for part in vector.split("/"):
        if ":" in part:
            k, v = part.split(":", 1)
            metrics[k] = v
    try:
        av = _CVSS_AV[metrics["AV"]]
        ac = _CVSS_AC[metrics["AC"]]
        ui = _CVSS_UI[metrics["UI"]]
        scope_changed = metrics["S"] == "C"
        pr_table = _CVSS_PR_C if scope_changed else _CVSS_PR_U
        pr = pr_table[metrics["PR"]]
        c = _CVSS_CIA[metrics["C"]]
        i = _CVSS_CIA[metrics["I"]]
        a = _CVSS_CIA[metrics["A"]]
    except KeyError:
        return None, "—"

    iss = 1 - ((1 - c) * (1 - i) * (1 - a))
    if scope_changed:
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    else:
        impact = 6.42 * iss

    if impact <= 0:
        return 0.0, "None"

    exploitability = 8.22 * av * ac * pr * ui

    if scope_changed:
        base = _cvss_roundup(min(1.08 * (impact + exploitability), 10))
    else:
        base = _cvss_roundup(min(impact + exploitability, 10))

    if base >= 9.0:
        label = "Critical"
    elif base >= 7.0:
        label = "High"
    elif base >= 4.0:
        label = "Medium"
    elif base > 0:
        label = "Low"
    else:
        label = "None"

    return round(base, 1), label


# ── OSV.dev Vulnerability Metadata ──────────────────────────────────────────

def _get_vuln_metadata(vuln_id, cache):
    """Fetch enriched metadata for a vuln ID from OSV.dev.

    Returns dict: {published, modified, cvss_score, cvss_vector, cvss_label,
                    ref_url, aliases}. Results are cached in *cache*.
    """
    if vuln_id in cache:
        return cache[vuln_id]

    empty = {
        "published": "—", "modified": "—",
        "cvss_score": None, "cvss_vector": "", "cvss_label": "—",
        "ref_url": "", "aliases": [],
    }
    url = f"https://api.osv.dev/v1/vulns/{vuln_id}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        cache[vuln_id] = empty
        return empty

    published = data.get("published", "")
    modified = data.get("modified", "")
    aliases = data.get("aliases", [])

    # CVSS from severity array
    cvss_score, cvss_label, cvss_vector = None, "—", ""
    for sev in data.get("severity", []):
        if sev.get("type", "").startswith("CVSS_V3"):
            cvss_vector = sev.get("score", "")
            cvss_score, cvss_label = _parse_cvss_base_score(cvss_vector)
            break

    # If no CVSS and we have aliases, try the first CVE/GHSA alias
    if cvss_score is None and aliases:
        for alias in aliases:
            if alias.startswith(("CVE-", "GHSA-")) and alias != vuln_id:
                alias_meta = _get_vuln_metadata(alias, cache)
                if alias_meta.get("cvss_score") is not None:
                    cvss_score = alias_meta["cvss_score"]
                    cvss_label = alias_meta["cvss_label"]
                    cvss_vector = alias_meta["cvss_vector"]
                    break

    # Best reference link (prefer ADVISORY, then WEB)
    ref_url = ""
    for ref_type in ("ADVISORY", "WEB", "FIX"):
        for ref in data.get("references", []):
            if ref.get("type") == ref_type:
                ref_url = ref.get("url", "")
                break
        if ref_url:
            break

    result = {
        "published": published[:10] if published else "—",
        "modified": modified[:10] if modified else "—",
        "cvss_score": cvss_score,
        "cvss_vector": cvss_vector,
        "cvss_label": cvss_label,
        "ref_url": ref_url,
        "aliases": aliases,
    }
    cache[vuln_id] = result
    return result


# ── OSV.dev file-based cache ──────────────────────────────────────────────────

_OSV_CACHE_FILE = Path(".sbom-cache.json")
_OSV_CACHE_MAX_AGE_DAYS = 7


def _load_osv_cache(cache_file=_OSV_CACHE_FILE, max_age_days=_OSV_CACHE_MAX_AGE_DAYS):
    """Load cached OSV metadata from disk. Returns {} if stale or missing."""
    if not cache_file.exists():
        return {}
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    cached_at = data.get("_meta", {}).get("cached_at", "")
    if not cached_at:
        return {}
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)
        if age.days > max_age_days:
            return {}
    except ValueError:
        return {}
    entries = dict(data)
    entries.pop("_meta", None)
    return entries


def _save_osv_cache(cache, cache_file=_OSV_CACHE_FILE):
    """Persist OSV metadata cache to disk."""
    data = dict(cache)
    data["_meta"] = {"cached_at": datetime.now(timezone.utc).isoformat()}
    cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Ecosystem detection ───────────────────────────────────────────────────────

_SKIP_DIRS = {"node_modules", "venv", ".venv", "obj", "bin", ".git", "__pycache__", "target", "build", ".tox"}


def _find_files(*patterns):
    """Return True if any file matching a glob pattern exists (skips common build dirs)."""
    for pattern in patterns:
        for p in Path(".").rglob(pattern):
            if not any(part in _SKIP_DIRS for part in p.parts):
                return True
    return False


# ── Python ────────────────────────────────────────────────────────────────────

def get_python_packages():
    """Return [{name, version}] for all installed packages."""
    data, ok = _run_json([sys.executable, "-m", "pip", "list", "--format=json"])
    return data if ok and isinstance(data, list) else []


def get_python_vulns():
    """Return {pkg_name_lower: [{id, fix_version, description}]} via pip-audit --format=json."""
    data, ok = _run_json(["pip-audit", "--format=json"])
    if not ok:
        data, ok = _run_json([sys.executable, "-m", "pip_audit", "--format=json"])
    if not ok:
        print("  ⚠️  pip-audit not available — install with: pip install pip-audit")
        return {}

    vulns = {}
    for dep in data.get("dependencies", []):
        dep_vulns = dep.get("vulns", [])
        if dep_vulns:
            key = dep.get("name", "").lower()
            vulns[key] = [
                {
                    "id": v.get("id", "?"),
                    "fix_version": (v.get("fix_versions") or ["—"])[0],
                    "description": v.get("description", "")[:120],
                }
                for v in dep_vulns
            ]
    return vulns


def get_python_licenses():
    """Return {pkg_name_lower: license_str} using importlib.metadata."""
    licenses = {}
    try:
        from importlib.metadata import distributions
        for dist in distributions():
            name = (dist.metadata.get("Name") or "").lower()
            lic = dist.metadata.get("License") or ""
            if not lic or lic == "UNKNOWN":
                classifiers = dist.metadata.get_all("Classifier") or []
                for c in classifiers:
                    if c.startswith("License :: OSI Approved :: "):
                        lic = c.split(" :: ")[-1]
                        break
            if name:
                licenses[name] = lic[:60] if lic else "Unknown"
    except Exception:
        pass
    return licenses


def get_python_outdated():
    """Return {pkg_name_lower: latest_version} for outdated packages."""
    data, ok = _run_json([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if not ok or not isinstance(data, list):
        return {}
    return {
        p.get("name", "").lower(): p.get("latest_version", "")
        for p in data if p.get("latest_version")
    }


# ── Node.js ───────────────────────────────────────────────────────────────────

def get_npm_packages():
    """Return [{name, version}] for direct npm dependencies (depth=0)."""
    data, ok = _run_json(["npm", "list", "--json", "--depth=0"])
    if not ok:
        return []
    return [
        {"name": name, "version": info.get("version", "unknown")}
        for name, info in data.get("dependencies", {}).items()
    ]


def get_npm_vulns():
    """Return {pkg_name: [{id, severity, fix_version, description}]} via npm audit --json."""
    data, _ = _run_json(["npm", "audit", "--json"])
    vulns = {}
    for pkg_name, info in data.get("vulnerabilities", {}).items():
        severity = info.get("severity", "unknown")
        title = ""
        for via in info.get("via", []):
            if isinstance(via, dict):
                title = via.get("title", via.get("url", ""))[:120]
                break
        cves = info.get("cves", [])
        vuln_id = cves[0] if cves else info.get("url", pkg_name)
        fix_available = info.get("fixAvailable", False)
        if fix_available is False:
            fix_version = "None"
        elif isinstance(fix_available, dict):
            fix_version = fix_available.get("version", "Available")
        else:
            fix_version = "Available"
        vulns.setdefault(pkg_name, []).append(
            {"id": str(vuln_id), "severity": severity, "fix_version": fix_version, "description": title or severity}
        )
    return vulns


def get_npm_licenses():
    """Return {pkg_name: license_str} by reading node_modules package.json files."""
    licenses = {}
    nm = Path("node_modules")
    if not nm.is_dir():
        return licenses
    for pkg_json in nm.glob("*/package.json"):
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            name = data.get("name", "")
            lic = data.get("license", "")
            if isinstance(lic, dict):
                lic = lic.get("type", "")
            if name:
                licenses[name] = str(lic)[:60] if lic else "Unknown"
        except (json.JSONDecodeError, OSError):
            continue
    # Also check scoped packages (@scope/name)
    for scope_dir in nm.glob("@*"):
        if scope_dir.is_dir():
            for pkg_json in scope_dir.glob("*/package.json"):
                try:
                    data = json.loads(pkg_json.read_text(encoding="utf-8"))
                    name = data.get("name", "")
                    lic = data.get("license", "")
                    if isinstance(lic, dict):
                        lic = lic.get("type", "")
                    if name:
                        licenses[name] = str(lic)[:60] if lic else "Unknown"
                except (json.JSONDecodeError, OSError):
                    continue
    return licenses


def get_npm_outdated():
    """Return {pkg_name: latest_version} for outdated npm packages."""
    data, ok = _run_json(["npm", "outdated", "--json"])
    if not data:
        return {}
    return {
        name: info.get("latest", "")
        for name, info in data.items() if info.get("latest")
    }


# ── .NET / NuGet ──────────────────────────────────────────────────────────────

def get_dotnet_packages():
    """Return [{name, version}] for all NuGet packages via dotnet list package --format json."""
    if not _find_files("*.csproj", "*.fsproj", "*.sln"):
        return []
    data, ok = _run_json(["dotnet", "list", "package", "--format", "json"])
    if not ok:
        print("  ⚠️  dotnet CLI not available or does not support --format json (requires .NET 7+)")
        return []
    packages = {}
    for project in data.get("projects", []):
        for fw in project.get("frameworks", []):
            for pkg in fw.get("topLevelPackages", []) + fw.get("transitivePackages", []):
                name = pkg.get("id", "")
                version = pkg.get("resolvedVersion") or pkg.get("requestedVersion", "unknown")
                if name:
                    packages[name.lower()] = {"name": name, "version": version}
    return sorted(packages.values(), key=lambda x: x["name"].lower())


def get_dotnet_vulns():
    """Return {pkg_name_lower: [{id, severity, fix_version, description}]} via dotnet --vulnerable."""
    if not _find_files("*.csproj", "*.fsproj", "*.sln"):
        return {}
    stdout, _ = _run(["dotnet", "list", "package", "--vulnerable", "--include-transitive"])
    if not stdout:
        return {}
    vulns = {}
    for line in stdout.splitlines():
        m = re.match(
            r"\s*>\s+(\S+)\s+\S+\s+\S+\s+(Critical|High|Moderate|Medium|Low)\s+(https://\S+)",
            line,
            re.IGNORECASE,
        )
        if m:
            name, severity, url = m.group(1), m.group(2).lower(), m.group(3)
            vulns.setdefault(name.lower(), []).append({
                "id": url,
                "severity": severity,
                "fix_version": "—",
                "description": f"{severity.capitalize()} vulnerability — {url[:80]}",
            })
    return vulns


# ── Java / Maven ───────────────────────────────────────────────────────────────

def get_maven_packages():
    """Return [{name, version}] from mvn dependency:list output."""
    if not Path("pom.xml").exists():
        return []
    stdout, rc = _run(["mvn", "dependency:list", "-q"])
    if rc == 127 or not stdout:
        print("  ⚠️  Maven (mvn) not available — install Apache Maven to list Java dependencies")
        return []
    packages = {}
    for line in stdout.splitlines():
        m = re.match(r"\s*\[INFO\]\s+([^:\s]+):([^:\s]+):\S+:([^:\s]+):\S+", line)
        if m:
            group, artifact, version = m.group(1), m.group(2), m.group(3)
            name = f"{group}:{artifact}"
            packages[name] = {"name": name, "version": version}
    return sorted(packages.values(), key=lambda x: x["name"].lower())


def get_maven_vulns():
    """Return {pkg_name: [{id, severity, fix_version, description}]} via OWASP dependency-check Maven plugin."""
    if not Path("pom.xml").exists():
        return {}
    report = Path("target/dependency-check-report.json")
    _run([
        "mvn", "org.owasp:dependency-check-maven:check",
        "-DfailBuildOnCVSS=11", "-Dformat=JSON", "-DoutputDirectory=target/", "-q",
    ])
    return _parse_owasp_report(report)


# ── Java / Gradle ──────────────────────────────────────────────────────────────

def get_gradle_packages():
    """Return [{name, version}] from gradle dependencies output."""
    if not (Path("build.gradle").exists() or Path("build.gradle.kts").exists()):
        return []
    gradle_cmd = "./gradlew" if Path("gradlew").exists() else "gradle"
    stdout, rc = _run([gradle_cmd, "dependencies", "--configuration", "runtimeClasspath", "-q"])
    if rc == 127 or not stdout:
        print("  ⚠️  Gradle not available — install Gradle to list Java dependencies")
        return []
    packages = {}
    for line in stdout.splitlines():
        m = re.match(r"[+\\|]\s*---\s+([^:\s]+):([^:\s]+):([^\s:(]+)", line)
        if m:
            group, artifact, version = m.group(1), m.group(2), m.group(3)
            name = f"{group}:{artifact}"
            packages[name] = {"name": name, "version": version}
    return sorted(packages.values(), key=lambda x: x["name"].lower())


def get_gradle_vulns():
    """Return {pkg_name: [{id, severity, fix_version, description}]} via OWASP dependency-check Gradle plugin."""
    if not (Path("build.gradle").exists() or Path("build.gradle.kts").exists()):
        return {}
    gradle_cmd = "./gradlew" if Path("gradlew").exists() else "gradle"
    report = Path("build/reports/dependency-check-report.json")
    _run([gradle_cmd, "dependencyCheckAnalyze", "-q"])
    return _parse_owasp_report(report)


# ── OWASP report parser (Maven + Gradle) ─────────────────────────────────────

def _parse_owasp_report(report_path):
    """Parse an OWASP dependency-check JSON report into {pkg_name: [{id, severity, ...}]}."""
    if not report_path.exists():
        print(f"  ⚠️  OWASP report not found at {report_path} — install dependency-check plugin/CLI")
        return {}
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    vulns = {}
    for dep in data.get("dependencies", []):
        if not dep.get("vulnerabilities"):
            continue
        name = dep.get("fileName", "unknown")
        for pkg in dep.get("packages", []):
            m = re.match(r"pkg:maven/([^/]+)/([^@]+)", pkg.get("id", ""))
            if m:
                name = f"{m.group(1)}:{m.group(2)}"
                break
        for v in dep["vulnerabilities"]:
            severity = v.get("severity", "unknown").lower()
            vuln_id = v.get("name", "?")
            description = v.get("description", "")[:120]
            vulns.setdefault(name.lower(), []).append({
                "id": vuln_id,
                "severity": severity,
                "fix_version": "—",
                "description": description,
            })
    return vulns


# ── Policy ───────────────────────────────────────────────────────────────────

_DEFAULT_POLICY = {
    "allowed_licenses": [
        "MIT", "MIT License", "Apache-2.0", "Apache Software License",
        "BSD-2-Clause", "BSD-3-Clause", "BSD License",
        "ISC", "PSF-2.0", "Python Software Foundation License",
        "Python-2.0", "0BSD", "Unlicense", "WTFPL",
        "Artistic-2.0", "Zlib", "MPL-2.0", "Mozilla Public License 2.0",
    ],
    "rejected_packages": [],
    "max_versions_per_package": 1,
    "require_fix_for_severity": ["critical", "high"],
}


def _load_policy():
    """Load sbom-policy.json from repo root, falling back to defaults."""
    policy_path = Path("sbom-policy.json")
    if policy_path.exists():
        try:
            data = json.loads(policy_path.read_text(encoding="utf-8"))
            merged = dict(_DEFAULT_POLICY)
            merged.update(data)
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULT_POLICY)


def _check_policy(policy, all_pkgs, all_vulns, licenses, meta_cache):
    """Check policy compliance. Returns list of {rule, status, details} dicts."""
    results = []

    # 1. Rejected packages in use
    rejected = set(r.lower() for r in policy.get("rejected_packages", []))
    found_rejected = [p for p in all_pkgs if p["name"].lower() in rejected]
    if found_rejected:
        names = ", ".join(f"`{p['name']}`" for p in found_rejected)
        results.append({"rule": "Rejected packages in use", "status": "⚠️ Fail", "details": names})
    else:
        results.append({"rule": "Rejected packages in use", "status": "✅ Pass", "details": "None found"})

    # 2. License violations
    allowed = set(a.lower() for a in policy.get("allowed_licenses", []))
    violations = []
    for pkg_name, lic in licenses.items():
        if lic.lower() not in allowed and lic != "Unknown":
            violations.append(f"`{pkg_name}` ({lic})")
    if violations:
        results.append({
            "rule": "License violations",
            "status": f"⚠️ {len(violations)} violation{'s' if len(violations) != 1 else ''}",
            "details": ", ".join(violations[:10]) + (" ..." if len(violations) > 10 else ""),
        })
    else:
        results.append({"rule": "License violations", "status": "✅ Pass", "details": "All licenses allowed"})

    # 3. Unfixed critical/high CVEs
    require_fix = set(s.lower() for s in policy.get("require_fix_for_severity", []))
    unfixed = []
    for vulns_dict in all_vulns:
        for pkg_name, vlist in vulns_dict.items():
            for v in vlist:
                sev = v.get("severity", "").lower()
                meta = meta_cache.get(v["id"], {})
                cvss_label = (meta.get("cvss_label") or "").lower()
                if (sev in require_fix or cvss_label in require_fix) and v.get("fix_version") not in ("—", "None", ""):
                    unfixed.append(f"`{v['id']}` ({pkg_name}) — fix: {v['fix_version']}")
    if unfixed:
        results.append({
            "rule": "Unfixed critical/high CVEs with available fix",
            "status": f"⚠️ {len(unfixed)} actionable",
            "details": ", ".join(unfixed[:5]) + (" ..." if len(unfixed) > 5 else ""),
        })
    else:
        results.append({
            "rule": "Unfixed critical/high CVEs with available fix",
            "status": "✅ Pass",
            "details": "No actionable fixes pending",
        })

    return results


# ── Impact analysis registry ─────────────────────────────────────────────────
# Keyed by vuln ID (CVE / PYSEC) or by package name for npm advisory slugs.
# Add an entry here whenever a new vulnerability appears in the SBOM.
# Vulns without an entry are marked "⚪ Unknown — review manually".

_IMPACT = {
    # ── pip ──────────────────────────────────────────────────────────────────
    # pip is invoked ONLY at build time (CI `pip install` / local venv setup).
    # The production Docker container runs gunicorn + nginx and never calls pip.
    "CVE-2025-8869": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "pip is only invoked during Docker image builds and local `pip install` runs. "
            "The production container (gunicorn + nginx) never calls pip. "
            "Exploitation requires supplying a maliciously crafted tar archive to the pip "
            "process during installation — not reachable through normal application traffic."
        ),
    },
    "CVE-2026-1703": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "Same build-time-only scope as CVE-2025-8869. Wheel extraction happens only "
            "during `pip install`; no wheel archives are processed at runtime. "
            "Risk is limited to supply-chain compromise of a dependency during CI/CD."
        ),
    },
    # ── setuptools ───────────────────────────────────────────────────────────
    # setuptools is a packaging tool.  api/app.py never imports or calls it at runtime.
    "PYSEC-2022-43012": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "setuptools is used only during package installation. "
            "The Flask application (`api/app.py`) never imports or invokes setuptools at "
            "runtime. This ReDoS/HTML-injection vuln requires feeding maliciously crafted "
            "package metadata to setuptools during `pip install` — not possible via app traffic."
        ),
    },
    "PYSEC-2025-49": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "`PackageIndex` is the setuptools feature for downloading packages from PyPI. "
            "Radio Calico never calls PackageIndex at runtime; it is only exercised during "
            "dependency installation in CI or dev. Production containers do not run pip or "
            "setuptools after the image is built."
        ),
    },
    "CVE-2024-6345": {
        "rating": "🟡 Low (build-time only)",
        "analysis": (
            "The most severe setuptools vuln: RCE if `package_index` fetches from a "
            "compromised source. The production Flask app never invokes `package_index`, "
            "so runtime risk is zero. However, the attack surface exists during CI `pip install` "
            "if a dependency index is compromised. "
            "Recommend upgrading setuptools to ≥ 70.0.0 in the dev venv to close this gap."
        ),
    },
    # ── npm / jest transitive deps ───────────────────────────────────────────
    # All four npm vulns are transitive test-only dependencies pulled in by Jest.
    # None are present in the production Docker image (no `npm ci` in prod).
    # None are loaded by the Radio Calico frontend (static/js/player.js).
    "@tootallnate/once": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "Transitive dependency of Jest (dev tooling only). "
            "Not installed in the production Docker image. "
            "No production code path touches `@tootallnate/once`. "
            "Exploitation would require control over the test environment itself."
        ),
    },
    "http-proxy-agent": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "Transitive test dependency pulled in by Jest → jsdom → http-proxy-agent. "
            "Radio Calico does not use HTTP proxying anywhere — all external requests "
            "(CloudFront, iTunes API) use standard `fetch()` or `httpx`. "
            "Not present in the production runtime environment."
        ),
    },
    "jest-environment-jsdom": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "jsdom is a simulated browser DOM used exclusively by Jest unit tests "
            "(`player.test.js`). Never deployed to production and not reachable by end users "
            "or external traffic. Exploitation would require an attacker to control test input, "
            "which is not a realistic threat model."
        ),
    },
    "jsdom": {
        "rating": "🟢 Not Applicable",
        "analysis": (
            "Same scope as jest-environment-jsdom. jsdom is a test-only dependency — "
            "no jsdom code runs in the browser or on the production server."
        ),
    },
}

# ── Formatting ────────────────────────────────────────────────────────────────

_SEV_RANK = {"critical": 4, "high": 3, "moderate": 2, "medium": 2, "low": 1}
_SEV_ICON = {"critical": "🔴", "high": "🟠", "moderate": "🟡", "medium": "🟡", "low": "🔵"}


def _cell_py(vulns):
    if not vulns:
        return "✅ None"
    ids = ", ".join(f"`{v['id']}`" for v in vulns[:2])
    if len(vulns) > 2:
        ids += f" +{len(vulns) - 2} more"
    return f"⚠️ {ids}"


def _cell_npm(vulns):
    if not vulns:
        return "✅ None"
    top = max(vulns, key=lambda v: _SEV_RANK.get(v.get("severity", "low"), 1))
    sev = top.get("severity", "low")
    icon = _SEV_ICON.get(sev, "⚪")
    ids = ", ".join(f"`{v['id']}`" for v in vulns[:2])
    if len(vulns) > 2:
        ids += f" +{len(vulns) - 2} more"
    return f"{icon} {sev.capitalize()} — {ids}"



# ── MySQL persistence ────────────────────────────────────────────────────────

def _save_to_db(project, today, ecosystems, meta_cache, impact_entries):
    """Save SBOM data to MySQL. Requires pymysql and DB env vars."""
    try:
        import pymysql
    except ImportError:
        print("  ⚠️  pymysql not installed — skipping DB save (pip install pymysql)")
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(Path("api/.env"))
    except ImportError:
        pass

    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "radiocalico"),
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            # Insert scan
            total_pkgs = sum(len(e["packages"]) for e in ecosystems)
            total_vulns = sum(
                sum(len(v) for v in e["vulns"].values()) for e in ecosystems
            )
            cur.execute(
                "INSERT INTO sbom_scans (project, scan_date, total_packages, total_vulns) "
                "VALUES (%s, %s, %s, %s)",
                (project, today, total_pkgs, total_vulns),
            )
            scan_id = cur.lastrowid

            # Insert packages
            for eco in ecosystems:
                for pkg in eco["packages"]:
                    cur.execute(
                        "INSERT INTO sbom_packages (scan_id, ecosystem, name, version, license, latest_version) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (scan_id, eco["ecosystem"], pkg["name"], pkg["version"],
                         eco.get("licenses", {}).get(pkg["name"].lower(), ""),
                         eco.get("outdated", {}).get(pkg["name"].lower(), "")),
                    )

            # Insert vulnerabilities
            for eco in ecosystems:
                for pkg_name, vlist in eco["vulns"].items():
                    for v in vlist:
                        meta = meta_cache.get(v["id"], {})
                        pub = meta.get("published", "")
                        mod = meta.get("modified", "")
                        cur.execute(
                            "INSERT INTO sbom_vulnerabilities "
                            "(scan_id, package_name, ecosystem, vuln_id, severity, "
                            "cvss_score, cvss_vector, published_date, modified_date, "
                            "fix_version, reference_url, description) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (scan_id, pkg_name, eco["ecosystem"], v["id"],
                             v.get("severity", ""),
                             meta.get("cvss_score"),
                             meta.get("cvss_vector", ""),
                             pub if pub != "—" else None,
                             mod if mod != "—" else None,
                             v.get("fix_version", "—"),
                             meta.get("ref_url", ""),
                             v.get("description", "")[:500]),
                        )

            # Insert impact analysis
            for name, v, rating, analysis in impact_entries:
                cur.execute(
                    "INSERT INTO sbom_impact_analysis "
                    "(scan_id, vuln_id, package_name, rating, analysis) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE rating=VALUES(rating), analysis=VALUES(analysis)",
                    (scan_id, v["id"], name, rating, analysis),
                )

            conn.commit()
            print(f"  ✅ Saved SBOM scan #{scan_id} to MySQL ({project}, {today})")
    except Exception as e:
        print(f"  ⚠️  DB save failed: {e}")
    finally:
        conn.close()


# ── Document builder ──────────────────────────────────────────────────────────

def _scan_python(save_db):
    """Scan Python ecosystem: packages, vulns, licenses, outdated."""
    print("Scanning Python packages + vulnerabilities...")
    pkgs = get_python_packages()
    vulns = get_python_vulns()
    licenses = get_python_licenses()
    outdated = get_python_outdated() if save_db else {}
    return {"packages": pkgs, "vulns": vulns, "licenses": licenses, "outdated": outdated}


def _scan_nodejs(save_db):
    """Scan Node.js ecosystem: packages, vulns, licenses, outdated."""
    print("Scanning Node.js packages + vulnerabilities...")
    pkgs = get_npm_packages()
    vulns = get_npm_vulns()
    licenses = get_npm_licenses()
    outdated = get_npm_outdated() if save_db else {}
    return {"packages": pkgs, "vulns": vulns, "licenses": licenses, "outdated": outdated}


def _scan_dotnet():
    """Scan .NET ecosystem: packages + vulns."""
    print("Scanning .NET packages + vulnerabilities...")
    return {"packages": get_dotnet_packages(), "vulns": get_dotnet_vulns(),
            "licenses": {}, "outdated": {}}


def _scan_maven():
    """Scan Maven ecosystem: packages + vulns."""
    print("Scanning Java/Maven packages + vulnerabilities...")
    return {"packages": get_maven_packages(), "vulns": get_maven_vulns(),
            "licenses": {}, "outdated": {}}


def _scan_gradle():
    """Scan Gradle ecosystem: packages + vulns."""
    print("Scanning Java/Gradle packages + vulnerabilities...")
    return {"packages": get_gradle_packages(), "vulns": get_gradle_vulns(),
            "licenses": {}, "outdated": {}}


_EMPTY_ECO = {"packages": [], "vulns": {}, "licenses": {}, "outdated": {}}


def generate_sbom(today, project, save_db=False):
    # Early ecosystem detection — skip ecosystems without project files
    has_dotnet = _find_files("*.csproj", "*.fsproj", "*.sln")
    has_maven = Path("pom.xml").exists()
    has_gradle = Path("build.gradle").exists() or Path("build.gradle.kts").exists()

    # Parallel scanning of all detected ecosystems
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_scan_python, save_db): "python",
            executor.submit(_scan_nodejs, save_db): "nodejs",
        }
        if has_dotnet:
            futures[executor.submit(_scan_dotnet)] = "dotnet"
        if has_maven:
            futures[executor.submit(_scan_maven)] = "maven"
        if has_gradle:
            futures[executor.submit(_scan_gradle)] = "gradle"

        for future in as_completed(futures):
            eco_name = futures[future]
            results[eco_name] = future.result()

    # Unpack results
    py = results["python"]
    py_pkgs, py_vulns, py_licenses, py_outdated = py["packages"], py["vulns"], py["licenses"], py["outdated"]
    npm = results["nodejs"]
    npm_pkgs, npm_vulns, npm_licenses, npm_outdated = npm["packages"], npm["vulns"], npm["licenses"], npm["outdated"]
    dotnet = results.get("dotnet", _EMPTY_ECO)
    dotnet_pkgs, dotnet_vulns = dotnet["packages"], dotnet["vulns"]
    maven = results.get("maven", _EMPTY_ECO)
    maven_pkgs, maven_vulns = maven["packages"], maven["vulns"]
    gradle = results.get("gradle", _EMPTY_ECO)
    gradle_pkgs, gradle_vulns = gradle["packages"], gradle["vulns"]

    # Policy
    print("Loading policy (sbom-policy.json)...")
    policy = _load_policy()

    py_vuln_n = sum(len(v) for v in py_vulns.values())
    npm_vuln_n = sum(len(v) for v in npm_vulns.values())
    dotnet_vuln_n = sum(len(v) for v in dotnet_vulns.values())
    maven_vuln_n = sum(len(v) for v in maven_vulns.values())
    gradle_vuln_n = sum(len(v) for v in gradle_vulns.values())
    total_vuln_n = py_vuln_n + npm_vuln_n + dotnet_vuln_n + maven_vuln_n + gradle_vuln_n
    total_pkgs = len(py_pkgs) + len(npm_pkgs) + len(dotnet_pkgs) + len(maven_pkgs) + len(gradle_pkgs)

    # Fetch enriched metadata from OSV.dev (with file-based cache)
    meta_cache = _load_osv_cache()
    if total_vuln_n:
        print("Fetching vulnerability metadata (OSV.dev — CVSS, dates, links)...")
        for vulns_dict in (py_vulns, npm_vulns, dotnet_vulns, maven_vulns, gradle_vulns):
            for vlist in vulns_dict.values():
                for v in vlist:
                    _get_vuln_metadata(v["id"], meta_cache)
        _save_osv_cache(meta_cache)

    # Policy check
    all_pkgs = [
        *[{"name": p["name"], "ecosystem": "python"} for p in py_pkgs],
        *[{"name": p["name"], "ecosystem": "nodejs"} for p in npm_pkgs],
        *[{"name": p["name"], "ecosystem": "dotnet"} for p in dotnet_pkgs],
        *[{"name": p["name"], "ecosystem": "maven"} for p in maven_pkgs],
        *[{"name": p["name"], "ecosystem": "gradle"} for p in gradle_pkgs],
    ]
    all_licenses = {**py_licenses, **npm_licenses}
    policy_results = _check_policy(
        policy, all_pkgs,
        [py_vulns, npm_vulns, dotnet_vulns, maven_vulns, gradle_vulns],
        all_licenses, meta_cache,
    )

    L = []

    # ── Header ──
    pkg_breakdown_parts = [f"{len(py_pkgs)} Python", f"{len(npm_pkgs)} Node.js"]
    if dotnet_pkgs:
        pkg_breakdown_parts.append(f"{len(dotnet_pkgs)} .NET")
    if maven_pkgs:
        pkg_breakdown_parts.append(f"{len(maven_pkgs)} Maven")
    if gradle_pkgs:
        pkg_breakdown_parts.append(f"{len(gradle_pkgs)} Gradle")
    pkg_breakdown = " · ".join(pkg_breakdown_parts)

    vuln_breakdown_parts = [f"{py_vuln_n} Python", f"{npm_vuln_n} Node.js"]
    if dotnet_pkgs:
        vuln_breakdown_parts.append(f"{dotnet_vuln_n} .NET")
    if maven_pkgs:
        vuln_breakdown_parts.append(f"{maven_vuln_n} Maven")
    if gradle_pkgs:
        vuln_breakdown_parts.append(f"{gradle_vuln_n} Gradle")
    vuln_breakdown = " · ".join(vuln_breakdown_parts)

    L += [
        "# Software Bill of Materials (SBOM)",
        "",
        f"**Project**: {project} &nbsp;·&nbsp; "
        f"**Last updated**: {today} &nbsp;·&nbsp; "
        "generated by `scripts/generate_sbom.py`",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| **Project** | {project} |",
        f"| **Total packages** | {total_pkgs} "
        f"({pkg_breakdown}) |",
        "| **Vulnerabilities** | "
        + (
            "✅ None detected"
            if not total_vuln_n
            else f"⚠️ {total_vuln_n} detected "
                 f"({vuln_breakdown})"
        )
        + " |",
        "| **Python scanner** | `pip-audit` (GHSA / OSV database) |",
        "| **Node.js scanner** | `npm audit` (npm advisory database) |",
    ]
    if dotnet_pkgs:
        L.append("| **.NET scanner** | `dotnet list package --vulnerable --include-transitive` (built-in .NET CLI) |")
    if maven_pkgs:
        L.append("| **Java/Maven scanner** | OWASP Dependency-Check Maven plugin (`mvn org.owasp:dependency-check-maven:check`) |")
    if gradle_pkgs:
        L.append("| **Java/Gradle scanner** | OWASP Dependency-Check Gradle plugin (`gradle dependencyCheckAnalyze`) |")
    L += [
        f"| **Scan date** | {today} |",
        "",
    ]

    # ── Python packages ──
    L += [
        "---",
        "",
        f"## Python Packages ({len(py_pkgs)})",
        "",
        "Source: `api/requirements.txt` + `api/requirements-dev.txt` "
        "&nbsp;·&nbsp; Scanner: `pip-audit`",
        "",
        "| Package | Version | Vulnerabilities |",
        "| --- | --- | --- |",
    ]
    for pkg in sorted(py_pkgs, key=lambda x: x["name"].lower()):
        cell = _cell_py(py_vulns.get(pkg["name"].lower(), []))
        L.append(f"| `{pkg['name']}` | {pkg['version']} | {cell} |")
    L.append("")

    # ── Node.js packages ──
    L += [
        "---",
        "",
        f"## Node.js Packages ({len(npm_pkgs)})",
        "",
        "Source: `package.json` &nbsp;·&nbsp; Scanner: `npm audit`",
        "",
        "| Package | Version | Vulnerabilities |",
        "| --- | --- | --- |",
    ]
    for pkg in sorted(npm_pkgs, key=lambda x: x["name"].lower()):
        cell = _cell_npm(npm_vulns.get(pkg["name"], []))
        L.append(f"| `{pkg['name']}` | {pkg['version']} | {cell} |")
    L.append("")

    # ── .NET packages ──
    if dotnet_pkgs:
        L += [
            "---", "",
            f"## .NET / NuGet Packages ({len(dotnet_pkgs)})",
            "",
            "Source: `*.csproj` / `*.sln` &nbsp;·&nbsp; Scanner: `dotnet list package --vulnerable`",
            "",
            "| Package | Version | Vulnerabilities |",
            "| --- | --- | --- |",
        ]
        for pkg in dotnet_pkgs:
            cell = _cell_npm(dotnet_vulns.get(pkg["name"].lower(), []))
            L.append(f"| `{pkg['name']}` | {pkg['version']} | {cell} |")
        L.append("")

    # ── Maven packages ──
    if maven_pkgs:
        L += [
            "---", "",
            f"## Java / Maven Packages ({len(maven_pkgs)})",
            "",
            "Source: `pom.xml` &nbsp;·&nbsp; Scanner: OWASP Dependency-Check Maven plugin",
            "",
            "| Package | Version | Vulnerabilities |",
            "| --- | --- | --- |",
        ]
        for pkg in maven_pkgs:
            cell = _cell_npm(maven_vulns.get(pkg["name"].lower(), []))
            L.append(f"| `{pkg['name']}` | {pkg['version']} | {cell} |")
        L.append("")

    # ── Gradle packages ──
    if gradle_pkgs:
        L += [
            "---", "",
            f"## Java / Gradle Packages ({len(gradle_pkgs)})",
            "",
            "Source: `build.gradle` / `build.gradle.kts` &nbsp;·&nbsp; Scanner: OWASP Dependency-Check Gradle plugin",
            "",
            "| Package | Version | Vulnerabilities |",
            "| --- | --- | --- |",
        ]
        for pkg in gradle_pkgs:
            cell = _cell_npm(gradle_vulns.get(pkg["name"].lower(), []))
            L.append(f"| `{pkg['name']}` | {pkg['version']} | {cell} |")
        L.append("")

    # ── Vulnerability details (enriched) ──
    if total_vuln_n:
        L += ["---", "", "## Vulnerability Details", ""]

        def _vuln_detail_rows(vulns_dict, header_label, show_severity=False):
            if not vulns_dict:
                return
            cols = "| Package | Vuln ID | CVSS | Created | Modified | Fix Version | Link | Description |"
            sep = "| --- | --- | --- | --- | --- | --- | --- | --- |"
            if show_severity:
                cols = "| Package | Vuln ID | Severity | CVSS | Created | Modified | Fix Version | Link | Description |"
                sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
            L.extend([f"### {header_label}", "", cols, sep])
            for name in sorted(vulns_dict):
                for v in vulns_dict[name]:
                    meta = meta_cache.get(v["id"], {})
                    pub = meta.get("published", "—")
                    mod = meta.get("modified", "—")
                    cvss = meta.get("cvss_score")
                    cvss_label = meta.get("cvss_label", "—")
                    cvss_str = f"{cvss} ({cvss_label})" if cvss is not None else "—"
                    fix = v.get("fix_version", "—")
                    ref = meta.get("ref_url", "")
                    link = f"[Details]({ref})" if ref else "—"
                    if show_severity:
                        L.append(
                            f"| `{name}` | `{v['id']}` | {v.get('severity', '—')} "
                            f"| {cvss_str} | {pub} | {mod} | {fix} | {link} | {v['description']} |"
                        )
                    else:
                        L.append(
                            f"| `{name}` | `{v['id']}` | {cvss_str} | {pub} "
                            f"| {mod} | {fix} | {link} | {v['description']} |"
                        )
            L.append("")

        _vuln_detail_rows(py_vulns, "Python")
        _vuln_detail_rows(npm_vulns, "Node.js", show_severity=True)
        _vuln_detail_rows(dotnet_vulns, ".NET / NuGet", show_severity=True)
        _vuln_detail_rows(maven_vulns, "Java / Maven", show_severity=True)
        _vuln_detail_rows(gradle_vulns, "Java / Gradle", show_severity=True)

    # ── Impact analysis ──
    L += [
        "---",
        "",
        "## Impact Analysis",
        "",
        "> Real-world assessment of each vulnerability in the context of the "
        f"{project} deployment. A vulnerability in a library does not always mean "
        "the application is affected — it depends on whether the vulnerable code "
        "path is reachable at runtime.",
        "",
        "### Rating Legend",
        "",
        "| Rating | Meaning |",
        "| --- | --- |",
        "| 🟢 Not Applicable | Vulnerable code path unreachable in this deployment |",
        "| 🟡 Low (build-time only) | Risk exists during CI/dev builds only, not at runtime |",
        "| 🟠 Moderate | Partially affects the app — monitor and patch when convenient |",
        "| 🔴 High | Directly exploitable in the current deployment — patch immediately |",
        "| ⚪ Unknown | No analysis yet — review manually against the codebase |",
        "",
    ]

    impact_entries = []
    all_vuln_pairs = []
    for vulns_dict in (py_vulns, npm_vulns, dotnet_vulns, maven_vulns, gradle_vulns):
        for name in sorted(vulns_dict):
            for v in vulns_dict[name]:
                all_vuln_pairs.append((name, v))

    if all_vuln_pairs:
        L += [
            "| Package | Vuln ID | Impact Rating | Analysis |",
            "| --- | --- | --- | --- |",
        ]
        for name, v in all_vuln_pairs:
            vuln_id = v["id"]
            impact = _IMPACT.get(vuln_id) or _IMPACT.get(name)
            if impact:
                rating = impact["rating"]
                analysis = impact["analysis"]
            else:
                rating = "⚪ Unknown"
                analysis = (
                    "No impact analysis available — review manually "
                    f"against the {project} codebase."
                )
            L.append(f"| `{name}` | `{vuln_id}` | {rating} | {analysis} |")
            impact_entries.append((name, v, rating, analysis))
        L.append("")
    else:
        L += ["✅ No vulnerabilities to analyse.", ""]

    # ── Policy Compliance ──
    L += [
        "---",
        "",
        "## Policy Compliance",
        "",
        "> Checked against `sbom-policy.json` (falls back to built-in defaults if file absent).",
        "",
        "| Rule | Status | Details |",
        "| --- | --- | --- |",
    ]
    for r in policy_results:
        L.append(f"| {r['rule']} | {r['status']} | {r['details']} |")
    L.append("")

    # ── Footer ──
    L += [
        "---",
        "",
        "> **Remediation**: update the package version in `api/requirements.txt`, "
        "`package.json`, a `.csproj` file, or `pom.xml`/`build.gradle`, "
        "then run `make generate-sbom` to verify the fix.",
        "",
        "*Refresh: `make generate-sbom` locally, "
        "or open a PR to main (CI auto-updates `docs/SBOM.md`).*",
        "",
    ]

    content = "\n".join(L)
    if not content.endswith("\n"):
        content += "\n"

    path = Path("docs/SBOM.md")
    path.parent.mkdir(exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(
        f"✅ Generated {path}: {total_pkgs} packages, "
        f"{total_vuln_n} vulnerabilit{'y' if total_vuln_n == 1 else 'ies'}"
    )

    # ── MySQL persistence ──
    if save_db:
        ecosystems = [
            {"ecosystem": "python", "packages": py_pkgs, "vulns": py_vulns, "licenses": py_licenses, "outdated": py_outdated},
            {"ecosystem": "nodejs", "packages": npm_pkgs, "vulns": npm_vulns, "licenses": npm_licenses, "outdated": npm_outdated},
        ]
        if dotnet_pkgs:
            ecosystems.append({"ecosystem": "dotnet", "packages": dotnet_pkgs, "vulns": dotnet_vulns, "licenses": {}, "outdated": {}})
        if maven_pkgs:
            ecosystems.append({"ecosystem": "maven", "packages": maven_pkgs, "vulns": maven_vulns, "licenses": {}, "outdated": {}})
        if gradle_pkgs:
            ecosystems.append({"ecosystem": "gradle", "packages": gradle_pkgs, "vulns": gradle_vulns, "licenses": {}, "outdated": {}})
        _save_to_db(project, today, ecosystems, meta_cache, impact_entries)


def main():
    parser = argparse.ArgumentParser(
        description="Generate SBOM.md from installed packages and vulnerability scans"
    )
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Date in YYYY-MM-DD format (default: today UTC)",
    )
    parser.add_argument(
        "--project",
        default=Path(".").resolve().name,
        help="Project name for SBOM header and DB storage (default: repo directory name)",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Save scan results to MySQL (requires pymysql + DB env vars)",
    )
    args = parser.parse_args()
    generate_sbom(args.date, args.project, args.save_db)


if __name__ == "__main__":
    main()
