<!-- Radio Calico Skill v2.0.0 -->
Generate or update the technical specification document for Radio Calico.

## Agent
Delegate this entire skill to the **Documentation Writer** subagent (`documentation-writer`).
The Documentation Writer has specialized knowledge of cross-document consistency, Mermaid diagrams, and all docs generation workflows. It will run all steps in an isolated context window and return only a summary to the main conversation.

### Output file

Create/update `docs/tech-spec.md` with a comprehensive technical specification.

### Specification layout

1. **Title & Metadata** — use this exact header layout (logo right, version table left, vertically centered). Read version from `VERSION` file; set date to today:

   ```html
   <table><tr>
   <td valign="middle">

   # Radio Calico — Technical Specification

   | Field | Value |
   | --- | --- |
   | **Project** | Radio Calico |
   | **Version** | 1.0.0 |
   | **Date** | YYYY-MM-DD |
   | **Status** | Living document |

   </td>
   <td valign="middle" width="20%" align="right"><img src="../RadioCalicoLogoTM.png" alt="Radio Calico Logo" width="100%"></td>
   </tr></table>

   ---

   ## Table of Contents
   ...

   ---
   ```

2. **Executive Summary**
   - One paragraph describing what the system does and who it serves

3. **System Architecture**
   - Include the System Architecture diagram from `docs/architecture.md`
   - Describe each component's role and technology choice rationale

4. **Technology Stack**
   - Table: Layer | Technology | Version | Purpose
   - Cover: Frontend, Backend, Database, CDN, Streaming, Reverse Proxy, Containerization

5. **API Reference**
   - For each endpoint: method, path, auth required, request/response format, status codes
   - Read actual routes from `api/app.py`

6. **Database Schema**
   - Include the ER diagram from `docs/architecture.md`
   - Describe each table, columns, constraints, and relationships

7. **Authentication & Security**
   - Include the Auth Flow diagram from `docs/architecture.md`
   - Describe: PBKDF2 hashing, token management, rate limiting, security headers
   - List all nginx security headers from `nginx/nginx.conf`

8. **Deployment Architecture**
   - Include Request Flow diagram from `docs/architecture.md`
   - Docker: dev vs prod profiles, health checks, networking
   - nginx: static files, /api proxy, /health endpoint

9. **Observability**
   - Structured logging: Python (python-json-logger), nginx (JSON), JS (log utility)
   - X-Request-ID correlation across layers
   - Log format examples

10. **Testing Strategy**
    - Include CI/CD Pipeline diagram from `docs/architecture.md`
    - Table of all test suites: unit, integration, E2E, skills
    - Coverage thresholds and enforcement
    - Security scanning tools (6 tools)
    - Linting tools (4 linters)

11. **Performance Optimizations**
    - WebP images, dns-prefetch, iTunes API cache, gzip, asset caching
    - API pagination on ratings endpoint

12. **Configuration**
    - Environment variables (from `.env.example`)
    - Docker Compose profiles (dev vs prod)
    - Makefile targets summary

13. **Known Limitations & Future Work**
    - Read from CLAUDE.md "Known Gotchas" section
    - Identify gaps and potential improvements

### Steps

1. **Read** all key files to gather current state:
   - `VERSION`, `CLAUDE.md`, `README.md`, `api/app.py`, `nginx/nginx.conf`
   - `docker-compose.yml`, `Dockerfile`, `.github/workflows/ci.yml`
   - `db/init.sql`, `api/.env.example`, `Makefile`
   - `docs/architecture.md` (for diagrams)

2. **Generate** the full tech spec following the layout above

3. **Cross-reference** diagrams from `docs/architecture.md` (include them inline)

4. **Report** the generated document path and section count