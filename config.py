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
