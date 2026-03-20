"""Unit tests for scripts/generate_sbom.py — ecosystem support + SBOM enrichment.

Tests ecosystem detection, package/vulnerability parsing, CVSS v3 base score
calculation, OSV metadata enrichment, and policy compliance.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_sbom import (
    _check_policy,
    _cvss_roundup,
    _find_files,
    _load_osv_cache,
    _load_policy,
    _parse_cvss_base_score,
    _parse_owasp_report,
    _save_osv_cache,
    get_dotnet_packages,
    get_dotnet_vulns,
    get_gradle_packages,
    get_gradle_vulns,
    get_maven_packages,
    get_maven_vulns,
    get_npm_licenses,
    get_npm_outdated,
    get_python_licenses,
    get_python_outdated,
)

# ── _find_files ───────────────────────────────────────────────────────────────


def test_find_files_returns_false_for_nonexistent_pattern(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _find_files("*.csproj") is False


def test_find_files_returns_true_when_file_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "MyApp.csproj").write_text("<Project/>")
    assert _find_files("*.csproj") is True


def test_find_files_skips_node_modules(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    nm = tmp_path / "node_modules" / "some_pkg"
    nm.mkdir(parents=True)
    (nm / "Fake.csproj").write_text("<Project/>")
    assert _find_files("*.csproj") is False


# ── CVSS v3 Base Score Calculator ────────────────────────────────────────────


def test_cvss_roundup():
    assert _cvss_roundup(4.0) == 4.0
    assert _cvss_roundup(4.01) == 4.1
    assert _cvss_roundup(4.09) == 4.1
    assert _cvss_roundup(0.0) == 0.0


def test_parse_cvss_high_score():
    """CVSS:3.0/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H should be 8.8 High."""
    score, label = _parse_cvss_base_score("CVSS:3.0/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H")
    assert score == 8.8
    assert label == "High"


def test_parse_cvss_critical_score():
    """CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H should be 10.0 Critical."""
    score, label = _parse_cvss_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H")
    assert score == 10.0
    assert label == "Critical"


def test_parse_cvss_low_score():
    """CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N should be low."""
    score, label = _parse_cvss_base_score("CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N")
    assert score is not None
    assert score < 4.0
    assert label == "Low"


def test_parse_cvss_none_impact():
    """All CIA=N should yield 0.0 None."""
    score, label = _parse_cvss_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N")
    assert score == 0.0
    assert label == "None"


def test_parse_cvss_invalid_vector():
    score, label = _parse_cvss_base_score("not-a-vector")
    assert score is None
    assert label == "—"


def test_parse_cvss_empty_string():
    score, label = _parse_cvss_base_score("")
    assert score is None
    assert label == "—"


def test_parse_cvss_medium_scope_changed():
    """CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:N should be Medium (6.4)."""
    score, label = _parse_cvss_base_score("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:N")
    assert score is not None
    assert 4.0 <= score < 7.0
    assert label == "Medium"


# ── _get_vuln_metadata ───────────────────────────────────────────────────────


def test_get_vuln_metadata_returns_cached(tmp_path):
    from generate_sbom import _get_vuln_metadata

    cache = {
        "CVE-TEST": {
            "published": "2024-01-01",
            "modified": "2024-06-01",
            "cvss_score": 7.5,
            "cvss_vector": "...",
            "cvss_label": "High",
            "ref_url": "https://example.com",
            "aliases": [],
        }
    }
    result = _get_vuln_metadata("CVE-TEST", cache)
    assert result["published"] == "2024-01-01"
    assert result["cvss_score"] == 7.5


def test_get_vuln_metadata_handles_network_error():
    from generate_sbom import _get_vuln_metadata

    cache = {}
    with patch("generate_sbom.urllib.request.urlopen", side_effect=Exception("network")):
        result = _get_vuln_metadata("CVE-FAKE-999", cache)
    assert result["published"] == "—"
    assert result["cvss_score"] is None


# ── .NET ──────────────────────────────────────────────────────────────────────


def test_dotnet_packages_returns_empty_without_csproj(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert get_dotnet_packages() == []


def test_dotnet_packages_parses_json_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "MyApp.csproj").write_text("<Project/>")
    fake_json = json.dumps(
        {
            "projects": [
                {
                    "frameworks": [
                        {
                            "topLevelPackages": [
                                {"id": "Newtonsoft.Json", "resolvedVersion": "13.0.3"},
                                {"id": "Serilog", "resolvedVersion": "3.1.1"},
                            ],
                            "transitivePackages": [],
                        }
                    ]
                }
            ]
        }
    )
    with patch("generate_sbom._run_json", return_value=(json.loads(fake_json), True)):
        result = get_dotnet_packages()
    names = [p["name"] for p in result]
    assert "Newtonsoft.Json" in names
    assert "Serilog" in names


def test_dotnet_vulns_returns_empty_without_csproj(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert get_dotnet_vulns() == {}


def test_dotnet_vulns_parses_text_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "MyApp.csproj").write_text("<Project/>")
    fake_output = "   > Newtonsoft.Json   12.0.0   12.0.0   High   https://github.com/advisories/GHSA-5crp-9r3c-p9vx\n"
    with patch("generate_sbom._run", return_value=(fake_output, 0)):
        result = get_dotnet_vulns()
    assert "newtonsoft.json" in result
    assert result["newtonsoft.json"][0]["severity"] == "high"


# ── Maven ─────────────────────────────────────────────────────────────────────


def test_maven_packages_returns_empty_without_pom_xml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert get_maven_packages() == []


def test_maven_packages_parses_text_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pom.xml").write_text("<project/>")
    fake_output = (
        "[INFO] --- dependency:3.6.1:list ---\n"
        "[INFO]    com.google.guava:guava:jar:31.0.1-jre:compile\n"
        "[INFO]    junit:junit:jar:4.13.2:test\n"
    )
    with patch("generate_sbom._run", return_value=(fake_output, 0)):
        result = get_maven_packages()
    names = [p["name"] for p in result]
    assert "com.google.guava:guava" in names
    assert "junit:junit" in names


def test_maven_vulns_returns_empty_without_pom_xml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert get_maven_vulns() == {}


# ── Gradle ────────────────────────────────────────────────────────────────────


def test_gradle_packages_returns_empty_without_build_gradle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert get_gradle_packages() == []


def test_gradle_packages_parses_text_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build.gradle").write_text("// gradle")
    fake_output = "+--- com.google.guava:guava:31.0.1-jre\n\\--- org.springframework:spring-core:5.3.30\n"
    with patch("generate_sbom._run", return_value=(fake_output, 0)):
        result = get_gradle_packages()
    names = [p["name"] for p in result]
    assert "com.google.guava:guava" in names
    assert "org.springframework:spring-core" in names


def test_gradle_vulns_returns_empty_without_build_gradle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert get_gradle_vulns() == {}


# ── OWASP report parser ───────────────────────────────────────────────────────


def test_parse_owasp_report_handles_missing_file(tmp_path):
    result = _parse_owasp_report(tmp_path / "nonexistent.json")
    assert result == {}


# ── Policy ───────────────────────────────────────────────────────────────────


def test_load_policy_returns_defaults_without_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    policy = _load_policy()
    assert "allowed_licenses" in policy
    assert "MIT" in policy["allowed_licenses"]


def test_load_policy_merges_custom_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sbom-policy.json").write_text(
        json.dumps(
            {
                "rejected_packages": ["bad-pkg"],
            }
        )
    )
    policy = _load_policy()
    assert "bad-pkg" in policy["rejected_packages"]
    assert "MIT" in policy["allowed_licenses"]  # defaults preserved


def test_check_policy_detects_rejected_package():
    policy = {"rejected_packages": ["evil-pkg"], "allowed_licenses": ["MIT"], "require_fix_for_severity": ["critical"]}
    pkgs = [{"name": "evil-pkg", "ecosystem": "python"}]
    results = _check_policy(policy, pkgs, [{}], {"evil-pkg": "MIT"}, {})
    assert any("Fail" in r["status"] for r in results)


def test_check_policy_detects_license_violation():
    policy = {"rejected_packages": [], "allowed_licenses": ["MIT"], "require_fix_for_severity": []}
    pkgs = [{"name": "some-pkg", "ecosystem": "python"}]
    licenses = {"some-pkg": "GPL-3.0"}
    results = _check_policy(policy, pkgs, [{}], licenses, {})
    assert any("violation" in r["status"].lower() for r in results)


def test_check_policy_passes_clean():
    policy = {"rejected_packages": [], "allowed_licenses": ["MIT"], "require_fix_for_severity": []}
    pkgs = [{"name": "clean-pkg", "ecosystem": "python"}]
    licenses = {"clean-pkg": "MIT"}
    results = _check_policy(policy, pkgs, [{}], licenses, {})
    assert all("Pass" in r["status"] for r in results)



# ── License helpers ──────────────────────────────────────────────────────────


def test_get_python_licenses_returns_dict():
    licenses = get_python_licenses()
    assert isinstance(licenses, dict)
    # At minimum, pip itself should be in the venv
    assert any("pip" in k for k in licenses)


def test_get_npm_licenses_returns_dict(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    nm = tmp_path / "node_modules" / "fake-pkg"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text(json.dumps({"name": "fake-pkg", "license": "MIT"}))
    licenses = get_npm_licenses()
    assert licenses.get("fake-pkg") == "MIT"


# ── Outdated helpers ─────────────────────────────────────────────────────────


def test_get_python_outdated_returns_dict():
    with patch("generate_sbom._run_json", return_value=([{"name": "flask", "latest_version": "3.1.0"}], True)):
        result = get_python_outdated()
    assert result.get("flask") == "3.1.0"


def test_get_npm_outdated_returns_dict():
    with patch(
        "generate_sbom._run_json",
        return_value=({"jest": {"current": "29.0.0", "wanted": "29.7.0", "latest": "30.0.0"}}, True),
    ):
        result = get_npm_outdated()
    assert result.get("jest") == "30.0.0"


# ── OSV file-based cache ───────────────────────────────────────────────────


def test_load_osv_cache_missing_file(tmp_path):
    result = _load_osv_cache(cache_file=tmp_path / "nonexistent.json")
    assert result == {}


def test_load_osv_cache_fresh(tmp_path):
    from datetime import datetime, timezone
    cache_file = tmp_path / "cache.json"
    data = {
        "_meta": {"cached_at": datetime.now(timezone.utc).isoformat()},
        "CVE-TEST": {"cvss_score": 7.5, "published": "2024-01-01"},
    }
    cache_file.write_text(json.dumps(data))
    result = _load_osv_cache(cache_file=cache_file)
    assert result["CVE-TEST"]["cvss_score"] == 7.5
    assert "_meta" not in result


def test_load_osv_cache_stale(tmp_path):
    from datetime import datetime, timedelta, timezone
    cache_file = tmp_path / "cache.json"
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    data = {
        "_meta": {"cached_at": old_date},
        "CVE-TEST": {"cvss_score": 7.5},
    }
    cache_file.write_text(json.dumps(data))
    result = _load_osv_cache(cache_file=cache_file)
    assert result == {}


def test_load_osv_cache_corrupt_json(tmp_path):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("not valid json{{{")
    result = _load_osv_cache(cache_file=cache_file)
    assert result == {}


def test_save_osv_cache_roundtrip(tmp_path):
    cache_file = tmp_path / "cache.json"
    original = {"CVE-2025-001": {"cvss_score": 9.8, "published": "2025-01-15"}}
    _save_osv_cache(original, cache_file=cache_file)
    loaded = _load_osv_cache(cache_file=cache_file)
    assert loaded["CVE-2025-001"]["cvss_score"] == 9.8


def test_load_osv_cache_custom_max_age(tmp_path):
    from datetime import datetime, timedelta, timezone
    cache_file = tmp_path / "cache.json"
    three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    data = {
        "_meta": {"cached_at": three_days_ago},
        "CVE-TEST": {"cvss_score": 5.0},
    }
    cache_file.write_text(json.dumps(data))
    # Should be stale with max_age_days=2
    assert _load_osv_cache(cache_file=cache_file, max_age_days=2) == {}
    # Should be fresh with max_age_days=5
    assert _load_osv_cache(cache_file=cache_file, max_age_days=5) != {}
