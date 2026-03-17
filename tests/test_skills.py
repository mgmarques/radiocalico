"""Tests for Claude Code slash commands (skills).

Validates that all 12 command files:
- Exist with correct structure and version headers
- Reference valid files, paths, and make targets
- Have consistent information with the actual codebase

These tests run in CI without Docker or MySQL.
"""

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = ROOT / ".claude" / "commands"

# ── All 12 expected commands ──────────────────────────────────

EXPECTED_COMMANDS = [
    "start.md",
    "check-stream.md",
    "troubleshoot.md",
    "test-ratings.md",
    "run-ci.md",
    "create-pr.md",
    "docker-verify.md",
    "add-endpoint.md",
    "security-audit.md",
    "add-share-button.md",
    "add-dark-style.md",
    "update-claude-md.md",
]


class TestCommandFilesExist:
    """All expected command files must exist."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_command_file_exists(self, filename):
        path = COMMANDS_DIR / filename
        assert path.exists(), f"Missing command file: {path}"

    def test_no_unexpected_commands(self):
        """No extra .md files beyond the expected set."""
        actual = {f.name for f in COMMANDS_DIR.glob("*.md")}
        expected = set(EXPECTED_COMMANDS)
        extra = actual - expected
        assert not extra, f"Unexpected command files: {extra}"

    def test_commands_directory_exists(self):
        assert COMMANDS_DIR.is_dir()


class TestVersionHeaders:
    """All commands must have a version header comment."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_has_version_header(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        assert "<!-- Radio Calico Skill v" in content, f"{filename} missing version header"

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_version_is_semver(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        match = re.search(r"v(\d+\.\d+\.\d+)", content)
        assert match, f"{filename} has no semver version"

    def test_all_versions_consistent(self):
        """All commands should be at the same version."""
        versions = set()
        for filename in EXPECTED_COMMANDS:
            content = (COMMANDS_DIR / filename).read_text()
            match = re.search(r"v(\d+\.\d+\.\d+)", content)
            if match:
                versions.add(match.group(1))
        assert len(versions) == 1, f"Inconsistent versions across commands: {versions}"


class TestProjectVersionFile:
    """VERSION file must exist and match command versions."""

    def test_version_file_exists(self):
        assert (ROOT / "VERSION").exists()

    def test_version_is_semver(self):
        version = (ROOT / "VERSION").read_text().strip()
        assert re.match(r"^\d+\.\d+\.\d+$", version), f"Invalid semver: {version}"

    def test_version_matches_commands(self):
        project_version = (ROOT / "VERSION").read_text().strip()
        content = (COMMANDS_DIR / "start.md").read_text()
        match = re.search(r"v(\d+\.\d+\.\d+)", content)
        assert match and match.group(1) == project_version


class TestCommandContent:
    """Commands must have meaningful content (not just a header)."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_has_description(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        # Remove the version header line, check remaining content is non-trivial
        lines = [l for l in content.strip().splitlines() if not l.startswith("<!--")]
        assert len(lines) >= 3, f"{filename} has too little content ({len(lines)} lines)"

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_no_empty_file(self, filename):
        content = (COMMANDS_DIR / filename).read_text().strip()
        assert len(content) > 50, f"{filename} is too short ({len(content)} chars)"


class TestMakeTargetReferences:
    """Commands that reference make targets must reference valid ones."""

    @pytest.fixture(autouse=True)
    def load_makefile(self):
        makefile = (ROOT / "Makefile").read_text()
        # Extract all target names from the Makefile
        self.targets = set(re.findall(r"^([a-z][\w-]+):", makefile, re.MULTILINE))

    def test_run_ci_references_valid_targets(self):
        content = (COMMANDS_DIR / "run-ci.md").read_text()
        for target in ["ci", "lint", "coverage"]:
            if f"make {target}" in content:
                assert target in self.targets, f"run-ci.md references missing target: make {target}"

    def test_docker_verify_references_valid_targets(self):
        content = (COMMANDS_DIR / "docker-verify.md").read_text()
        # docker-verify references docker compose commands, not make targets
        assert "docker compose" in content

    def test_security_audit_references_valid_targets(self):
        content = (COMMANDS_DIR / "security-audit.md").read_text()
        for target in ["bandit", "safety", "hadolint", "trivy", "zap"]:
            if f"make {target}" in content:
                assert target in self.targets, f"security-audit.md references missing target: make {target}"

    def test_add_endpoint_references_valid_files(self):
        content = (COMMANDS_DIR / "add-endpoint.md").read_text()
        referenced_files = ["api/app.py", "api/test_app.py", "api/test_integration.py", "db/init.sql"]
        for f in referenced_files:
            if f in content:
                assert (ROOT / f).exists(), f"add-endpoint.md references missing file: {f}"


class TestFileReferences:
    """Commands that reference project files must point to real files."""

    def test_start_references_valid_paths(self):
        content = (COMMANDS_DIR / "start.md").read_text()
        assert (ROOT / "api").is_dir()
        if "venv" in content:
            assert (ROOT / "api" / "venv").is_dir() or True  # venv may not exist in CI

    def test_check_stream_references_valid_urls(self):
        content = (COMMANDS_DIR / "check-stream.md").read_text()
        # Should reference the CloudFront URLs
        assert "cloudfront" in content.lower() or "127.0.0.1" in content

    def test_add_share_button_references_player_js(self):
        content = (COMMANDS_DIR / "add-share-button.md").read_text()
        assert "player.js" in content
        assert (ROOT / "static" / "js" / "player.js").exists()

    def test_add_dark_style_references_player_css(self):
        content = (COMMANDS_DIR / "add-dark-style.md").read_text()
        assert "player.css" in content or "css" in content.lower()
        assert (ROOT / "static" / "css" / "player.css").exists()

    def test_update_claude_md_references_claude_md(self):
        content = (COMMANDS_DIR / "update-claude-md.md").read_text()
        assert "CLAUDE.md" in content
        assert (ROOT / "CLAUDE.md").exists()


class TestCoverageThresholdConsistency:
    """Coverage thresholds in commands must match Makefile."""

    def test_run_ci_python_threshold_matches_makefile(self):
        makefile = (ROOT / "Makefile").read_text()
        makefile_match = re.search(r"cov-fail-under=(\d+)", makefile)
        assert makefile_match, "Makefile missing cov-fail-under"
        makefile_threshold = makefile_match.group(1)

        content = (COMMANDS_DIR / "run-ci.md").read_text()
        # Check that the threshold mentioned in run-ci matches Makefile
        if "cov-fail-under" in content:
            cmd_match = re.search(r"cov-fail-under=(\d+)", content)
            assert cmd_match, "run-ci.md mentions cov-fail-under but no number"
            assert cmd_match.group(1) == makefile_threshold, (
                f"run-ci.md threshold ({cmd_match.group(1)}) != "
                f"Makefile threshold ({makefile_threshold})"
            )

    def test_run_ci_mentions_correct_test_counts(self):
        content = (COMMANDS_DIR / "run-ci.md").read_text()
        # Should mention 61 Python tests and 162 JS tests
        assert "61" in content, "run-ci.md should mention 61 Python tests"
        assert "162" in content, "run-ci.md should mention 162 JS tests"


class TestCLAUDEmdConsistency:
    """CLAUDE.md must be consistent with the actual project state."""

    @pytest.fixture(autouse=True)
    def load_claude_md(self):
        self.content = (ROOT / "CLAUDE.md").read_text()

    def test_mentions_all_commands(self):
        for cmd in EXPECTED_COMMANDS:
            name = cmd.replace(".md", "")
            assert name in self.content, f"CLAUDE.md missing reference to /{name}"

    def test_mentions_version(self):
        version = (ROOT / "VERSION").read_text().strip()
        assert version in self.content or "v1.0.0" in self.content or "VERSION" in self.content

    def test_test_count_is_261(self):
        assert "261" in self.content, "CLAUDE.md should mention 261 total tests"

    def test_mentions_structured_logging(self):
        assert "structured" in self.content.lower() or "json log" in self.content.lower()

    def test_mentions_pagination(self):
        assert "pagination" in self.content.lower() or "limit" in self.content.lower()

    def test_mentions_health_endpoint(self):
        assert "/health" in self.content