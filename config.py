import os

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value or not value.strip():
        raise KeyError(f"Missing required environment variable: {key}")
    return value.strip()


CLIENT_ID = _require("SALESFORCE_CLIENT_ID")
CLIENT_SECRET = _require("SALESFORCE_CLIENT_SECRET")
INSTANCE_URL = _require("SALESFORCE_INSTANCE_URL")
REDIRECT_URI = os.environ.get("SALESFORCE_REDIRECT_URI", "http://localhost:8788/callback")
