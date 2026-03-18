#!/usr/bin/env python3
"""Generate SBOM.md — Software Bill of Materials with vulnerability data.

Collects all installed Python and Node.js packages, scans each for known
vulnerabilities, and writes a Markdown summary to SBOM.md at the repo root.

Usage (from repo root, with api venv active or in CI after pip install):
    python scripts/generate_sbom.py [--date YYYY-MM-DD]

Scanners:
    Python  — pip-audit (GHSA / OSV database)
    Node.js — npm audit (npm advisory database)

pip-audit must be installed:
    pip install pip-audit
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
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


def _get_published_date(vuln_id: str, cache: dict) -> str:
    """Return the published date (YYYY-MM-DD) for a vuln ID from OSV.dev, or '—'."""
    if vuln_id in cache:
        return cache[vuln_id]
    url = f"https://api.osv.dev/v1/vulns/{vuln_id}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        published = data.get("published", "")
        result = published[:10] if published else "—"
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        result = "—"
    cache[vuln_id] = result
    return result


# ── Python ────────────────────────────────────────────────────────────────────

def get_python_packages():
    """Return [{name, version}] for all installed packages."""
    data, ok = _run_json([sys.executable, "-m", "pip", "list", "--format=json"])
    return data if ok and isinstance(data, list) else []


def get_python_vulns():
    """Return {pkg_name_lower: [{id, fix_version, description}]} via pip-audit --format=json."""
    # pip-audit JSON: {"dependencies": [{"name":..,"version":..,"vulns":[{"id":..,"fix_versions":[..],"description":..}]}]}
    data, ok = _run_json(["pip-audit", "--format=json"])
    if not ok:
        # fallback: try python -m pip_audit
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
    # npm audit exits non-zero when vulns exist, so we ignore rc
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


# ── Document builder ──────────────────────────────────────────────────────────

def generate_sbom(today: str) -> None:
    print("Collecting Python packages (pip list)...")
    py_pkgs = get_python_packages()
    print("Scanning Python vulnerabilities (pip-audit)...")
    py_vulns = get_python_vulns()
    print("Collecting Node.js packages (npm list)...")
    npm_pkgs = get_npm_packages()
    print("Scanning Node.js vulnerabilities (npm audit)...")
    npm_vulns = get_npm_vulns()

    py_vuln_n = sum(len(v) for v in py_vulns.values())
    npm_vuln_n = sum(len(v) for v in npm_vulns.values())
    total_vuln_n = py_vuln_n + npm_vuln_n
    total_pkgs = len(py_pkgs) + len(npm_pkgs)

    # Fetch published dates from OSV.dev for all unique vuln IDs
    date_cache: dict = {}
    if total_vuln_n:
        print("Fetching vulnerability published dates (OSV.dev)...")
        for vulns_dict in (py_vulns, npm_vulns):
            for vlist in vulns_dict.values():
                for v in vlist:
                    _get_published_date(v["id"], date_cache)

    L = []

    # ── Header ──
    L += [
        "# Software Bill of Materials (SBOM)",
        "",
        f"**Last updated**: {today} &nbsp;·&nbsp; "
        "generated by `scripts/generate_sbom.py`",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| **Total packages** | {total_pkgs} "
        f"({len(py_pkgs)} Python · {len(npm_pkgs)} Node.js) |",
        f"| **Vulnerabilities** | "
        + (
            "✅ None detected"
            if not total_vuln_n
            else f"⚠️ {total_vuln_n} detected "
                 f"({py_vuln_n} Python · {npm_vuln_n} Node.js)"
        )
        + " |",
        "| **Python scanner** | `pip-audit` (GHSA / OSV database) |",
        "| **Node.js scanner** | `npm audit` (npm advisory database) |",
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

    # ── Vulnerability details ──
    if total_vuln_n:
        L += ["---", "", "## Vulnerability Details", ""]

        if py_vulns:
            L += [
                "### Python",
                "",
                "| Package | Vuln ID | Published | Fix Version | Description |",
                "| --- | --- | --- | --- | --- |",
            ]
            for name in sorted(py_vulns):
                for v in py_vulns[name]:
                    published = date_cache.get(v["id"], "—")
                    fix = v.get("fix_version", "—")
                    L.append(
                        f"| `{name}` | `{v['id']}` | {published} | {fix} | {v['description']} |"
                    )
            L.append("")

        if npm_vulns:
            L += [
                "### Node.js",
                "",
                "| Package | Vuln ID | Severity | Published | Fix Version | Description |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for name in sorted(npm_vulns):
                for v in npm_vulns[name]:
                    published = date_cache.get(v["id"], "—")
                    fix = v.get("fix_version", "—")
                    L.append(
                        f"| `{name}` | `{v['id']}` | {v.get('severity', '—')} "
                        f"| {published} | {fix} | {v['description']} |"
                    )
            L.append("")

    # ── Footer ──
    L += [
        "---",
        "",
        "> **Remediation**: update the package version in `api/requirements.txt` "
        "or `package.json`, then run `make generate-sbom` to verify the fix.",
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate SBOM.md from installed packages and vulnerability scans"
    )
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Date in YYYY-MM-DD format (default: today UTC)",
    )
    args = parser.parse_args()
    generate_sbom(args.date)


if __name__ == "__main__":
    main()