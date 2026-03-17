# Claude Code Project Template

> This template documents the Claude Code setup patterns used in Radio Calico.
> Copy the relevant pieces to bootstrap a new project.

## Directory Structure

```
your-project/
├── CLAUDE.md                      # Project overview (<200 lines)
├── VERSION                        # Semver version
├── CONTRIBUTING.md                # Onboarding guide
├── .claudeignore                  # Exclude noise from context
├── .claude/
│   ├── settings.json              # Permissions, hooks, denied ops
│   ├── TEMPLATE.md                # This file
│   ├── rules/                     # Topic-specific deep context
│   │   ├── architecture.md        # System internals
│   │   ├── testing.md             # Test strategy, CI/CD
│   │   ├── database.md            # Schema, migrations
│   │   └── style-guide.md         # Code conventions
│   ├── commands/                   # Slash commands (backward compat)
│   │   └── your-command.md
│   └── skills/                     # Skills (modern format)
│       ├── README.md               # Skill catalog
│       └── your-skill/
│           └── SKILL.md
└── tests/
    └── test_skills.py              # Validates all skills
```

## CLAUDE.md Template

Keep under 200 lines. Include:
- Project overview (1 paragraph)
- Architecture bullets (tech stack, key decisions)
- API endpoints (method, path, auth, body)
- Common tasks (bash commands)
- Important notes / gotchas
- Slash commands table

Reference `.claude/rules/` for details:
```markdown
> Detailed rules in `.claude/rules/`: architecture.md, testing.md, database.md, style-guide.md
```

## Settings Template

```json
{
  "permissions": {
    "allow": [
      "Bash(make *)",
      "Bash(git *)",
      "Bash(npm *)",
      "Bash(docker compose*)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git reset --hard*)",
      "Bash(git push --force*)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Lint your changes'"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Context compacted. Key reminders: ...'"
          }
        ]
      }
    ]
  }
}
```

## .claudeignore Template

```
node_modules/
venv/
__pycache__/
*.pyc
coverage/
.pytest_cache/
.DS_Store
*.log
package-lock.json
```

## Skill Template

```markdown
<!-- Project Skill v1.0.0 -->
Short description of what the skill does.

### Steps

1. **Read** relevant files to understand current state
2. **Do** the main action
3. **Verify** the result (run tests, check output)
4. **Report** what was done

### Rules

- Rule 1
- Rule 2

### Prerequisites

- What must exist before running this skill
```

## Skill Test Template

```python
"""Tests for slash commands/skills."""
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = ROOT / ".claude" / "commands"
SKILLS_DIR = ROOT / ".claude" / "skills"

EXPECTED_COMMANDS = [
    "your-command.md",
]

class TestCommandFilesExist:
    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_command_file_exists(self, filename):
        assert (COMMANDS_DIR / filename).exists()

class TestVersionHeaders:
    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_has_version_header(self, filename):
        content = (COMMANDS_DIR / filename).read_text()
        assert "<!-- " in content and " v" in content

class TestSkillDirectories:
    @pytest.mark.parametrize("filename", EXPECTED_COMMANDS)
    def test_skill_has_skill_md(self, filename):
        name = filename.replace(".md", "")
        assert (SKILLS_DIR / name / "SKILL.md").exists()
```

## Knowledge Transfer Checklist

When onboarding a new contributor or Claude Code session:

1. [ ] CLAUDE.md gives enough context to start working
2. [ ] `/start` launches the dev environment successfully
3. [ ] `/run-ci` passes all tests
4. [ ] CONTRIBUTING.md explains the workflow
5. [ ] Skill catalog (`.claude/skills/README.md`) lists all available commands
6. [ ] `.claude/rules/` covers domain-specific knowledge
7. [ ] `.claude/settings.json` auto-approves safe operations
8. [ ] `.claudeignore` keeps context focused