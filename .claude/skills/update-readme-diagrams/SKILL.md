---
name: update-readme-diagrams
description: Sync architecture diagrams to README.md
---
Update README.md with architecture diagrams from docs/architecture.md.

### Diagrams to sync (6 total)

All diagrams in README.md are Mermaid code blocks. Replace each with the latest version from `docs/architecture.md`:

1. **System Architecture** (graph TD) — in the "## Architecture" section
2. **Data Flow — Playback & Metadata** (graph TD) — in "### Data Flow — Playback & Metadata"
3. **Data Flow — Authentication & Profile** (sequenceDiagram) — in "### Data Flow — Authentication & Profile"
4. **Request Flow** (sequenceDiagram) — in "### Request Flow"
5. **CI/CD Pipeline** (graph LR) — in "### CI/CD" subsection
6. **Database Schema** (erDiagram) — in "### Database Schema"

### Steps

1. **Read** `docs/architecture.md` to get the latest Mermaid diagrams
2. **Read** `README.md` to find each diagram section by its heading
3. **Replace** each Mermaid code block with the corresponding one from `docs/architecture.md`
4. **Preserve** the 1-2 sentence description before each diagram
5. **Do NOT** add the Authentication Flow or Event-Driven Architecture diagrams to README (those stay in tech-spec only)

### Rules

- Replace Mermaid code blocks in place — do NOT duplicate or move them
- Keep the exact Mermaid syntax from `docs/architecture.md` (including style lines)
- Do NOT remove any non-diagram README content (screenshots, text, tables)
- Do NOT convert any remaining `text` code blocks (the project structure tree stays as text)

### Prerequisites

- `docs/architecture.md` must exist with all 8 diagrams (run `/generate-diagrams` first if missing)

### Report

- List which of the 6 diagrams were updated
- Note any that were already up to date (identical content)