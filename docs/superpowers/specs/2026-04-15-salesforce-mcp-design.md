# Salesforce MCP Server — Design Spec

**Date:** 2026-04-15  
**Status:** Approved  

---

## Overview

A local MCP server written in Python that exposes Salesforce read, write, and workflow automation capabilities to Claude. Built with the official `mcp` Python SDK and `simple-salesforce`. Intended for personal productivity and learning MCP internals.

---

## Architecture

```
Claude (Claude Desktop / Claude Code)
        │  stdio (MCP protocol)
        ▼
  server.py  ← tool registry, request routing
        │
  ┌─────┼─────┐
  │     │     │
records schema flows
  │     │     │
        ▼
   client.py  ← simple-salesforce instance
        │
   auth.py    ← OAuth 2.0 token lifecycle
        │
        ▼
  Salesforce REST API
```

**Transport:** stdio — Claude Desktop and Claude Code communicate with the server via stdin/stdout.

**File layout:**
```
salesforce-mcp/
├── server.py          # MCP server init, tool registration
├── auth.py            # OAuth flow + token storage/refresh
├── client.py          # simple-salesforce wrapper, singleton client
├── tools/
│   ├── records.py     # CRUD operations
│   ├── schema.py      # object/field discovery
│   └── flows.py       # Salesforce flow invocation
├── config.py          # Connected App credentials, org URL
├── .env               # local secrets (gitignored)
└── tests/
    ├── test_records.py
    ├── test_schema.py
    ├── test_flows.py
    └── test_integration.py
```

---

## Tools

### Records (`tools/records.py`)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `query_records` | `soql: str` | Run arbitrary SOQL; returns list of records |
| `get_record` | `object_name: str, record_id: str` | Fetch a single record by ID |
| `create_record` | `object_name: str, fields: dict` | Create a new record |
| `update_record` | `object_name: str, record_id: str, fields: dict` | Update an existing record |
| `delete_record` | `object_name: str, record_id: str` | Delete a record |

`query_records` with raw SOQL is the power tool for complex queries. Claude uses `describe_object` before create/update to know which fields are available.

### Schema (`tools/schema.py`)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `list_objects` | none | List all queryable objects in the org (standard + custom) |
| `describe_object` | `object_name: str` | Return field names, types, and labels for an object |

### Flows (`tools/flows.py`)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `invoke_flow` | `flow_api_name: str, inputs: dict` | Trigger an autolaunched Salesforce flow with input variables |

---

## Authentication

### First-run OAuth 2.0 flow

1. Server detects no stored tokens at `~/.salesforce-mcp/tokens.json`
2. Prints a localhost callback URL and opens the browser
3. User logs into Salesforce and approves the Connected App
4. Salesforce redirects to `http://localhost:8788/callback` with an auth code
5. Server exchanges code for access + refresh tokens, saves to `~/.salesforce-mcp/tokens.json`
6. MCP server starts — Claude can connect

### Subsequent runs

Load tokens from disk → if access token expired, use refresh token to get a new one → start server. If refresh fails, return a "re-authentication required" error from any tool call.

### Configuration

Environment variables (read from `.env` via `python-dotenv`):

```
SALESFORCE_CLIENT_ID        # Connected App consumer key
SALESFORCE_CLIENT_SECRET    # Connected App consumer secret
SALESFORCE_REDIRECT_URI     # http://localhost:8788/callback
SALESFORCE_INSTANCE_URL     # e.g. https://yourorg.my.salesforce.com
```

Tokens are stored in `~/.salesforce-mcp/` (outside the project directory) so they survive directory changes and are never accidentally committed.

### Claude Desktop config

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "python",
      "args": ["/path/to/salesforce-mcp/server.py"]
    }
  }
}
```

---

## Error Handling

- **Salesforce API errors** (invalid SOQL, missing fields, permission denied): caught and returned as descriptive MCP error responses. Claude sees the message and can self-correct.
- **Expired tokens**: trigger a silent refresh. If refresh fails, tool returns a clear "re-authentication required" message.
- **Invalid object names or record IDs**: Salesforce error returned as-is — informative enough for Claude to act on.
- **No silent failures**: every error surfaces with enough context to understand what went wrong.

---

## Testing

| Test type | File | Approach |
|-----------|------|----------|
| Unit | `tests/test_*.py` | Mock `simple-salesforce` responses; test tool logic in isolation |
| Integration | `tests/test_integration.py` | Hit a real Salesforce sandbox org; full round-trip: auth → query → create → update → delete |
| Smoke | manual | Wire up Claude Desktop config, verify tools appear and work end-to-end |

---

## Dependencies

```
mcp                 # official MCP Python SDK
simple-salesforce   # Salesforce REST API wrapper
python-dotenv       # .env file loading
requests            # OAuth callback HTTP server
pytest              # test runner
pytest-mock         # mocking in unit tests
```
