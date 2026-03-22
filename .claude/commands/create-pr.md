---
name: create-pr
description: Branch, commit, push, and create a pull request
---
Create a pull request for the current changes.

### Steps

1. **Check state**: Run `git status` and `git diff --stat` to see all changes
2. **Create branch**: If on `main`, create a descriptive feature branch name from the changes
3. **Stage files**: Add only relevant files (never `.env`, `coverage/`, `__pycache__/`, `.DS_Store`)
4. **Commit**: Write a descriptive commit message with:
   - Summary line (imperative mood, under 72 chars)
   - Bullet points for each area changed
   - `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`
5. **Push**: `git push -u origin <branch>`
6. **Create PR**: Use `gh pr create` with this template:
   ```
   --title "<short title under 70 chars>"
   --body "## Summary
   <1-3 bullet points>

   ## Test plan
   <checklist of verification steps>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)"
   ```
7. **Report**: Show the PR URL to the user

### Rules

- Keep PR title under 70 characters
- PR body should explain WHY, not just WHAT
- Always include a test plan with checkboxes
- Never force-push or push to main directly
- If there are uncommitted changes unrelated to the current task, ask the user before including them