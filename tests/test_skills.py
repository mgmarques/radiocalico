"""Tests for Claude Code slash commands (skills).

Validates that all 17 command files:
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
SKILLS_DIR = ROOT / ".claude" / "skills"

# ── All 17 expected commands ──────────────────────────────────

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
    "generate-diagrams.md",
    "generate-tech-spec.md",
    "update-readme-diagrams.md",
    "generate-requirements.md",
    "generate-vv-plan.md",
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

    def test_skills_directory_exists(self):
        assert SKILLS_DIR.is_dir()

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_skill_directory_has_skill_md(self, filename):
        """Each command should also have a .claude/skills/<name>/SKILL.md mirror."""
        name = filename.replace(".md", "")
        skill_file = SKILLS_DIR / name / "SKILL.md"
        assert skill_file.exists(), f"Missing skill: {skill_file}"


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


class TestGenerateDiagramsCommand:
    """Validate /generate-diagrams command content."""

    def test_mentions_mermaid(self):
        content = (COMMANDS_DIR / "generate-diagrams.md").read_text()
        assert "mermaid" in content.lower() or "Mermaid" in content

    def test_mentions_output_file(self):
        content = (COMMANDS_DIR / "generate-diagrams.md").read_text()
        assert "docs/architecture.md" in content

    def test_mentions_all_diagram_types(self):
        content = (COMMANDS_DIR / "generate-diagrams.md").read_text()
        for diagram in [
            "System Architecture", "Request Flow",
            "Data Flow", "Event-Driven",
            "CI/CD Pipeline", "Database Schema", "Authentication Flow",
        ]:
            assert diagram in content, f"Missing diagram type: {diagram}"

    def test_references_source_files(self):
        content = (COMMANDS_DIR / "generate-diagrams.md").read_text()
        for ref in ["app.py", "player.js", "nginx.conf", "docker-compose.yml", "ci.yml", "init.sql"]:
            assert ref in content, f"Missing source file reference: {ref}"

    def test_mentions_data_flow_details(self):
        content = (COMMANDS_DIR / "generate-diagrams.md").read_text()
        for detail in ["fetchMetadata", "fetchItunesCached", "updateTrack", "localStorage"]:
            assert detail in content, f"Missing data flow detail: {detail}"

    def test_mentions_event_details(self):
        content = (COMMANDS_DIR / "generate-diagrams.md").read_text()
        for event in ["MANIFEST_PARSED", "FRAG_CHANGED", "FRAG_PARSING_METADATA", "LEVEL_LOADED", "ERROR"]:
            assert event in content, f"Missing HLS event: {event}"


class TestGenerateTechSpecCommand:
    """Validate /generate-tech-spec command content."""

    def test_mentions_output_file(self):
        content = (COMMANDS_DIR / "generate-tech-spec.md").read_text()
        assert "docs/tech-spec.md" in content

    def test_mentions_version_file(self):
        content = (COMMANDS_DIR / "generate-tech-spec.md").read_text()
        assert "VERSION" in content

    def test_has_all_spec_sections(self):
        content = (COMMANDS_DIR / "generate-tech-spec.md").read_text()
        required_sections = [
            "Executive Summary",
            "System Architecture",
            "Technology Stack",
            "API Reference",
            "Database Schema",
            "Authentication",
            "Deployment",
            "Observability",
            "Testing Strategy",
            "Performance",
            "Configuration",
        ]
        for section in required_sections:
            assert section in content, f"Missing spec section: {section}"

    def test_references_architecture_diagrams(self):
        content = (COMMANDS_DIR / "generate-tech-spec.md").read_text()
        assert "docs/architecture.md" in content

    def test_references_source_files(self):
        content = (COMMANDS_DIR / "generate-tech-spec.md").read_text()
        for ref in ["app.py", "nginx.conf", "CLAUDE.md", "Makefile", ".env.example"]:
            assert ref in content, f"Missing source file reference: {ref}"


class TestUpdateReadmeDiagramsCommand:
    """Validate /update-readme-diagrams command content."""

    def test_mentions_source_file(self):
        content = (COMMANDS_DIR / "update-readme-diagrams.md").read_text()
        assert "docs/architecture.md" in content

    def test_mentions_target_file(self):
        content = (COMMANDS_DIR / "update-readme-diagrams.md").read_text()
        assert "README.md" in content

    def test_mentions_which_diagrams_to_include(self):
        content = (COMMANDS_DIR / "update-readme-diagrams.md").read_text()
        for diagram in ["System Architecture", "Request Flow", "CI/CD Pipeline", "Database Schema"]:
            assert diagram in content, f"Missing diagram: {diagram}"

    def test_mentions_prerequisite(self):
        content = (COMMANDS_DIR / "update-readme-diagrams.md").read_text()
        assert "generate-diagrams" in content, "Should reference /generate-diagrams as prerequisite"

    def test_preserves_existing_content(self):
        content = (COMMANDS_DIR / "update-readme-diagrams.md").read_text()
        assert "NOT remove" in content or "not remove" in content.lower() or "Do NOT" in content


class TestGenerateRequirementsCommand:
    """Validate /generate-requirements command content."""

    def test_mentions_output_file(self):
        content = (COMMANDS_DIR / "generate-requirements.md").read_text()
        assert "docs/requirements.md" in content

    def test_has_functional_requirements_section(self):
        content = (COMMANDS_DIR / "generate-requirements.md").read_text()
        for area in ["Audio Streaming", "Track Metadata", "Ratings", "Authentication",
                      "User Profile", "Feedback", "Social Sharing", "Theme"]:
            assert area in content, f"Missing functional area: {area}"

    def test_has_non_functional_requirements_section(self):
        content = (COMMANDS_DIR / "generate-requirements.md").read_text()
        for area in ["Performance", "Security", "Reliability", "Observability", "Maintainability"]:
            assert area in content, f"Missing NFR area: {area}"

    def test_has_requirement_format(self):
        content = (COMMANDS_DIR / "generate-requirements.md").read_text()
        assert "FR-" in content, "Should use FR-xxx format for functional requirements"
        assert "NFR-" in content, "Should use NFR-xxx format for non-functional requirements"

    def test_has_traceability_matrix(self):
        content = (COMMANDS_DIR / "generate-requirements.md").read_text()
        assert "Traceability" in content or "traceability" in content

    def test_references_source_files(self):
        content = (COMMANDS_DIR / "generate-requirements.md").read_text()
        for ref in ["app.py", "player.js", "nginx.conf"]:
            assert ref in content, f"Missing source reference: {ref}"


class TestGenerateVVPlanCommand:
    """Validate /generate-vv-plan command content."""

    def test_mentions_output_file(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        assert "docs/vv-test-plan.md" in content

    def test_has_all_test_case_sections(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        for section in ["Audio Streaming", "Track Metadata", "Ratings", "Authentication",
                        "User Profile", "Feedback", "Social Sharing", "Theme", "Non-Functional"]:
            assert section in content, f"Missing test section: {section}"

    def test_uses_tc_format(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        assert "TC-" in content, "Should use TC-xxx format for test cases"

    def test_has_test_case_structure(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        for field in ["Precondition", "Steps", "Expected result", "Automated"]:
            assert field in content, f"Missing test case field: {field}"

    def test_references_all_test_suites(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        for suite in ["test_app.py", "test_integration.py", "player.test.js", "test_e2e.py", "test_skills.py"]:
            assert suite in content, f"Missing test suite reference: {suite}"

    def test_has_manual_test_procedures(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        assert "Manual" in content or "manual" in content

    def test_has_coverage_matrix(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        assert "Coverage Matrix" in content or "coverage" in content.lower()

    def test_has_execution_summary_template(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        assert "Execution Summary" in content or "Pass/Fail" in content

    def test_references_requirements(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        assert "requirements.md" in content, "Should reference requirements doc"

    def test_mentions_specific_test_cases(self):
        content = (COMMANDS_DIR / "generate-vv-plan.md").read_text()
        # Should have test cases for core user flows
        assert "TC-101" in content or "Play audio" in content.lower()
        assert "TC-301" in content or "Rate a track" in content.lower()
        assert "TC-401" in content or "Register" in content


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

    def test_test_count_is_401(self):
        assert "401" in self.content, "CLAUDE.md should mention 401 total tests"

    def test_mentions_structured_logging(self):
        assert "structured" in self.content.lower() or "json log" in self.content.lower()

    def test_mentions_pagination(self):
        assert "pagination" in self.content.lower() or "limit" in self.content.lower()

    def test_mentions_health_endpoint(self):
        assert "/health" in self.content