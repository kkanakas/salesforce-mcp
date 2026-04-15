# Salesforce MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python MCP server that exposes Salesforce CRUD, schema discovery, and flow invocation as tools available to Claude via stdio.

**Architecture:** The server uses the official `mcp` Python SDK for protocol handling and `simple-salesforce` for Salesforce REST API calls. OAuth 2.0 tokens are obtained on first run via browser redirect and refreshed silently on subsequent runs. Each tool module is independent and delegates to a shared client singleton.

**Tech Stack:** Python 3.12+, `mcp` (Anthropic MCP SDK), `simple-salesforce`, `python-dotenv`, `requests`, `pytest`, `pytest-mock`

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.py` | Load env vars; fail fast if required vars are missing |
| `auth.py` | OAuth 2.0 flow, token load/save/refresh |
| `client.py` | `simple-salesforce` singleton; resets on re-auth |
| `tools/records.py` | `query_records`, `get_record`, `create_record`, `update_record`, `delete_record` |
| `tools/schema.py` | `list_objects`, `describe_object` |
| `tools/flows.py` | `invoke_flow` |
| `server.py` | MCP `Server` init, tool registration, stdio entrypoint |
| `tests/conftest.py` | Set required env vars before any module import |
| `tests/test_config.py` | Config loading and missing-var behavior |
| `tests/test_auth.py` | Token storage, refresh, OAuth exchange |
| `tests/test_client.py` | Singleton behavior |
| `tests/test_records.py` | All five record tools |
| `tests/test_schema.py` | `list_objects`, `describe_object` |
| `tests/test_flows.py` | `invoke_flow` |
| `tests/test_server.py` | Tool registration and routing |
| `tests/test_integration.py` | Live sandbox round-trip (run manually) |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `tools/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```
mcp>=1.0.0
simple-salesforce>=1.12.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=8.0.0
pytest-mock>=3.12.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Create .gitignore**

```
.env
__pycache__/
*.py[cod]
.pytest_cache/
dist/
*.egg-info/
.venv/
```

- [ ] **Step 3: Create .env.example**

```
SALESFORCE_CLIENT_ID=your_connected_app_consumer_key
SALESFORCE_CLIENT_SECRET=your_connected_app_consumer_secret
SALESFORCE_INSTANCE_URL=https://yourorg.my.salesforce.com
SALESFORCE_REDIRECT_URI=http://localhost:8788/callback
```

- [ ] **Step 4: Create package init files**

Create `tools/__init__.py` — empty file.
Create `tests/__init__.py` — empty file.

- [ ] **Step 5: Create tests/conftest.py**

```python
import os

# Set env vars at module scope so they are available before any import.
os.environ.setdefault("SALESFORCE_CLIENT_ID", "test_client_id")
os.environ.setdefault("SALESFORCE_CLIENT_SECRET", "test_secret")
os.environ.setdefault("SALESFORCE_INSTANCE_URL", "https://test.salesforce.com")
os.environ.setdefault("SALESFORCE_REDIRECT_URI", "http://localhost:8788/callback")
```

- [ ] **Step 6: Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .gitignore .env.example tools/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: project scaffolding"
```

---

## Task 2: Config Module

**Files:**
- Create: `tests/test_config.py`
- Create: `config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
import importlib
import os
import sys
import pytest


def _reload_config(overrides: dict = {}, remove: list = []):
    """Reload config with custom env, clearing module cache first."""
    for key in remove:
        os.environ.pop(key, None)
    for key, val in overrides.items():
        os.environ[key] = val
    sys.modules.pop("config", None)
    import config
    return config


def test_config_loads_all_vars():
    cfg = _reload_config({
        "SALESFORCE_CLIENT_ID": "cid",
        "SALESFORCE_CLIENT_SECRET": "csecret",
        "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
        "SALESFORCE_REDIRECT_URI": "http://localhost:8788/callback",
    })
    assert cfg.CLIENT_ID == "cid"
    assert cfg.CLIENT_SECRET == "csecret"
    assert cfg.INSTANCE_URL == "https://org.salesforce.com"
    assert cfg.REDIRECT_URI == "http://localhost:8788/callback"


def test_config_redirect_uri_defaults():
    cfg = _reload_config(
        overrides={
            "SALESFORCE_CLIENT_ID": "cid",
            "SALESFORCE_CLIENT_SECRET": "csecret",
            "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
        },
        remove=["SALESFORCE_REDIRECT_URI"],
    )
    assert cfg.REDIRECT_URI == "http://localhost:8788/callback"


def test_config_raises_on_missing_client_id():
    with pytest.raises(KeyError, match="SALESFORCE_CLIENT_ID"):
        _reload_config(
            overrides={
                "SALESFORCE_CLIENT_SECRET": "csecret",
                "SALESFORCE_INSTANCE_URL": "https://org.salesforce.com",
            },
            remove=["SALESFORCE_CLIENT_ID"],
        )


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

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'` or `ImportError`.

- [ ] **Step 3: Implement config.py**

```python
import os

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise KeyError(f"Missing required environment variable: {key}")
    return value


CLIENT_ID = _require("SALESFORCE_CLIENT_ID")
CLIENT_SECRET = _require("SALESFORCE_CLIENT_SECRET")
INSTANCE_URL = _require("SALESFORCE_INSTANCE_URL")
REDIRECT_URI = os.environ.get("SALESFORCE_REDIRECT_URI", "http://localhost:8788/callback")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add config module with env var loading"
```

---

## Task 3: Auth — Token Storage

**Files:**
- Create: `tests/test_auth.py`
- Create: `auth.py` (token storage portion)

- [ ] **Step 1: Write failing tests for token storage**

Create `tests/test_auth.py`:

```python
import json
import pytest


def test_load_tokens_returns_none_when_file_missing(tmp_path, monkeypatch):
    import auth
    monkeypatch.setattr(auth, "TOKEN_PATH", str(tmp_path / "tokens.json"))
    assert auth.load_tokens() is None


def test_load_tokens_returns_parsed_json(tmp_path, monkeypatch):
    import auth
    token_file = tmp_path / "tokens.json"
    token_file.write_text('{"access_token": "abc", "refresh_token": "xyz"}')
    monkeypatch.setattr(auth, "TOKEN_PATH", str(token_file))
    result = auth.load_tokens()
    assert result == {"access_token": "abc", "refresh_token": "xyz"}


def test_save_tokens_creates_directories_and_writes_json(tmp_path, monkeypatch):
    import auth
    token_path = str(tmp_path / "subdir" / "tokens.json")
    monkeypatch.setattr(auth, "TOKEN_PATH", token_path)
    auth.save_tokens({"access_token": "abc", "refresh_token": "xyz"})
    with open(token_path) as f:
        data = json.load(f)
    assert data == {"access_token": "abc", "refresh_token": "xyz"}


def test_save_tokens_overwrites_existing(tmp_path, monkeypatch):
    import auth
    token_file = tmp_path / "tokens.json"
    token_file.write_text('{"access_token": "old"}')
    monkeypatch.setattr(auth, "TOKEN_PATH", str(token_file))
    auth.save_tokens({"access_token": "new", "refresh_token": "r"})
    assert json.loads(token_file.read_text())["access_token"] == "new"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'auth'`.

- [ ] **Step 3: Implement auth.py (token storage only)**

```python
import json
import os
from urllib.parse import parse_qs, urlencode, urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser

import requests

import config

TOKEN_PATH = os.path.expanduser("~/.salesforce-mcp/tokens.json")


def load_tokens() -> dict | None:
    if not os.path.exists(TOKEN_PATH):
        return None
    with open(TOKEN_PATH) as f:
        return json.load(f)


def save_tokens(tokens: dict) -> None:
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add auth module with token storage"
```

---

## Task 4: Auth — Token Exchange and Refresh

**Files:**
- Modify: `tests/test_auth.py` (add exchange/refresh tests)
- Modify: `auth.py` (add `_exchange_code`, `refresh_access_token`)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_auth.py`:

```python
def test_exchange_code_posts_to_token_endpoint(mocker):
    import auth
    mock_post = mocker.patch("auth.requests.post")
    mock_post.return_value.json.return_value = {
        "access_token": "at",
        "refresh_token": "rt",
    }
    mock_post.return_value.raise_for_status = lambda: None

    result = auth._exchange_code("mycode")

    mock_post.assert_called_once_with(
        "https://test.salesforce.com/services/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "redirect_uri": "http://localhost:8788/callback",
            "code": "mycode",
        },
    )
    assert result == {"access_token": "at", "refresh_token": "rt"}


def test_refresh_access_token_posts_to_token_endpoint(mocker):
    import auth
    mock_post = mocker.patch("auth.requests.post")
    mock_post.return_value.json.return_value = {"access_token": "new_at"}
    mock_post.return_value.raise_for_status = lambda: None

    result = auth.refresh_access_token("old_rt")

    mock_post.assert_called_once_with(
        "https://test.salesforce.com/services/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "refresh_token": "old_rt",
        },
    )
    assert result == {"access_token": "new_at"}


def test_refresh_access_token_raises_on_http_error(mocker):
    import auth
    import requests as req
    mock_post = mocker.patch("auth.requests.post")
    mock_post.return_value.raise_for_status.side_effect = req.HTTPError("401")

    with pytest.raises(req.HTTPError):
        auth.refresh_access_token("bad_rt")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_auth.py::test_exchange_code_posts_to_token_endpoint tests/test_auth.py::test_refresh_access_token_posts_to_token_endpoint tests/test_auth.py::test_refresh_access_token_raises_on_http_error -v
```

Expected: `AttributeError: module 'auth' has no attribute '_exchange_code'`.

- [ ] **Step 3: Add `_exchange_code` and `refresh_access_token` to auth.py**

Append to `auth.py` after `save_tokens`:

```python

def _exchange_code(code: str) -> dict:
    response = requests.post(
        f"{config.INSTANCE_URL}/services/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET,
            "redirect_uri": config.REDIRECT_URI,
            "code": code,
        },
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str) -> dict:
    response = requests.post(
        f"{config.INSTANCE_URL}/services/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": config.CLIENT_ID,
            "client_secret": config.CLIENT_SECRET,
            "refresh_token": refresh_token,
        },
    )
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 4: Run all auth tests**

```bash
pytest tests/test_auth.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add OAuth code exchange and token refresh"
```

---

## Task 5: Auth — OAuth Flow and get_valid_tokens

**Files:**
- Modify: `tests/test_auth.py` (add flow/get_valid_tokens tests)
- Modify: `auth.py` (add `run_oauth_flow`, `get_valid_tokens`)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_auth.py`:

```python
def test_get_valid_tokens_runs_oauth_flow_when_no_tokens(tmp_path, mocker, monkeypatch):
    import auth
    monkeypatch.setattr(auth, "TOKEN_PATH", str(tmp_path / "tokens.json"))
    mock_flow = mocker.patch("auth.run_oauth_flow", return_value={"access_token": "at", "refresh_token": "rt"})
    mocker.patch("auth.save_tokens")

    result = auth.get_valid_tokens()

    mock_flow.assert_called_once()
    assert result["access_token"] == "at"


def test_get_valid_tokens_refreshes_when_tokens_exist(tmp_path, mocker, monkeypatch):
    import auth
    token_file = tmp_path / "tokens.json"
    token_file.write_text('{"access_token": "old_at", "refresh_token": "rt"}')
    monkeypatch.setattr(auth, "TOKEN_PATH", str(token_file))
    mock_refresh = mocker.patch(
        "auth.refresh_access_token",
        return_value={"access_token": "new_at"},
    )
    mocker.patch("auth.save_tokens")

    result = auth.get_valid_tokens()

    mock_refresh.assert_called_once_with("rt")
    assert result["access_token"] == "new_at"
    # refresh_token preserved when not returned by refresh endpoint
    assert result["refresh_token"] == "rt"


def test_get_valid_tokens_falls_back_to_oauth_flow_when_refresh_fails(tmp_path, mocker, monkeypatch):
    import auth
    import requests as req
    token_file = tmp_path / "tokens.json"
    token_file.write_text('{"access_token": "old_at", "refresh_token": "bad_rt"}')
    monkeypatch.setattr(auth, "TOKEN_PATH", str(token_file))
    mocker.patch("auth.refresh_access_token", side_effect=req.HTTPError("401"))
    mock_flow = mocker.patch("auth.run_oauth_flow", return_value={"access_token": "new_at", "refresh_token": "new_rt"})
    mocker.patch("auth.save_tokens")

    result = auth.get_valid_tokens()

    mock_flow.assert_called_once()
    assert result["access_token"] == "new_at"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_auth.py::test_get_valid_tokens_runs_oauth_flow_when_no_tokens tests/test_auth.py::test_get_valid_tokens_refreshes_when_tokens_exist tests/test_auth.py::test_get_valid_tokens_falls_back_to_oauth_flow_when_refresh_fails -v
```

Expected: `AttributeError: module 'auth' has no attribute 'get_valid_tokens'`.

- [ ] **Step 3: Add `run_oauth_flow` and `get_valid_tokens` to auth.py**

Append to `auth.py`:

```python

def run_oauth_flow() -> dict:
    auth_url = f"{config.INSTANCE_URL}/services/oauth2/authorize?" + urlencode(
        {
            "response_type": "code",
            "client_id": config.CLIENT_ID,
            "redirect_uri": config.REDIRECT_URI,
        }
    )

    auth_code = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            params = parse_qs(urlparse(self.path).query)
            auth_code = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authentication successful. You can close this tab.")

        def log_message(self, format, *args):
            pass  # suppress server logs

    print("Opening browser for Salesforce authentication...")
    print(f"If the browser does not open, visit: {auth_url}")
    webbrowser.open(auth_url)
    server = HTTPServer(("localhost", 8788), CallbackHandler)
    server.handle_request()

    if not auth_code:
        raise RuntimeError("OAuth flow failed: no authorization code received")

    return _exchange_code(auth_code)


def get_valid_tokens() -> dict:
    tokens = load_tokens()

    if tokens is None:
        tokens = run_oauth_flow()
        save_tokens(tokens)
        return tokens

    try:
        new_tokens = refresh_access_token(tokens["refresh_token"])
        # Refresh endpoint may not return a new refresh_token; preserve the existing one.
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = tokens["refresh_token"]
        save_tokens(new_tokens)
        return new_tokens
    except Exception:
        tokens = run_oauth_flow()
        save_tokens(tokens)
        return tokens
```

- [ ] **Step 4: Run all auth tests**

```bash
pytest tests/test_auth.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add OAuth flow and get_valid_tokens"
```

---

## Task 6: Salesforce Client

**Files:**
- Create: `tests/test_client.py`
- Create: `client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_client.py`:

```python
import pytest


def test_get_client_returns_salesforce_instance(mocker):
    import client
    client.reset_client()
    mocker.patch("client.auth.get_valid_tokens", return_value={"access_token": "at", "refresh_token": "rt"})
    mock_sf_class = mocker.patch("client.Salesforce")
    mock_sf_class.return_value = mock_sf_class

    result = client.get_client()

    mock_sf_class.assert_called_once_with(
        instance_url="https://test.salesforce.com",
        session_id="at",
    )
    assert result is mock_sf_class


def test_get_client_returns_singleton(mocker):
    import client
    client.reset_client()
    mocker.patch("client.auth.get_valid_tokens", return_value={"access_token": "at", "refresh_token": "rt"})
    mock_sf_class = mocker.patch("client.Salesforce")
    mock_sf_class.return_value = mock_sf_class

    first = client.get_client()
    second = client.get_client()

    assert first is second
    mock_sf_class.assert_called_once()  # constructor called only once


def test_reset_client_clears_singleton(mocker):
    import client
    mocker.patch("client.auth.get_valid_tokens", return_value={"access_token": "at", "refresh_token": "rt"})
    mock_sf_class = mocker.patch("client.Salesforce")
    mock_sf_class.return_value = mock_sf_class

    client.get_client()
    client.reset_client()
    client.get_client()

    assert mock_sf_class.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'client'`.

- [ ] **Step 3: Implement client.py**

```python
from simple_salesforce import Salesforce

import auth
import config

_client: Salesforce | None = None


def get_client() -> Salesforce:
    global _client
    if _client is None:
        tokens = auth.get_valid_tokens()
        _client = Salesforce(
            instance_url=config.INSTANCE_URL,
            session_id=tokens["access_token"],
        )
    return _client


def reset_client() -> None:
    """Reset the singleton — used in tests and after re-authentication."""
    global _client
    _client = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_client.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add client.py tests/test_client.py
git commit -m "feat: add Salesforce client singleton"
```

---

## Task 7: Records Tools — query_records and get_record

**Files:**
- Create: `tests/test_records.py`
- Create: `tools/records.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_records.py`:

```python
import pytest


@pytest.fixture
def mock_sf(mocker):
    mock = mocker.MagicMock()
    mocker.patch("client.get_client", return_value=mock)
    return mock


def test_query_records_returns_record_list(mock_sf):
    from tools.records import query_records
    mock_sf.query_all.return_value = {
        "records": [{"Id": "001", "Name": "Acme"}, {"Id": "002", "Name": "Globex"}]
    }

    result = query_records("SELECT Id, Name FROM Account")

    mock_sf.query_all.assert_called_once_with("SELECT Id, Name FROM Account")
    assert result == [{"Id": "001", "Name": "Acme"}, {"Id": "002", "Name": "Globex"}]


def test_query_records_returns_empty_list_when_no_results(mock_sf):
    from tools.records import query_records
    mock_sf.query_all.return_value = {"records": []}

    result = query_records("SELECT Id FROM Account WHERE Name = 'Nobody'")

    assert result == []


def test_get_record_fetches_by_id(mock_sf):
    from tools.records import get_record
    mock_sf.Account.get.return_value = {"Id": "001", "Name": "Acme"}

    result = get_record("Account", "001")

    mock_sf.Account.get.assert_called_once_with("001")
    assert result["Id"] == "001"
    assert result["Name"] == "Acme"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_records.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.records'`.

- [ ] **Step 3: Implement query_records and get_record in tools/records.py**

> Use `import client; client.get_client()` (not `from client import get_client`) so `mocker.patch("client.get_client", ...)` intercepts the call correctly in tests.

```python
import client


def query_records(soql: str) -> list[dict]:
    sf = client.get_client()
    result = sf.query_all(soql)
    return result["records"]


def get_record(object_name: str, record_id: str) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    return dict(obj.get(record_id))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_records.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/records.py tests/test_records.py
git commit -m "feat: add query_records and get_record tools"
```

---

## Task 8: Records Tools — create_record, update_record, delete_record

**Files:**
- Modify: `tests/test_records.py` (add 3 more tests)
- Modify: `tools/records.py` (add 3 more functions)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_records.py`:

```python
def test_create_record_calls_create_and_returns_result(mock_sf):
    from tools.records import create_record
    mock_sf.Contact.create.return_value = {"id": "003", "success": True, "errors": []}

    result = create_record("Contact", {"FirstName": "Jane", "LastName": "Doe"})

    mock_sf.Contact.create.assert_called_once_with({"FirstName": "Jane", "LastName": "Doe"})
    assert result == {"id": "003", "success": True, "errors": []}


def test_update_record_calls_update_and_returns_status(mock_sf):
    from tools.records import update_record
    mock_sf.Contact.update.return_value = 204

    result = update_record("Contact", "003", {"LastName": "Smith"})

    mock_sf.Contact.update.assert_called_once_with("003", {"LastName": "Smith"})
    assert result == {"status_code": 204}


def test_delete_record_calls_delete_and_returns_status(mock_sf):
    from tools.records import delete_record
    mock_sf.Contact.delete.return_value = 204

    result = delete_record("Contact", "003")

    mock_sf.Contact.delete.assert_called_once_with("003")
    assert result == {"status_code": 204}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_records.py::test_create_record_calls_create_and_returns_result tests/test_records.py::test_update_record_calls_update_and_returns_status tests/test_records.py::test_delete_record_calls_delete_and_returns_status -v
```

Expected: `ImportError: cannot import name 'create_record'`.

- [ ] **Step 3: Add create, update, delete to tools/records.py**

Append to `tools/records.py`:

```python

def create_record(object_name: str, fields: dict) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    return obj.create(fields)


def update_record(object_name: str, record_id: str, fields: dict) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    result = obj.update(record_id, fields)
    return {"status_code": result}


def delete_record(object_name: str, record_id: str) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    result = obj.delete(record_id)
    return {"status_code": result}
```

- [ ] **Step 4: Run all records tests**

```bash
pytest tests/test_records.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/records.py tests/test_records.py
git commit -m "feat: add create, update, delete record tools"
```

---

## Task 9: Schema Tools

**Files:**
- Create: `tests/test_schema.py`
- Create: `tools/schema.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_schema.py`:

```python
import pytest


@pytest.fixture
def mock_sf(mocker):
    mock = mocker.MagicMock()
    mocker.patch("client.get_client", return_value=mock)
    return mock


def test_list_objects_returns_queryable_objects(mock_sf):
    from tools.schema import list_objects
    mock_sf.describe.return_value = {
        "sobjects": [
            {"name": "Account", "label": "Account", "queryable": True},
            {"name": "Account__History", "label": "Account History", "queryable": False},
            {"name": "Contact__c", "label": "Contact Custom", "queryable": True},
        ]
    }

    result = list_objects()

    assert len(result) == 2
    assert result[0] == {"name": "Account", "label": "Account"}
    assert result[1] == {"name": "Contact__c", "label": "Contact Custom"}


def test_describe_object_returns_field_metadata(mock_sf):
    from tools.schema import describe_object
    mock_sf.Account.describe.return_value = {
        "name": "Account",
        "label": "Account",
        "fields": [
            {"name": "Id", "label": "Account ID", "type": "id"},
            {"name": "Name", "label": "Account Name", "type": "string"},
        ],
    }

    result = describe_object("Account")

    assert result["name"] == "Account"
    assert result["label"] == "Account"
    assert len(result["fields"]) == 2
    assert result["fields"][0] == {"name": "Id", "label": "Account ID", "type": "id"}
    assert result["fields"][1] == {"name": "Name", "label": "Account Name", "type": "string"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_schema.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.schema'`.

- [ ] **Step 3: Implement tools/schema.py**

> Same `import client; client.get_client()` pattern so the mock fixture works correctly.

```python
import client


def list_objects() -> list[dict]:
    sf = client.get_client()
    result = sf.describe()
    return [
        {"name": obj["name"], "label": obj["label"]}
        for obj in result["sobjects"]
        if obj["queryable"]
    ]


def describe_object(object_name: str) -> dict:
    sf = client.get_client()
    obj = getattr(sf, object_name)
    desc = obj.describe()
    return {
        "name": desc["name"],
        "label": desc["label"],
        "fields": [
            {"name": f["name"], "label": f["label"], "type": f["type"]}
            for f in desc["fields"]
        ],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_schema.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/schema.py tests/test_schema.py
git commit -m "feat: add list_objects and describe_object schema tools"
```

---

## Task 10: Flow Tools

**Files:**
- Create: `tests/test_flows.py`
- Create: `tools/flows.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_flows.py`:

```python
import pytest
import requests as req


@pytest.fixture
def mock_tokens(mocker):
    mocker.patch("auth.get_valid_tokens", return_value={"access_token": "at", "refresh_token": "rt"})


def test_invoke_flow_posts_to_flow_endpoint(mocker, mock_tokens):
    from tools.flows import invoke_flow
    mock_post = mocker.patch("tools.flows.requests.post")
    mock_post.return_value.json.return_value = [{"outputValues": {}, "isSuccess": True}]
    mock_post.return_value.raise_for_status = lambda: None

    result = invoke_flow("My_Flow", {"recordId": "001"})

    mock_post.assert_called_once_with(
        "https://test.salesforce.com/services/data/v62.0/actions/custom/flow/My_Flow",
        json={"inputs": [{"recordId": "001"}]},
        headers={
            "Authorization": "Bearer at",
            "Content-Type": "application/json",
        },
    )
    assert result == [{"outputValues": {}, "isSuccess": True}]


def test_invoke_flow_raises_on_http_error(mocker, mock_tokens):
    from tools.flows import invoke_flow
    mock_post = mocker.patch("tools.flows.requests.post")
    mock_post.return_value.raise_for_status.side_effect = req.HTTPError("404")

    with pytest.raises(req.HTTPError):
        invoke_flow("Nonexistent_Flow", {})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_flows.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.flows'`.

- [ ] **Step 3: Implement tools/flows.py**

```python
import requests

import auth
import config


def invoke_flow(flow_api_name: str, inputs: dict) -> dict:
    tokens = auth.get_valid_tokens()
    url = f"{config.INSTANCE_URL}/services/data/v62.0/actions/custom/flow/{flow_api_name}"
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, json={"inputs": [inputs]}, headers=headers)
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_flows.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/flows.py tests/test_flows.py
git commit -m "feat: add invoke_flow tool"
```

---

## Task 11: MCP Server

**Files:**
- Create: `tests/test_server.py`
- Create: `server.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_server.py`:

```python
import json
import pytest
import pytest_asyncio


@pytest.fixture
def mock_tools(mocker):
    mocker.patch("tools.records.query_records", return_value=[{"Id": "001"}])
    mocker.patch("tools.records.get_record", return_value={"Id": "001", "Name": "Acme"})
    mocker.patch("tools.records.create_record", return_value={"id": "002", "success": True, "errors": []})
    mocker.patch("tools.records.update_record", return_value={"status_code": 204})
    mocker.patch("tools.records.delete_record", return_value={"status_code": 204})
    mocker.patch("tools.schema.list_objects", return_value=[{"name": "Account", "label": "Account"}])
    mocker.patch("tools.schema.describe_object", return_value={"name": "Account", "label": "Account", "fields": []})
    mocker.patch("tools.flows.invoke_flow", return_value=[{"isSuccess": True}])


@pytest.mark.asyncio
async def test_list_tools_returns_all_eight_tools(mock_tools):
    from server import handle_list_tools
    tools = await handle_list_tools()
    names = [t.name for t in tools]
    assert set(names) == {
        "query_records", "get_record", "create_record", "update_record",
        "delete_record", "list_objects", "describe_object", "invoke_flow",
    }


@pytest.mark.asyncio
async def test_call_tool_query_records(mock_tools):
    from server import handle_call_tool
    result = await handle_call_tool("query_records", {"soql": "SELECT Id FROM Account"})
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data == [{"Id": "001"}]


@pytest.mark.asyncio
async def test_call_tool_unknown_tool_returns_error(mock_tools):
    from server import handle_call_tool
    result = await handle_call_tool("nonexistent_tool", {})
    assert "Error" in result[0].text
    assert "Unknown tool" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_salesforce_error_returned_as_text(mock_tools, mocker):
    from server import handle_call_tool
    mocker.patch("tools.records.query_records", side_effect=Exception("INVALID_FIELD: No such column 'Bogus'"))
    result = await handle_call_tool("query_records", {"soql": "SELECT Bogus FROM Account"})
    assert "Error" in result[0].text
    assert "INVALID_FIELD" in result[0].text
```

- [ ] **Step 2: Add pytest-asyncio config to pyproject.toml or pytest.ini**

Create `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_server.py -v
```

Expected: `ModuleNotFoundError: No module named 'server'`.

- [ ] **Step 4: Implement server.py**

```python
import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools.flows import invoke_flow
from tools.records import create_record, delete_record, get_record, query_records, update_record
from tools.schema import describe_object, list_objects

app = Server("salesforce-mcp")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_records",
            description="Run a SOQL query against Salesforce. Returns a list of matching records.",
            inputSchema={
                "type": "object",
                "properties": {
                    "soql": {
                        "type": "string",
                        "description": "A valid SOQL query, e.g. SELECT Id, Name FROM Account LIMIT 10",
                    }
                },
                "required": ["soql"],
            },
        ),
        Tool(
            name="get_record",
            description="Fetch a single Salesforce record by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Salesforce object API name, e.g. Account"},
                    "record_id": {"type": "string", "description": "18-character Salesforce record ID"},
                },
                "required": ["object_name", "record_id"],
            },
        ),
        Tool(
            name="create_record",
            description="Create a new Salesforce record. Use describe_object first to check available fields.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Salesforce object API name, e.g. Contact"},
                    "fields": {"type": "object", "description": "Field name/value pairs for the new record"},
                },
                "required": ["object_name", "fields"],
            },
        ),
        Tool(
            name="update_record",
            description="Update fields on an existing Salesforce record.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "record_id": {"type": "string"},
                    "fields": {"type": "object", "description": "Field name/value pairs to update"},
                },
                "required": ["object_name", "record_id", "fields"],
            },
        ),
        Tool(
            name="delete_record",
            description="Delete a Salesforce record by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "record_id": {"type": "string"},
                },
                "required": ["object_name", "record_id"],
            },
        ),
        Tool(
            name="list_objects",
            description="List all queryable Salesforce objects in the org, including standard and custom objects.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="describe_object",
            description="Get field metadata for a Salesforce object — field names, types, and labels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "Salesforce object API name, e.g. Opportunity",
                    }
                },
                "required": ["object_name"],
            },
        ),
        Tool(
            name="invoke_flow",
            description="Trigger an autolaunched Salesforce flow with input variables.",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_api_name": {"type": "string", "description": "The API name of the flow"},
                    "inputs": {
                        "type": "object",
                        "description": "Input variable name/value pairs for the flow",
                    },
                },
                "required": ["flow_api_name", "inputs"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "query_records":
            result = query_records(arguments["soql"])
        elif name == "get_record":
            result = get_record(arguments["object_name"], arguments["record_id"])
        elif name == "create_record":
            result = create_record(arguments["object_name"], arguments["fields"])
        elif name == "update_record":
            result = update_record(arguments["object_name"], arguments["record_id"], arguments["fields"])
        elif name == "delete_record":
            result = delete_record(arguments["object_name"], arguments["record_id"])
        elif name == "list_objects":
            result = list_objects()
        elif name == "describe_object":
            result = describe_object(arguments["object_name"])
        elif name == "invoke_flow":
            result = invoke_flow(arguments["flow_api_name"], arguments["inputs"])
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/test_server.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Run the full test suite**

```bash
pytest -v
```

Expected: all tests PASS. Note: `test_integration.py` does not exist yet — that is fine.

- [ ] **Step 7: Commit**

```bash
git add server.py tests/test_server.py pytest.ini
git commit -m "feat: add MCP server with all tool registrations"
```

---

## Task 12: Integration Test and Smoke Test

**Files:**
- Create: `tests/test_integration.py`

> **Note:** This test hits a live Salesforce sandbox. Do NOT run it in CI. Run manually: `pytest tests/test_integration.py -v -s`

- [ ] **Step 1: Create the integration test**

Create `tests/test_integration.py`:

```python
"""
Integration tests — require a live Salesforce sandbox.

Setup:
1. Copy .env.example to .env and fill in your Connected App credentials.
2. Delete ~/.salesforce-mcp/tokens.json to force a fresh OAuth flow, or ensure valid tokens exist.
3. Run: pytest tests/test_integration.py -v -s

These tests create and then delete a Contact record in your sandbox.
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def sf_client():
    """Real Salesforce client using live credentials."""
    import client
    client.reset_client()
    return client.get_client()


def test_query_accounts(sf_client):
    from tools.records import query_records
    results = query_records("SELECT Id, Name FROM Account LIMIT 5")
    assert isinstance(results, list)
    # Sandbox may be empty — just verify structure
    for record in results:
        assert "Id" in record
        assert "Name" in record


def test_list_objects_includes_account(sf_client):
    from tools.schema import list_objects
    objects = list_objects()
    names = [o["name"] for o in objects]
    assert "Account" in names
    assert "Contact" in names


def test_describe_contact_has_expected_fields(sf_client):
    from tools.schema import describe_object
    desc = describe_object("Contact")
    field_names = [f["name"] for f in desc["fields"]]
    assert "Id" in field_names
    assert "FirstName" in field_names
    assert "LastName" in field_names
    assert "Email" in field_names


def test_create_get_update_delete_contact(sf_client):
    from tools.records import create_record, delete_record, get_record, update_record

    # Create
    created = create_record("Contact", {"FirstName": "MCP", "LastName": "TestContact"})
    assert created["success"] is True
    record_id = created["id"]

    try:
        # Get
        record = get_record("Contact", record_id)
        assert record["FirstName"] == "MCP"
        assert record["LastName"] == "TestContact"

        # Update
        update_result = update_record("Contact", record_id, {"LastName": "UpdatedContact"})
        assert update_result["status_code"] == 204

        # Verify update
        updated = get_record("Contact", record_id)
        assert updated["LastName"] == "UpdatedContact"

    finally:
        # Delete (always clean up)
        delete_result = delete_record("Contact", record_id)
        assert delete_result["status_code"] == 204
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for full CRUD round-trip"
```

- [ ] **Step 3: Wire up Claude Desktop**

Add the following to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "salesforce": {
      "command": "/absolute/path/to/salesforce-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/salesforce-mcp/server.py"]
    }
  }
}
```

Replace `/absolute/path/to/salesforce-mcp` with the actual path from `pwd` in the project directory.

- [ ] **Step 4: Smoke test**

1. Restart Claude Desktop.
2. In a new Claude conversation, look for the hammer icon — the `salesforce` MCP server should appear.
3. Ask: "List all Salesforce objects available in my org."
4. Expected: Claude calls `list_objects` and returns a list including `Account`, `Contact`, `Opportunity`.

---

## Final Unit Test Run

After Task 12, run the full unit suite one last time to confirm nothing is broken:

```bash
pytest tests/ --ignore=tests/test_integration.py -v
```

Expected: all tests PASS.
