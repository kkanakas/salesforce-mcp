# Salesforce MCP — Token Auth & Gateway Design Spec

**Date:** 2026-04-21
**Status:** Approved

---

## Overview

Extends the existing Salesforce MCP server with two additional authentication methods (username/password flow and direct access token) and HTTP/SSE transport support for MCP gateway deployments. Also adds a comprehensive README covering setup, all auth methods, and both deployment modes.

---

## 1. Authentication

### Current state

Only OAuth 2.0 browser flow is supported. On first run, the server opens a browser, catches the callback on `localhost:8788`, exchanges the code for tokens, and stores them in `~/.salesforce-mcp/tokens.json`.

### New auth methods

Two additional methods are added, both configured entirely via environment variables.

**Selection priority (highest → lowest):**

1. `SALESFORCE_ACCESS_TOKEN` is set → **direct token mode**
2. `SALESFORCE_USERNAME` + `SALESFORCE_PASSWORD` + `SALESFORCE_SECURITY_TOKEN` are all set → **password flow**
3. Neither → **OAuth browser flow** (existing behavior, unchanged)

### Direct token mode

User supplies a pre-existing Salesforce access token directly. No browser, no HTTP server, no token refresh. The token is used as-is for the life of the process. If it expires, the tool returns an error asking the user to supply a fresh token.

New env var: `SALESFORCE_ACCESS_TOKEN`

### Username/password flow

Uses Salesforce's OAuth 2.0 Resource Owner Password Credentials grant. Posts credentials to `/services/oauth2/token` with `grant_type=password`. Returns an access token for the session. No refresh token is issued by this grant type; if the token expires, the server re-authenticates automatically on the next tool call.

New env vars:
- `SALESFORCE_USERNAME`
- `SALESFORCE_PASSWORD`
- `SALESFORCE_SECURITY_TOKEN` (appended to password per Salesforce's API requirement: `password + security_token`)

### Changes to existing files

**`auth.py`** — add two new functions:
- `get_token_from_env() -> dict` — returns `{"access_token": SALESFORCE_ACCESS_TOKEN}`
- `get_token_via_password() -> dict` — POSTs username/password/security_token to `/services/oauth2/token`

Update `get_valid_tokens()` to check env vars first and route accordingly.

**`config.py`** — add optional vars (no `_require`, validated only when their auth path is active):
- `SALESFORCE_ACCESS_TOKEN`
- `SALESFORCE_USERNAME`
- `SALESFORCE_PASSWORD`
- `SALESFORCE_SECURITY_TOKEN`

**`.env.example`** — add the new vars as commented-out alternatives.

---

## 2. Transport

### Current state

`server.py` uses `mcp.server.stdio.stdio_server` only. There is no way to run the server over HTTP/SSE.

### New `--transport` flag

`server.py` accepts a `--transport` CLI flag:

```
python server.py                          # stdio (default)
python server.py --transport stdio        # explicit stdio
python server.py --transport http         # HTTP/SSE
python server.py --transport http --host 0.0.0.0 --port 8000
```

Additional flags for HTTP mode:
- `--host` (default: `127.0.0.1`)
- `--port` (default: `8000`)

### HTTP/SSE transport

Uses `mcp.server.sse.SseServerTransport` from the MCP Python SDK. Exposes the server on `GET /sse` (event stream) and `POST /messages` (tool calls). This is the standard transport expected by MCP-compatible gateways.

`server.py` `main()` branches on the flag:
- `stdio` → existing `async with stdio_server()` path
- `http` → instantiate `SseServerTransport`, start an HTTP server (using `starlette` or the MCP SDK's built-in runner)

No changes to `tools/`, `client.py`, `auth.py`, or any tool definitions. Transport is entirely a server entry point concern.

### Dependency addition

`starlette` and `uvicorn` added to `requirements.txt` (required by MCP SDK's SSE transport).

---

## 3. README

Single `README.md` at the repo root. Tiered structure:

| Section | Audience | Content |
|---------|----------|---------|
| What this is | all | 2-sentence summary |
| Quick Start | technical | clone → install → .env → run in 5 steps |
| Authentication | all | 3 subsections, one per auth method |
| ↳ OAuth 2.0 (browser) | admin/new | Connected App creation walkthrough, scopes, callback URL |
| ↳ Username/Password | technical | env vars table, when to use |
| ↳ Direct Access Token | technical | env vars table, when to use |
| Running the Server | all | stdio (Claude Desktop + Claude Code config) and HTTP/SSE (Docker, gateway config) |
| Available Tools | all | table: tool name, description, required params |
| Environment Variable Reference | all | full table of all vars, required/optional, which auth method |
| Development | technical | running tests, project layout |

### Connected App setup (section 3a detail)

Step-by-step for OAuth browser flow:
1. Salesforce Setup → App Manager → New Connected App
2. Enable OAuth Settings
3. Callback URL: `http://localhost:8788/callback`
4. Required OAuth scopes: `api`, `refresh_token`
5. Copy Consumer Key → `SALESFORCE_CLIENT_ID`
6. Copy Consumer Secret → `SALESFORCE_CLIENT_SECRET`

For password flow, Connected App also needs: "Allow OAuth Username-Password Flows" enabled in Setup → OAuth and OpenID Connect Settings.

---

## 4. Updated Architecture

```
Claude Desktop / Claude Code / MCP Gateway
        │
        │  stdio  ──────────────────────────────────┐
        │                                            │
        │  HTTP/SSE (GET /sse, POST /messages)       │
        └──────────────────┐                         │
                           ▼                         ▼
                     server.py  ←── --transport http|stdio
                           │
               ┌───────────┼───────────┐
               │           │           │
           records       schema      flows
               └───────────┼───────────┘
                           ▼
                      client.py
                           │
                       auth.py  ←── priority: direct token → password → OAuth browser
                           │
                           ▼
                  Salesforce REST API
```

---

## 5. Environment Variable Reference

| Variable | Required | Auth method | Description |
|----------|----------|-------------|-------------|
| `SALESFORCE_INSTANCE_URL` | always | all | e.g. `https://yourorg.my.salesforce.com` |
| `SALESFORCE_CLIENT_ID` | OAuth/password | OAuth browser, password flow | Connected App consumer key |
| `SALESFORCE_CLIENT_SECRET` | OAuth/password | OAuth browser, password flow | Connected App consumer secret |
| `SALESFORCE_REDIRECT_URI` | OAuth browser | OAuth browser | Default: `http://localhost:8788/callback` |
| `SALESFORCE_ACCESS_TOKEN` | direct token | direct token mode | Pre-existing access token |
| `SALESFORCE_USERNAME` | password flow | password flow | Salesforce username |
| `SALESFORCE_PASSWORD` | password flow | password flow | Salesforce password |
| `SALESFORCE_SECURITY_TOKEN` | password flow | password flow | Salesforce security token |

---

## 6. Testing

| Test | Approach |
|------|----------|
| `test_auth.py` — new paths | Mock HTTP calls; test direct token returns as-is; test password flow POST; test priority routing |
| `test_config.py` | Test optional vars do not raise when absent |
| `test_server.py` | Test `--transport http` starts SSE server; test `--transport stdio` uses existing path |
| Existing tests | Unchanged |
