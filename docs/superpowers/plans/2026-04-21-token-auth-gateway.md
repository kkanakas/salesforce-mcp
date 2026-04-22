# Token Auth & MCP Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add username/password and direct-token auth methods to the Salesforce MCP server, add HTTP/SSE transport for MCP gateway deployments, and write a comprehensive README.

**Architecture:** `auth.py` gains two new auth paths selected by priority from env vars; `server.py` gains a `--transport` flag that switches between the existing stdio path and a new HTTP/SSE path powered by Starlette + uvicorn. All other files (`tools/`, `client.py`) are unchanged.

**Tech Stack:** Python 3.11+, MCP Python SDK (`mcp`), `simple-salesforce`, `starlette`, `uvicorn`, `requests`, `pytest`

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `config.py` | Modify | `CLIENT_ID`/`CLIENT_SECRET` become optional; 4 new optional vars added |
| `auth.py` | Modify | 2 new auth functions; `get_valid_tokens()` gains priority routing |
| `server.py` | Modify | `--transport`/`--host`/`--port` args; `run_http_server()` function |
| `requirements.txt` | Modify | Add `starlette`, `uvicorn` |
| `.env.example` | Modify | Document new env vars |
| `tests/conftest.py` | Modify | Clean up new optional env vars between tests |
| `tests/test_config.py` | Modify | Update 2 tests that assumed CLIENT_ID/SECRET are required |
| `tests/test_auth.py` | Modify | Add tests for 2 new auth paths and priority routing |
| `tests/test_server.py` | Modify | Add tests for `--transport` flag and `run_http_server` |
| `README.md` | Create | Full setup and usage documentation |

---

## Task 1: Update config.py — make CLIENT_ID/SECRET optional, add new vars

`CLIENT_ID` and `CLIENT_SECRET` are currently `_require()` at import time. Direct token mode doesn't need them, so they become optional. Four new optional vars are added.

**Files:**
- Modify: `config.py`
- Modify: `tests/test_config.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1.1: Write the failing tests for optional vars**

Add to `tests/test_config.py` (after the existing tests):

```python
def test_config_client_id_optional_when_absent():
    cfg = _reload_config(
        overrides={
            "SALESFORCE_CLIENT_SECRET": "csecret",
            "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
        },
        remove=["SALESFORCE_CLIENT_ID"],
    )
    assert cfg.CLIENT_ID == ""


def test_config_client_secret_optional_when_absent():
    cfg = _reload_config(
        overrides={
            "SALESFORCE_CLIENT_ID": "cid",
            "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
        },
        remove=["SALESFORCE_CLIENT_SECRET"],
    )
    assert cfg.CLIENT_SECRET == ""


def test_config_access_token_optional():
    cfg = _reload_config(
        overrides={
            "SALESFORCE_CLIENT_ID": "cid",
            "SALESFORCE_CLIENT_SECRET": "csecret",
            "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
            "SALESFORCE_ACCESS_TOKEN": "mytoken",
        },
    )
    assert cfg.ACCESS_TOKEN == "mytoken"


def test_config_access_token_empty_when_absent():
    cfg = _reload_config(
        overrides={
            "SALESFORCE_CLIENT_ID": "cid",
            "SALESFORCE_CLIENT_SECRET": "csecret",
            "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
        },
        remove=["SALESFORCE_ACCESS_TOKEN"],
    )
    assert cfg.ACCESS_TOKEN == ""


def test_config_username_password_security_token_optional():
    cfg = _reload_config(
        overrides={
            "SALESFORCE_CLIENT_ID": "cid",
            "SALESFORCE_CLIENT_SECRET": "csecret",
            "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
            "SALESFORCE_USERNAME": "user@example.com",
            "SALESFORCE_PASSWORD": "pass",
            "SALESFORCE_SECURITY_TOKEN": "tok",
        },
    )
    assert cfg.USERNAME == "user@example.com"
    assert cfg.PASSWORD == "pass"
    assert cfg.SECURITY_TOKEN == "tok"


def test_config_username_password_security_token_empty_when_absent():
    cfg = _reload_config(
        overrides={
            "SALESFORCE_CLIENT_ID": "cid",
            "SALESFORCE_CLIENT_SECRET": "csecret",
            "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
        },
        remove=["SALESFORCE_USERNAME", "SALESFORCE_PASSWORD", "SALESFORCE_SECURITY_TOKEN"],
    )
    assert cfg.USERNAME == ""
    assert cfg.PASSWORD == ""
    assert cfg.SECURITY_TOKEN == ""
```

- [ ] **Step 1.2: Update the two existing tests that expect CLIENT_ID/SECRET to be required**

In `tests/test_config.py`, replace `test_config_raises_on_missing_client_id` with:

```python
def test_config_raises_on_missing_instance_url():
    with pytest.raises(KeyError, match="SALESFORCE_INSTANCE_URL"):
        _reload_config(
            overrides={
                "SALESFORCE_CLIENT_ID": "cid",
                "SALESFORCE_CLIENT_SECRET": "csecret",
            },
            remove=["SALESFORCE_INSTANCE_URL"],
        )
```

And delete `test_config_raises_on_missing_client_id` (CLIENT_ID is no longer required). The `test_config_raises_on_missing_instance_url` test already exists — keep it, just remove the CLIENT_ID one.

- [ ] **Step 1.3: Run the new tests to confirm they fail**

```bash
pytest tests/test_config.py -v
```

Expected: failures on the new `test_config_client_id_optional_*` and `test_config_access_token_*` tests (config doesn't have these vars yet).

- [ ] **Step 1.4: Update config.py**

Replace the full contents of `config.py` with:

```python
import os

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value or not value.strip():
        raise KeyError(f"Missing required environment variable: {key}")
    return value.strip()


INSTANCE_URL = _require("SALESFORCE_INSTANCE_URL")
REDIRECT_URI = os.environ.get("SALESFORCE_REDIRECT_URI", "http://localhost:8788/callback")

CLIENT_ID = os.environ.get("SALESFORCE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("SALESFORCE_CLIENT_SECRET", "").strip()

ACCESS_TOKEN = os.environ.get("SALESFORCE_ACCESS_TOKEN", "").strip()

USERNAME = os.environ.get("SALESFORCE_USERNAME", "").strip()
PASSWORD = os.environ.get("SALESFORCE_PASSWORD", "").strip()
SECURITY_TOKEN = os.environ.get("SALESFORCE_SECURITY_TOKEN", "").strip()
```

- [ ] **Step 1.5: Update conftest.py to clean optional vars between tests**

Replace the contents of `tests/conftest.py` with:

```python
import os
import pytest

os.environ.setdefault("SALESFORCE_CLIENT_ID", "test_client_id")
os.environ.setdefault("SALESFORCE_CLIENT_SECRET", "test_secret")
os.environ.setdefault("SALESFORCE_INSTANCE_URL", "https://test.salesforce.com")
os.environ.setdefault("SALESFORCE_REDIRECT_URI", "http://localhost:8788/callback")

_REQUIRED_ENV = {
    "SALESFORCE_CLIENT_ID": "test_client_id",
    "SALESFORCE_CLIENT_SECRET": "test_secret",
    "SALESFORCE_INSTANCE_URL": "https://test.salesforce.com",
    "SALESFORCE_REDIRECT_URI": "http://localhost:8788/callback",
}

_OPTIONAL_ENV = [
    "SALESFORCE_ACCESS_TOKEN",
    "SALESFORCE_USERNAME",
    "SALESFORCE_PASSWORD",
    "SALESFORCE_SECURITY_TOKEN",
]


@pytest.fixture(autouse=True)
def restore_env():
    """Restore required env vars and clear optional vars before each test."""
    for key, val in _REQUIRED_ENV.items():
        os.environ[key] = val
    for key in _OPTIONAL_ENV:
        os.environ.pop(key, None)
    yield
    for key, val in _REQUIRED_ENV.items():
        os.environ[key] = val
    for key in _OPTIONAL_ENV:
        os.environ.pop(key, None)
```

- [ ] **Step 1.6: Run the config tests**

```bash
pytest tests/test_config.py -v
```

Expected: all tests pass.

- [ ] **Step 1.7: Run the full test suite to check nothing broke**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 1.8: Commit**

```bash
git add config.py tests/test_config.py tests/conftest.py
git commit -m "feat: make CLIENT_ID/SECRET optional in config; add auth env vars"
```

---

## Task 2: Add direct-token auth path to auth.py

When `SALESFORCE_ACCESS_TOKEN` is set, skip all token exchange and return it directly.

**Files:**
- Modify: `auth.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 2.1: Write the failing tests**

Add to `tests/test_auth.py`:

```python
def test_get_token_from_env_returns_access_token(monkeypatch):
    import sys
    sys.modules.pop("config", None)
    monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "direct_token_abc")
    import importlib
    import config as cfg
    importlib.reload(cfg)
    import auth
    importlib.reload(auth)

    result = auth.get_token_from_env()
    assert result == {"access_token": "direct_token_abc"}


def test_get_valid_tokens_uses_direct_token_when_access_token_set(mocker, monkeypatch):
    import sys
    sys.modules.pop("config", None)
    monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "mytoken")
    import importlib
    import config as cfg
    importlib.reload(cfg)
    import auth
    importlib.reload(auth)

    mock_oauth = mocker.patch("auth.run_oauth_flow")
    mock_password = mocker.patch("auth.get_token_via_password") if hasattr(auth, "get_token_via_password") else None

    result = auth.get_valid_tokens()

    assert result == {"access_token": "mytoken"}
    mock_oauth.assert_not_called()
```

- [ ] **Step 2.2: Run the new tests to confirm they fail**

```bash
pytest tests/test_auth.py::test_get_token_from_env_returns_access_token tests/test_auth.py::test_get_valid_tokens_uses_direct_token_when_access_token_set -v
```

Expected: `AttributeError: module 'auth' has no attribute 'get_token_from_env'`

- [ ] **Step 2.3: Add get_token_from_env() and update get_valid_tokens() in auth.py**

Replace the `get_valid_tokens` function and add the new function. The top of `auth.py` remains unchanged (imports, TOKEN_PATH, load_tokens, save_tokens, _exchange_code, refresh_access_token, run_oauth_flow stay as-is). Replace only `get_valid_tokens`:

```python
def get_token_from_env() -> dict:
    return {"access_token": config.ACCESS_TOKEN}


def get_token_via_password() -> dict:
    # Placeholder — implemented in Task 3
    raise NotImplementedError


def get_valid_tokens() -> dict:
    if config.ACCESS_TOKEN:
        return get_token_from_env()

    if config.USERNAME and config.PASSWORD:
        return get_token_via_password()

    tokens = load_tokens()

    if tokens is None:
        tokens = run_oauth_flow()
        save_tokens(tokens)
        return tokens

    try:
        new_tokens = refresh_access_token(tokens["refresh_token"])
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = tokens["refresh_token"]
        save_tokens(new_tokens)
        return new_tokens
    except requests.RequestException:
        tokens = run_oauth_flow()
        save_tokens(tokens)
        return tokens
```

- [ ] **Step 2.4: Run the direct-token tests**

```bash
pytest tests/test_auth.py::test_get_token_from_env_returns_access_token tests/test_auth.py::test_get_valid_tokens_uses_direct_token_when_access_token_set -v
```

Expected: both pass.

- [ ] **Step 2.5: Run the full test suite**

```bash
pytest -v
```

Expected: all pass (the existing `get_valid_tokens` tests still pass because conftest clears `ACCESS_TOKEN` and `USERNAME` before each test, so they fall through to the OAuth path).

- [ ] **Step 2.6: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add direct access token auth path"
```

---

## Task 3: Add username/password auth path to auth.py

When `SALESFORCE_USERNAME` and `SALESFORCE_PASSWORD` are set, use Salesforce's OAuth password grant to exchange credentials for an access token.

**Files:**
- Modify: `auth.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 3.1: Write the failing tests**

Add to `tests/test_auth.py`:

```python
def test_get_token_via_password_posts_credentials(mocker, monkeypatch):
    import sys
    sys.modules.pop("config", None)
    monkeypatch.setenv("SALESFORCE_USERNAME", "user@example.com")
    monkeypatch.setenv("SALESFORCE_PASSWORD", "pass123")
    monkeypatch.setenv("SALESFORCE_SECURITY_TOKEN", "tokABC")
    import importlib
    import config as cfg
    importlib.reload(cfg)
    import auth
    importlib.reload(auth)

    mock_post = mocker.patch("auth.requests.post")
    mock_post.return_value.json.return_value = {"access_token": "pw_token"}
    mock_post.return_value.raise_for_status = lambda: None

    result = auth.get_token_via_password()

    mock_post.assert_called_once_with(
        "https://test.salesforce.com/services/oauth2/token",
        data={
            "grant_type": "password",
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "username": "user@example.com",
            "password": "pass123tokABC",
        },
    )
    assert result == {"access_token": "pw_token"}


def test_get_token_via_password_appends_empty_security_token(mocker, monkeypatch):
    import sys
    sys.modules.pop("config", None)
    monkeypatch.setenv("SALESFORCE_USERNAME", "user@example.com")
    monkeypatch.setenv("SALESFORCE_PASSWORD", "pass123")
    import importlib
    import config as cfg
    importlib.reload(cfg)
    import auth
    importlib.reload(auth)

    mock_post = mocker.patch("auth.requests.post")
    mock_post.return_value.json.return_value = {"access_token": "pw_token"}
    mock_post.return_value.raise_for_status = lambda: None

    auth.get_token_via_password()

    call_data = mock_post.call_args[1]["data"]
    assert call_data["password"] == "pass123"


def test_get_token_via_password_raises_on_http_error(mocker, monkeypatch):
    import sys
    sys.modules.pop("config", None)
    monkeypatch.setenv("SALESFORCE_USERNAME", "user@example.com")
    monkeypatch.setenv("SALESFORCE_PASSWORD", "pass123")
    import importlib
    import config as cfg
    importlib.reload(cfg)
    import auth
    importlib.reload(auth)

    import requests as req
    mock_post = mocker.patch("auth.requests.post")
    mock_post.return_value.raise_for_status.side_effect = req.HTTPError("401")

    with pytest.raises(req.HTTPError):
        auth.get_token_via_password()


def test_get_valid_tokens_uses_password_flow_when_credentials_set(mocker, monkeypatch):
    import sys
    sys.modules.pop("config", None)
    monkeypatch.setenv("SALESFORCE_USERNAME", "user@example.com")
    monkeypatch.setenv("SALESFORCE_PASSWORD", "pass123")
    import importlib
    import config as cfg
    importlib.reload(cfg)
    import auth
    importlib.reload(auth)

    mock_pw = mocker.patch("auth.get_token_via_password", return_value={"access_token": "pw_tok"})
    mock_oauth = mocker.patch("auth.run_oauth_flow")

    result = auth.get_valid_tokens()

    mock_pw.assert_called_once()
    mock_oauth.assert_not_called()
    assert result == {"access_token": "pw_tok"}


def test_get_valid_tokens_direct_token_takes_priority_over_password(mocker, monkeypatch):
    import sys
    sys.modules.pop("config", None)
    monkeypatch.setenv("SALESFORCE_ACCESS_TOKEN", "direct_tok")
    monkeypatch.setenv("SALESFORCE_USERNAME", "user@example.com")
    monkeypatch.setenv("SALESFORCE_PASSWORD", "pass123")
    import importlib
    import config as cfg
    importlib.reload(cfg)
    import auth
    importlib.reload(auth)

    mock_pw = mocker.patch("auth.get_token_via_password")
    mock_oauth = mocker.patch("auth.run_oauth_flow")

    result = auth.get_valid_tokens()

    mock_pw.assert_not_called()
    mock_oauth.assert_not_called()
    assert result == {"access_token": "direct_tok"}
```

- [ ] **Step 3.2: Run the new tests to confirm they fail**

```bash
pytest tests/test_auth.py::test_get_token_via_password_posts_credentials tests/test_auth.py::test_get_valid_tokens_uses_password_flow_when_credentials_set -v
```

Expected: `NotImplementedError` (placeholder from Task 2).

- [ ] **Step 3.3: Implement get_token_via_password() in auth.py**

Replace the `get_token_via_password` placeholder with:

```python
def get_token_via_password() -> dict:
    response = requests.post(
        f"{config.INSTANCE_URL}/services/oauth2/token",
        data={
            "grant_type": "password",
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET,
            "username": config.USERNAME,
            "password": config.PASSWORD + config.SECURITY_TOKEN,
        },
    )
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 3.4: Run all auth tests**

```bash
pytest tests/test_auth.py -v
```

Expected: all pass.

- [ ] **Step 3.5: Run the full test suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 3.6: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add username/password auth flow"
```

---

## Task 4: Add --transport flag and HTTP/SSE support to server.py

`server.py` gains a `_parse_args()` helper and a `run_http_server()` function. The `__main__` block branches on `--transport`.

**Files:**
- Modify: `server.py`
- Modify: `requirements.txt`
- Modify: `tests/test_server.py`

- [ ] **Step 4.1: Add starlette and uvicorn to requirements.txt**

Add two lines to `requirements.txt`:

```
starlette>=0.27.0
uvicorn>=0.24.0
```

- [ ] **Step 4.2: Install the new deps**

```bash
pip install starlette uvicorn
```

Expected: installs without errors.

- [ ] **Step 4.3: Write the failing tests**

Add to `tests/test_server.py`:

```python
def test_parse_args_defaults_to_stdio():
    from server import _parse_args
    args = _parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_parse_args_http_transport():
    from server import _parse_args
    args = _parse_args(["--transport", "http"])
    assert args.transport == "http"


def test_parse_args_custom_host_and_port():
    from server import _parse_args
    args = _parse_args(["--transport", "http", "--host", "0.0.0.0", "--port", "9000"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_run_http_server_calls_uvicorn(mocker):
    mock_uvicorn = mocker.patch("uvicorn.run")
    mocker.patch("mcp.server.sse.SseServerTransport")
    from server import run_http_server
    run_http_server("127.0.0.1", 8000)
    mock_uvicorn.assert_called_once()
    call_kwargs = mock_uvicorn.call_args
    assert call_kwargs[1]["host"] == "127.0.0.1"
    assert call_kwargs[1]["port"] == 8000
```

- [ ] **Step 4.4: Run the new tests to confirm they fail**

```bash
pytest tests/test_server.py::test_parse_args_defaults_to_stdio tests/test_server.py::test_run_http_server_calls_uvicorn -v
```

Expected: `ImportError: cannot import name '_parse_args' from 'server'`

- [ ] **Step 4.5: Update server.py**

Replace the `main()` function and the `if __name__ == "__main__"` block at the bottom of `server.py`. Keep everything above `async def main()` unchanged. Replace from `async def main()` to end of file with:

```python
def _parse_args(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Salesforce MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transport")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transport")
    return parser.parse_args(argv)


def run_http_server(host: str, port: int) -> None:
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    import uvicorn

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    uvicorn.run(starlette_app, host=host, port=port)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    args = _parse_args()
    if args.transport == "http":
        run_http_server(args.host, args.port)
    else:
        asyncio.run(main())
```

- [ ] **Step 4.6: Run the server tests**

```bash
pytest tests/test_server.py -v
```

Expected: all pass.

- [ ] **Step 4.7: Run the full test suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 4.8: Commit**

```bash
git add server.py requirements.txt tests/test_server.py
git commit -m "feat: add --transport flag with HTTP/SSE support via Starlette/uvicorn"
```

---

## Task 5: Update .env.example

Document all auth methods clearly.

**Files:**
- Modify: `.env.example`

- [ ] **Step 5.1: Replace .env.example contents**

```bash
# ─── Required ────────────────────────────────────────────────────────────────
SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com

# ─── Auth Method 1: OAuth 2.0 Browser Flow (default) ────────────────────────
# Create a Connected App in Salesforce Setup and paste its credentials here.
SALESFORCE_CLIENT_ID=your_connected_app_consumer_key
SALESFORCE_CLIENT_SECRET=your_connected_app_consumer_secret
SALESFORCE_REDIRECT_URI=http://localhost:8788/callback

# ─── Auth Method 2: Username + Password Flow ─────────────────────────────────
# Set these three vars to skip the browser flow. CLIENT_ID and CLIENT_SECRET
# must also be set (your Connected App must have password flow enabled).
# SALESFORCE_USERNAME=you@yourorg.com
# SALESFORCE_PASSWORD=yourpassword
# SALESFORCE_SECURITY_TOKEN=yoursecuritytoken

# ─── Auth Method 3: Direct Access Token ──────────────────────────────────────
# If you already have a valid access token, set it here. No Connected App needed.
# SALESFORCE_ACCESS_TOKEN=your_access_token
```

- [ ] **Step 5.2: Commit**

```bash
git add .env.example
git commit -m "docs: update .env.example with all three auth methods"
```

---

## Task 6: Write README.md

Create `README.md` at the repo root.

**Files:**
- Create: `README.md`

- [ ] **Step 6.1: Create README.md**

```markdown
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
```

- [ ] **Step 6.2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with auth and deployment guide"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|------------|
| Direct token mode via `SALESFORCE_ACCESS_TOKEN` | Task 2 |
| Username/password flow via 3 env vars | Task 3 |
| Auth priority routing (direct > password > OAuth) | Tasks 2, 3 |
| `CLIENT_ID`/`CLIENT_SECRET` optional | Task 1 |
| `--transport stdio\|http` flag | Task 4 |
| `--host`/`--port` flags | Task 4 |
| HTTP/SSE via Starlette + uvicorn | Task 4 |
| `.env.example` updated | Task 5 |
| README: quick start | Task 6 |
| README: OAuth Connected App walkthrough | Task 6 |
| README: password flow setup | Task 6 |
| README: direct token setup | Task 6 |
| README: Claude Desktop config | Task 6 |
| README: gateway/Docker config | Task 6 |
| README: tools table | Task 6 |
| README: env var reference | Task 6 |

**No gaps found.**

**Type/signature consistency:** `get_token_from_env() -> dict`, `get_token_via_password() -> dict` are defined in Task 2 and Task 3 respectively and referenced consistently. `run_http_server(host: str, port: int) -> None` and `_parse_args(argv=None)` are defined and tested in Task 4.

**No placeholders found.**
