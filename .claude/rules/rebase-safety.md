# Rebase Safety

## Before Rebasing

1. Note the current commit hash: `git rev-parse HEAD` — this is your **restore point**
2. Identify key files that have been heavily modified in the branch (CSS, JS, HTML, Python)

## After Rebasing

1. **Always diff key files** against the pre-rebase commit:
   ```bash
   git diff <pre-rebase-hash> -- static/ api/ docker-compose.yml nginx/
   ```
2. If lines decreased significantly or fixes disappeared, restore from the pre-rebase commit:
   ```bash
   git checkout <pre-rebase-hash> -- <file>
   ```
3. Re-apply only the post-rebase fixes (stylelint renames, ruff format, etc.) on top

## Common Rebase Pitfalls

| Pitfall | Prevention |
|---|---|
| Conflict resolution takes the wrong side | Always keep the branch version for CSS/JS/HTML changes, take main for CLAUDE.md/README counts |
| Fixes in later commits lost when squashing | Check `git reflog` — the pre-rebase commit is always recoverable |
| Docker container still has old files after rebase | Rebuild with `--no-cache`: `docker compose --profile prod build --no-cache app` |

## Recovery

If fixes are lost and already pushed:
```bash
# Find pre-rebase commit
git reflog | grep "rebase (start)"
# The line ABOVE that is your pre-rebase commit
git diff <pre-rebase-hash> -- static/ api/ | diffstat
# Restore specific files
git checkout <pre-rebase-hash> -- static/css/player.css static/js/player.js
```