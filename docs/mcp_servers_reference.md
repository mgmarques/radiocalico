# Radio Calico - MCP Servers Reference

## Table of Contents

1. [What Are MCP Servers?](#1-what-are-mcp-servers)
2. [Recommended Servers for Radio Calico](#2-recommended-servers-for-radio-calico)
3. [Setup Instructions](#3-setup-instructions)
4. [Configuration File](#4-configuration-file)
5. [Security Notes](#5-security-notes)
6. [Verifying Connections](#6-verifying-connections)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. What Are MCP Servers?

Model Context Protocol (MCP) servers extend Claude Code with external tool integrations. They allow Claude to interact directly with services like Docker, Sentry, GitHub, and more — without leaving the terminal.

MCP servers come in two types:

| Type | Description | Example |
|------|-------------|---------|
| **claude.ai (built-in)** | Managed by Anthropic, available in all projects. Authenticate via `/mcp` menu. | Atlassian, Lucid Chart, PubMed |
| **Project (custom)** | Defined in `.mcp.json` at the project root. Configured per-project. | Docker, Sentry, Brave Search |

---

## 2. Recommended Servers for Radio Calico

### Project-Level (`.mcp.json`)

| Server | Type | Purpose for Radio Calico | Requirements |
|--------|------|--------------------------|-------------|
| **Docker** | stdio | Manage containers, images, volumes. Useful with `make docker-dev`, `make docker-prod`. | Docker Desktop running |
| **Sentry** | http/OAuth | Error monitoring, issue triage, release tracking. | Sentry account + OAuth |
| **Brave Search** | stdio | Web search from Claude Code (docs lookup, troubleshooting). | Free API key from [brave.com/search/api](https://brave.com/search/api/) |
| **GitHub** | http | PR management, issue tracking, code search directly from Claude. | GitHub Copilot subscription |

### Built-in claude.ai (No Configuration Needed)

| Server | Useful for Radio Calico? | Notes |
|--------|--------------------------|-------|
| **Atlassian** | Yes | Jira issue tracking, Confluence documentation |
| **Lucid Chart** | Maybe | Architecture diagrams (project already uses Mermaid) |
| **Notion** | Maybe | If used for project notes/docs |
| **PagerDuty** | Maybe | If used for production alerting |

---

## 3. Setup Instructions

### Step 1: Create `.mcp.json` in the Project Root

Create a file named `.mcp.json` at the root of the Radio Calico repository:

```
radiocalico/
├── .mcp.json        <-- MCP server configuration
├── .gitignore       <-- Must include .mcp.json
├── api/
├── static/
└── ...
```

### Step 2: Add Your Server Configurations

Copy the template below and customize with your credentials:

```json
{
  "mcpServers": {
    "sentry": {
      "type": "http",
      "url": "https://mcp.sentry.dev/mcp"
    },
    "docker": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "mcp-docker-server"
      ]
    },
    "brave-search": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-ai/mcp-server-brave-search"
      ],
      "env": {
        "BRAVE_SEARCH_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

### Step 3: Restart Claude Code

MCP server changes only take effect after restarting Claude Code. Exit and reopen the CLI.

### Step 4: Authenticate OAuth Servers

For servers that use OAuth (like Sentry):

1. Run `/mcp` in Claude Code
2. Select the server that says "needs authentication"
3. Follow the OAuth prompt in your browser
4. Return to Claude Code — the server should show as "connected"

---

## 4. Configuration File

### Server Types

**stdio** — Runs a local process. Claude communicates via stdin/stdout.

```json
{
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "package-name"],
  "env": {
    "API_KEY": "<your-key>"
  }
}
```

**http** — Connects to a remote URL. Often uses OAuth for authentication.

```json
{
  "type": "http",
  "url": "https://service.example.com/mcp"
}
```

### Full Example with All Recommended Servers

```json
{
  "mcpServers": {
    "docker": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "mcp-docker-server"]
    },
    "sentry": {
      "type": "http",
      "url": "https://mcp.sentry.dev/mcp"
    },
    "brave-search": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-brave-search"],
      "env": {
        "BRAVE_SEARCH_API_KEY": "<your-api-key>"
      }
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}
```

> **Note**: GitHub MCP requires an active GitHub Copilot subscription. Without it, use the `gh` CLI instead (already available in the project).

---

## 5. Security Notes

- **`.mcp.json` is in `.gitignore`** — it will never be committed or pushed to the repository. This is critical because the file may contain API keys.
- **Never commit API keys** — If you add servers with API keys (like Brave Search), the keys stay local only.
- **OAuth servers are safe** — Servers like Sentry use browser-based OAuth, so no secrets are stored in the file.
- **Rotate keys if exposed** — If `.mcp.json` is accidentally committed, immediately revoke and regenerate all API keys in the file.
- **Each developer creates their own `.mcp.json`** — Since the file is gitignored, each team member sets up their own MCP servers locally.

---

## 6. Verifying Connections

After restarting Claude Code, run `/mcp` to check server status:

| Status | Meaning |
|--------|---------|
| `✔ connected` | Server is running and authenticated |
| `△ needs authentication` | OAuth required — select and follow the prompt |
| `✘ failed` | Configuration error — check package name, API key, or service availability |

You can also run Claude Code with debug logging for detailed error info:

```bash
claude --debug
```

---

## 7. Troubleshooting

| Problem | Solution |
|---------|----------|
| Docker MCP shows "failed" | Ensure Docker Desktop is running (`docker info`) |
| Brave Search shows "failed" | Verify your API key is correct and not the placeholder |
| Sentry shows "needs authentication" | Select it in `/mcp` and complete the OAuth flow in browser |
| GitHub shows "failed" | Requires GitHub Copilot subscription — remove if you don't have one |
| Server not appearing at all | Restart Claude Code after editing `.mcp.json` |
| `npx` errors (E404) | Check the package name is correct on [npmjs.com](https://www.npmjs.com/) |
| All project MCPs missing | Verify `.mcp.json` is in the project root (not in `.claude/` or `docs/`) |

---

*Generated for Radio Calico — Claude Code MCP integration guide.*