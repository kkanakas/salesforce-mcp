import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

import config

TOKEN_PATH = os.path.expanduser("~/.salesforce-mcp/tokens.json")


def load_tokens() -> dict | None:
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        with open(TOKEN_PATH) as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def save_tokens(tokens: dict) -> None:
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f)


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
    except requests.RequestException:
        tokens = run_oauth_flow()
        save_tokens(tokens)
        return tokens
