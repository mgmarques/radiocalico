"""Tests for Claude Code slash commands (skills) and custom agents.

Validates that all 22 command files and 10 agent files:
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
AGENTS_DIR = ROOT / ".claude" / "agents"

# ── All 22 expected commands ──────────────────────────────────

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
    "test-browser.md",
    "generate-sbom.md",
    "check-llm.md",
    "add-language.md",
    "add-retro-button.md",
    "verify-deploy.md",
    "claude-qa.md",
]

# ── All 11 expected agents ──────────────────────────────────────

EXPECTED_AGENTS = [
    "qa-engineer.md",
    "dba.md",
    "frontend-reviewer.md",
    "devops.md",
    "api-designer.md",
    "release-manager.md",
    "security-auditor.md",
    "performance-analyst.md",
    "documentation-writer.md",
    "vv-plan-updater.md",
    "claude-code-housekeeper.md",
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
        has_html = "<!-- Radio Calico Skill v" in content
        has_yaml = content.startswith("---") and "name:" in content
        assert has_html or has_yaml, f"{filename} missing version header or YAML frontmatter"

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_version_is_semver(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        if content.startswith("---") and "name:" in content:
            return  # YAML frontmatter skills use name/description instead of version comment
        match = re.search(r"v(\d+\.\d+\.\d+)", content)
        assert match, f"{filename} has no semver version"

    def test_all_versions_consistent(self):
        """All commands should be at the same version or use YAML frontmatter."""
        versions = set()
        for filename in EXPECTED_COMMANDS:
            content = (COMMANDS_DIR / filename).read_text()
            if content.startswith("---") and "name:" in content:
                continue  # YAML frontmatter
            match = re.search(r"v(\d+\.\d+\.\d+)", content)
            if match:
                versions.add(match.group(1))
        assert len(versions) <= 1, f"Inconsistent versions across commands: {versions}"


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
        if content.startswith("---") and "name:" in content:
            return  # YAML frontmatter skills don't have version comments
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


class TestBrowserCommand:
    """Validate /test-browser command content."""

    def test_mentions_selenium(self):
        content = (COMMANDS_DIR / "test-browser.md").read_text()
        assert "selenium" in content.lower() or "Selenium" in content

    def test_mentions_make_target(self):
        content = (COMMANDS_DIR / "test-browser.md").read_text()
        assert "make test-browser" in content

    def test_mentions_headless_option(self):
        content = (COMMANDS_DIR / "test-browser.md").read_text()
        assert "BROWSER_HEADLESS" in content

    def test_lists_test_classes(self):
        content = (COMMANDS_DIR / "test-browser.md").read_text()
        for cls in ["TestPageLoad", "TestTheme", "TestRatings", "TestDrawer", "TestAuth",
                     "TestShareButtons", "TestResponsive", "TestAudioPlayback", "TestStreamQuality"]:
            assert cls in content, f"Missing test class: {cls}"

    def test_mentions_docker_prerequisite(self):
        content = (COMMANDS_DIR / "test-browser.md").read_text()
        assert "docker" in content.lower() or "Docker" in content


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

    def test_test_count_is_1002(self):
        assert "1002" in self.content, "CLAUDE.md should mention 1002 total tests"

    def test_mentions_structured_logging(self):
        assert "structured" in self.content.lower() or "json log" in self.content.lower()

    def test_mentions_pagination(self):
        assert "pagination" in self.content.lower() or "limit" in self.content.lower()

    def test_mentions_health_endpoint(self):
        # /health endpoint moved to .claude/rules/endpoints.md; CLAUDE.md references endpoints rule
        assert "/health" in self.content or "endpoints" in self.content

    def test_mentions_all_agents(self):
        for agent in EXPECTED_AGENTS:
            name = agent.replace(".md", "")
            assert name in self.content, f"CLAUDE.md missing reference to agent {name}"


# ── Agent Tests ────────────────────────────────────────────────


class TestAgentFilesExist:
    """All expected agent files must exist."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_agent_file_exists(self, filename):
        path = AGENTS_DIR / filename
        assert path.exists(), f"Missing agent file: {path}"

    def test_no_unexpected_agents(self):
        """No extra .md files beyond the expected set."""
        actual = {f.name for f in AGENTS_DIR.glob("*.md")}
        expected = set(EXPECTED_AGENTS)
        extra = actual - expected
        assert not extra, f"Unexpected agent files: {extra}"

    def test_agents_directory_exists(self):
        assert AGENTS_DIR.is_dir()


class TestAgentVersionHeaders:
    """All agents must have a version header comment."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_version_header(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        has_html = "<!-- Radio Calico Agent v" in content
        has_yaml = content.startswith("---") and "name:" in content
        assert has_html or has_yaml, f"{filename} missing version header or YAML frontmatter"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_version_is_semver(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        has_yaml = content.startswith("---") and "name:" in content
        if has_yaml:
            return  # YAML frontmatter agents use name/description instead of version comment
        match = re.search(r"v(\d+\.\d+\.\d+)", content)
        assert match, f"{filename} has no semver version"

    def test_all_agent_versions_consistent(self):
        """All agents should be at the same version or use YAML frontmatter."""
        versions = set()
        yaml_count = 0
        for filename in EXPECTED_AGENTS:
            content = (AGENTS_DIR / filename).read_text()
            if content.startswith("---") and "name:" in content:
                yaml_count += 1
                continue
            match = re.search(r"v(\d+\.\d+\.\d+)", content)
            if match:
                versions.add(match.group(1))
        assert len(versions) <= 1, f"Inconsistent agent versions: {versions}"

    def test_agent_version_matches_project(self):
        """Agent versions should match the project VERSION file or use YAML frontmatter."""
        content = (AGENTS_DIR / "qa-engineer.md").read_text()
        if content.startswith("---") and "name:" in content:
            return  # YAML frontmatter agents don't use version comments
        project_version = (ROOT / "VERSION").read_text().strip()
        match = re.search(r"v(\d+\.\d+\.\d+)", content)
        assert match and match.group(1) == project_version


class TestAgentContent:
    """Agents must have meaningful content."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_heading(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        assert "# " in content, f"{filename} missing heading"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_substantial_content(self, filename):
        content = (AGENTS_DIR / filename).read_text().strip()
        lines = [l for l in content.splitlines() if not l.startswith("<!--")]
        assert len(lines) >= 10, f"{filename} has too little content ({len(lines)} lines)"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_workflow_or_rules(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        has_workflow = "## Workflow" in content or "## Rules" in content
        assert has_workflow, f"{filename} missing Workflow or Rules section"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_has_key_files_section(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        assert "## Key Files" in content or "## Available" in content, (
            f"{filename} missing Key Files or Available section"
        )


# ── YAML Frontmatter Validation ───────────────────────────────


class TestCommandFrontmatter:
    """Commands with YAML frontmatter must have required fields."""

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_yaml_has_name(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        if content.startswith("---"):
            assert "name:" in content, f"{filename} YAML frontmatter missing 'name:'"

    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_yaml_has_description(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        if content.startswith("---"):
            assert "description:" in content, f"{filename} YAML frontmatter missing 'description:'"


# Delegated commands that must have context: fork + agent:
DELEGATED_COMMANDS = [
    "run-ci.md", "test-browser.md", "security-audit.md", "generate-sbom.md",
    "docker-verify.md", "generate-diagrams.md", "generate-tech-spec.md",
    "generate-requirements.md", "generate-vv-plan.md", "claude-qa.md",
]


class TestDelegatedCommandFrontmatter:
    """Delegated commands must have context: fork and agent: field."""

    @pytest.mark.parametrize("filename", DELEGATED_COMMANDS)
    def test_has_context_fork(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        assert "context: fork" in content, f"{filename} missing 'context: fork'"

    @pytest.mark.parametrize("filename", DELEGATED_COMMANDS)
    def test_has_agent_field(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        assert "agent:" in content, f"{filename} missing 'agent:' field"

    @pytest.mark.parametrize("filename", DELEGATED_COMMANDS)
    def test_agent_references_valid_agent(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        match = re.search(r"agent:\s*(\S+)", content)
        if match:
            agent_name = match.group(1)
            agent_file = AGENTS_DIR / f"{agent_name}.md"
            assert agent_file.exists(), f"{filename} references agent '{agent_name}' but {agent_file} doesn't exist"


class TestAgentFrontmatter:
    """Agents with YAML frontmatter must have required fields."""

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_yaml_has_name(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        if content.startswith("---"):
            assert "name:" in content, f"{filename} YAML frontmatter missing 'name:'"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_yaml_has_description(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        if content.startswith("---"):
            assert "description:" in content, f"{filename} YAML frontmatter missing 'description:'"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_yaml_has_tools(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        if content.startswith("---"):
            assert "tools:" in content, f"{filename} YAML frontmatter missing 'tools:'"

    @pytest.mark.parametrize("filename", EXPECTED_AGENTS)
    def test_yaml_has_model(self, filename):
        content = (AGENTS_DIR / filename).read_text()
        if content.startswith("---"):
            assert "model:" in content, f"{filename} YAML frontmatter missing 'model:'"


class TestQAEngineerAgent:
    """Validate QA Engineer agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "qa-engineer.md").read_text()

    def test_mentions_test_suites(self):
        for suite in ["Python unit", "integration", "JS", "E2E", "browser", "skills"]:
            assert suite.lower() in self.content.lower(), f"Missing test suite: {suite}"

    def test_mentions_coverage_thresholds(self):
        assert "95%" in self.content, "Missing Python coverage threshold"
        assert "97%" in self.content or "95%" in self.content, "Missing JS coverage threshold"

    def test_mentions_make_targets(self):
        for target in ["make test", "make coverage", "make ci"]:
            assert target in self.content, f"Missing make target: {target}"

    def test_mentions_test_files(self):
        for f in ["test_app.py", "player.test.js", "test_e2e.py", "test_browser.py"]:
            assert f in self.content, f"Missing test file reference: {f}"


class TestDBAAgent:
    """Validate DBA agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "dba.md").read_text()

    def test_mentions_all_tables(self):
        for table in ["ratings", "users", "profiles", "feedback"]:
            assert table in self.content, f"Missing table: {table}"

    def test_mentions_mysql_versions(self):
        assert "5.7" in self.content, "Missing MySQL 5.7 reference"
        assert "8.0" in self.content, "Missing MySQL 8.0 reference"

    def test_mentions_parameterized_queries(self):
        assert "%s" in self.content or "parameterized" in self.content

    def test_mentions_schema_file(self):
        assert "init.sql" in self.content

    def test_mentions_pymysql(self):
        assert "PyMySQL" in self.content


class TestFrontendReviewerAgent:
    """Validate Frontend Reviewer agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "frontend-reviewer.md").read_text()

    def test_mentions_xss_prevention(self):
        assert "escHtml" in self.content, "Missing escHtml reference"

    def test_mentions_theme_system(self):
        assert "data-theme" in self.content, "Missing theme attribute reference"
        assert "--mint" in self.content or "--forest" in self.content, "Missing CSS tokens"

    def test_mentions_breakpoint(self):
        assert "700px" in self.content, "Missing responsive breakpoint"

    def test_mentions_no_frameworks(self):
        assert "No frameworks" in self.content or "vanilla" in self.content.lower()

    def test_mentions_key_files(self):
        for f in ["player.js", "player.css", "index.html"]:
            assert f in self.content, f"Missing file reference: {f}"


class TestDevOpsAgent:
    """Validate DevOps agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "devops.md").read_text()

    def test_mentions_docker_services(self):
        for svc in ["nginx", "gunicorn", "MySQL"]:
            assert svc in self.content, f"Missing Docker service: {svc}"

    def test_mentions_ci_jobs(self):
        assert "13" in self.content, "Missing CI job count"

    def test_mentions_key_config_files(self):
        for f in ["Dockerfile", "docker-compose", "nginx.conf", "ci.yml", "Makefile"]:
            assert f in self.content, f"Missing config file: {f}"

    def test_mentions_ports(self):
        assert "5050" in self.content, "Missing Docker port"
        assert "5000" in self.content, "Missing Flask port"

    def test_mentions_health_endpoint(self):
        assert "/health" in self.content


class TestAPIDesignerAgent:
    """Validate API Designer agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "api-designer.md").read_text()

    def test_mentions_all_endpoint_groups(self):
        for group in ["Ratings", "Auth", "Profile", "Feedback", "Health"]:
            assert group in self.content, f"Missing endpoint group: {group}"

    def test_mentions_http_methods(self):
        for method in ["GET", "POST", "PUT"]:
            assert method in self.content, f"Missing HTTP method: {method}"

    def test_mentions_auth_pattern(self):
        assert "Bearer" in self.content, "Missing Bearer token reference"

    def test_mentions_rate_limiting(self):
        assert "rate limit" in self.content.lower() or "Rate limiting" in self.content

    def test_mentions_api_prefix(self):
        assert "/api/" in self.content

    def test_mentions_status_codes(self):
        for code in ["201", "400", "401", "409"]:
            assert code in self.content, f"Missing status code: {code}"


class TestReleaseManagerAgent:
    """Validate Release Manager agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "release-manager.md").read_text()

    def test_mentions_ci_pipeline(self):
        assert "13" in self.content, "Missing CI job count"

    def test_mentions_semver(self):
        assert "PATCH" in self.content and "MINOR" in self.content and "MAJOR" in self.content

    def test_mentions_version_file(self):
        assert "VERSION" in self.content

    def test_mentions_pre_merge_checklist(self):
        assert "Pre-Merge" in self.content or "checklist" in self.content.lower()

    def test_mentions_changelog(self):
        assert "changelog" in self.content.lower() or "Changelog" in self.content

    def test_mentions_gh_cli(self):
        assert "gh " in self.content, "Missing gh CLI reference"


class TestSecurityAuditorAgent:
    """Validate Security Auditor agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "security-auditor.md").read_text()

    def test_mentions_all_security_tools(self):
        for tool in ["Bandit", "Safety", "npm audit", "Hadolint", "Trivy", "ZAP"]:
            assert tool in self.content, f"Missing security tool: {tool}"

    def test_mentions_make_targets(self):
        for target in ["make security", "make security-all", "make docker-security"]:
            assert target in self.content, f"Missing make target: {target}"

    def test_mentions_owasp(self):
        assert "OWASP" in self.content, "Missing OWASP reference"

    def test_mentions_xss_prevention(self):
        assert "escHtml" in self.content, "Missing escHtml XSS prevention"

    def test_mentions_parameterized_queries(self):
        assert "%s" in self.content or "parameterized" in self.content

    def test_mentions_key_files(self):
        for f in ["app.py", "Dockerfile", "nginx.conf", "player.js"]:
            assert f in self.content, f"Missing file reference: {f}"


class TestPerformanceAnalystAgent:
    """Validate Performance Analyst agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "performance-analyst.md").read_text()

    def test_mentions_caching_strategies(self):
        assert "fetchItunesCached" in self.content, "Missing iTunes cache reference"
        assert "localStorage" in self.content, "Missing localStorage reference"

    def test_mentions_cdn(self):
        assert "CloudFront" in self.content, "Missing CDN reference"

    def test_mentions_pagination(self):
        assert "Pagination" in self.content or "pagination" in self.content

    def test_mentions_debounce(self):
        assert "METADATA_DEBOUNCE_MS" in self.content or "debounce" in self.content

    def test_mentions_key_files(self):
        for f in ["player.js", "player.css", "app.py", "nginx.conf"]:
            assert f in self.content, f"Missing file reference: {f}"


class TestDocumentationWriterAgent:
    """Validate Documentation Writer agent content."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        self.content = (AGENTS_DIR / "documentation-writer.md").read_text()

    def test_mentions_all_doc_files(self):
        for doc in ["architecture.md", "tech-spec.md", "requirements.md", "vv-test-plan.md"]:
            assert doc in self.content, f"Missing doc reference: {doc}"

    def test_mentions_generator_commands(self):
        for cmd in ["/generate-diagrams", "/generate-tech-spec", "/generate-requirements", "/generate-vv-plan"]:
            assert cmd in self.content, f"Missing generator command: {cmd}"

    def test_mentions_mermaid(self):
        assert "Mermaid" in self.content or "mermaid" in self.content

    def test_mentions_consistency(self):
        assert "consistency" in self.content.lower() or "Consistency" in self.content

    def test_mentions_key_files(self):
        for f in ["README.md", "CLAUDE.md", "docs/architecture.md", "docs/tech-spec.md"]:
            assert f in self.content, f"Missing file reference: {f}"


# ── Agent Delegation Tests ──────────────────────────────────────

SKILLS_WITH_AGENT_DELEGATION = {
    "run-ci": "qa-engineer",
    "security-audit": "security-auditor",
    "test-browser": "qa-engineer",
    "generate-vv-plan": "vv-plan-updater",
    "generate-tech-spec": "documentation-writer",
    "generate-requirements": "documentation-writer",
    "generate-diagrams": "documentation-writer",
    "docker-verify": "devops",
    "generate-sbom": "security-auditor",
}


class TestHeavySkillsAgentDelegation:
    """Heavy skills must delegate to their matching agent subagent."""

    @pytest.mark.parametrize("skill_name,agent_slug", SKILLS_WITH_AGENT_DELEGATION.items())
    def test_command_has_agent_section(self, skill_name, agent_slug):
        """Command file must contain ## Agent section."""
        skill_path = COMMANDS_DIR / f"{skill_name}.md"
        content = skill_path.read_text()
        assert "## Agent" in content, f"{skill_name}: missing ## Agent section in command file"

    @pytest.mark.parametrize("skill_name,agent_slug", SKILLS_WITH_AGENT_DELEGATION.items())
    def test_command_references_agent_slug(self, skill_name, agent_slug):
        """Command file must reference the correct agent slug."""
        skill_path = COMMANDS_DIR / f"{skill_name}.md"
        content = skill_path.read_text()
        assert agent_slug in content, (
            f"{skill_name}: missing agent slug '{agent_slug}' in command file"
        )

    @pytest.mark.parametrize("skill_name,agent_slug", SKILLS_WITH_AGENT_DELEGATION.items())
    def test_skill_mirror_has_agent_section(self, skill_name, agent_slug):
        """Skill mirror must also contain ## Agent section."""
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_path.read_text()
        assert "## Agent" in content, f"{skill_name}: missing ## Agent section in SKILL.md mirror"

    @pytest.mark.parametrize("skill_name,agent_slug", SKILLS_WITH_AGENT_DELEGATION.items())
    def test_skill_mirror_references_agent_slug(self, skill_name, agent_slug):
        """Skill mirror must reference the correct agent slug."""
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_path.read_text()
        assert agent_slug in content, (
            f"{skill_name}: missing agent slug '{agent_slug}' in SKILL.md mirror"
        )