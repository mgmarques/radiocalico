<!-- Radio Calico Skill v1.0.0 -->
Update README.md with architecture diagrams from docs/architecture.md.

### Steps

1. **Read** `docs/architecture.md` to get the latest Mermaid diagrams
2. **Read** `README.md` to find the current architecture/diagram sections
3. **Update** README.md by:
   - Adding or replacing the **System Architecture** diagram in the architecture section
   - Adding or replacing the **Request Flow** diagram near the deployment section
   - Adding or replacing the **CI/CD Pipeline** diagram in the Testing & CI section
   - Adding or replacing the **Database Schema** ER diagram near the database section

### Rules

- Only include the System Architecture, Request Flow, CI/CD Pipeline, and Database Schema diagrams in README.md (the Auth Flow stays only in the tech spec)
- Keep the Mermaid code blocks exactly as they are in `docs/architecture.md`
- Add a brief description (1-2 sentences) before each diagram
- If README.md already has a diagram section, replace it in place
- If README.md has no diagram section, add it after the relevant existing section
- Do NOT remove any existing README content — only add/replace diagram blocks
- After updating, verify the Mermaid syntax renders on GitHub (fenced code blocks with `mermaid` tag)

### Prerequisites

- `docs/architecture.md` must exist (run `/generate-diagrams` first if missing)
- If `docs/architecture.md` doesn't exist, tell the user to run `/generate-diagrams` first

### Report

- List which diagrams were added/updated in README.md
- Note any sections that were skipped (already up to date)