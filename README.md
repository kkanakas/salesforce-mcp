# Salesforce MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that gives Claude direct access to your Salesforce org — query records, create and update data, explore your schema, and invoke flows.

---

## Quick Start

```bash
git clone https://github.com/you/salesforce-mcp
cd salesforce-mcp
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Salesforce credentials (see Authentication below)
python server.py
```

---

## Authentication

The server supports three authentication methods. It checks them in priority order: if `SALESFORCE_ACCESS_TOKEN` is set it is used first; if `SALESFORCE_USERNAME` and `SALESFORCE_PASSWORD` are set the password flow is used next; otherwise the OAuth browser flow runs.

---

### Method 1 — OAuth 2.0 Browser Flow (default)

The server opens your browser, you log in and approve access, and the server saves tokens to `~/.salesforce-mcp/tokens.json`. On subsequent runs it refreshes the token automatically — no browser needed.

**Step 1 — Create a Salesforce Connected App**

1. In Salesforce, go to **Setup → App Manager → New Connected App**
2. Fill in the App Name and Contact Email (any values)
3. Check **Enable OAuth Settings**
4. Set **Callback URL** to `http://localhost:8788/callback`
5. Under **Selected OAuth Scopes**, add:
   - `Access and manage your data (api)`
   - `Perform requests on your behalf at any time (refresh_token, offline_access)`
6. Click **Save**, then **Continue**
7. Wait 2–10 minutes for Salesforce to activate the app
8. Click **Manage Consumer Details** to reveal the **Consumer Key** and **Consumer Secret**

**Step 2 — Configure your .env**

```env
SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com
SALESFORCE_CLIENT_ID=your_consumer_key
SALESFORCE_CLIENT_SECRET=your_consumer_secret
SALESFORCE_REDIRECT_URI=http://localhost:8788/callback
```

**Step 3 — Run the server**

```bash
python server.py
```

The browser opens automatically on first run. After login, the server starts and Claude can connect.

---

### Method 2 — Username + Password Flow

No browser required. Credentials are exchanged directly for an access token via Salesforce's OAuth password grant. Useful for headless environments and CI.

**Prerequisites:**
- A Connected App (same setup as Method 1)
- **"Allow OAuth Username-Password Flows"** must be enabled: **Setup → OAuth and OpenID Connect Settings → Allow OAuth Username-Password Flows**

**Configure your .env:**

```env
SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com
SALESFORCE_CLIENT_ID=your_consumer_key
SALESFORCE_CLIENT_SECRET=your_consumer_secret
SALESFORCE_USERNAME=you@yourorg.com
SALESFORCE_PASSWORD=yourpassword
SALESFORCE_SECURITY_TOKEN=yoursecuritytoken
```

> **Where to find your security token:** In Salesforce, go to your profile → **Settings → My Personal Information → Reset My Security Token**. Check your email. If your org's trusted IP ranges include your server's IP, the security token can be left blank.

---

### Method 3 — Direct Access Token

The simplest option if you already have a valid Salesforce access token (e.g., from Postman, a session token, or a Connected App with a long-lived token). No Connected App setup required.

**Configure your .env:**

```env
SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com
SALESFORCE_ACCESS_TOKEN=your_access_token
```

> **Note:** Access tokens expire (typically after 2 hours). When the token expires, update `SALESFORCE_ACCESS_TOKEN` in your `.env` and restart the server.

---

## Running the Server

### Local — Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "python",
      "args": ["/absolute/path/to/salesforce-mcp/server.py"],
      "env": {
        "SALESFORCE_INSTANCE_URL": "https://yourorg.my.salesforce.com",
        "SALESFORCE_CLIENT_ID": "your_consumer_key",
        "SALESFORCE_CLIENT_SECRET": "your_consumer_secret"
      }
    }
  }
}
```

Restart Claude Desktop. Salesforce tools appear in the tool list automatically.

### Local — Claude Code

Add to your project's `.claude/mcp.json` or run:

```bash
claude mcp add salesforce python /absolute/path/to/salesforce-mcp/server.py
```

### MCP Gateway — HTTP/SSE Transport

Run the server in HTTP mode to expose it over the network:

```bash
python server.py --transport http --host 0.0.0.0 --port 8000
```

The server listens at `http://your-host:8000/sse`.

**MCP gateway config** (the exact format depends on your gateway product):

```json
{
  "url": "http://your-host:8000/sse"
}
```

**Docker:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t salesforce-mcp .
docker run -p 8000:8000 \
  -e SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com \
  -e SALESFORCE_ACCESS_TOKEN=your_token \
  salesforce-mcp
```

---

## Available Tools

| Tool | Description | Required Parameters |
|------|-------------|---------------------|
| `query_records` | Run a SOQL query against Salesforce | `soql: string` |
| `get_record` | Fetch a single record by ID | `object_name: string`, `record_id: string` |
| `create_record` | Create a new record | `object_name: string`, `fields: object` |
| `update_record` | Update fields on an existing record | `object_name: string`, `record_id: string`, `fields: object` |
| `delete_record` | Delete a record by ID | `object_name: string`, `record_id: string` |
| `list_objects` | List all queryable objects in the org | _(none)_ |
| `describe_object` | Get field names, types, and labels for an object | `object_name: string` |
| `invoke_flow` | Trigger an autolaunched Salesforce flow | `flow_api_name: string`, `inputs: object` |

**Example prompts:**

- *"Show me the 10 most recently modified Opportunities over $50,000"*
- *"Create a Contact named Jane Smith at Acme Corp"*
- *"What fields are on the Case object?"*
- *"Run the flow New_Customer_Onboarding with AccountId 001Hs00000XYZ"*

---

## Environment Variable Reference

| Variable | Required | Auth Method | Description |
|----------|----------|-------------|-------------|
| `SALESFORCE_INSTANCE_URL` | Yes | All | Your org URL, e.g. `https://yourorg.my.salesforce.com` |
| `SALESFORCE_CLIENT_ID` | OAuth/Password | OAuth browser, password flow | Connected App consumer key |
| `SALESFORCE_CLIENT_SECRET` | OAuth/Password | OAuth browser, password flow | Connected App consumer secret |
| `SALESFORCE_REDIRECT_URI` | No | OAuth browser | Default: `http://localhost:8788/callback` |
| `SALESFORCE_ACCESS_TOKEN` | No | Direct token | A valid Salesforce access token |
| `SALESFORCE_USERNAME` | No | Password flow | Your Salesforce username |
| `SALESFORCE_PASSWORD` | No | Password flow | Your Salesforce password |
| `SALESFORCE_SECURITY_TOKEN` | No | Password flow | Your Salesforce security token (can be blank if IP is trusted) |

---

## Development

**Run tests:**

```bash
pytest
```

**Run a specific test file:**

```bash
pytest tests/test_auth.py -v
```

**Project layout:**

```
salesforce-mcp/
├── server.py          # MCP server, tool routing, --transport flag
├── auth.py            # Auth flow selection and token management
├── client.py          # simple-salesforce singleton
├── config.py          # Environment variable loading
├── tools/
│   ├── records.py     # CRUD operations
│   ├── schema.py      # Object/field discovery
│   └── flows.py       # Flow invocation
├── tests/
├── .env.example
└── requirements.txt
```

Tokens from the OAuth browser flow are stored in `~/.salesforce-mcp/tokens.json` — outside the project directory so they are never accidentally committed.
