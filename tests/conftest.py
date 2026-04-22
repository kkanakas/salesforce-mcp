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
    import sys
    for key, val in _REQUIRED_ENV.items():
        os.environ[key] = val
    for key in _OPTIONAL_ENV:
        os.environ.pop(key, None)
    sys.modules.pop("config", None)
    sys.modules.pop("auth", None)
    yield
    for key, val in _REQUIRED_ENV.items():
        os.environ[key] = val
    for key in _OPTIONAL_ENV:
        os.environ.pop(key, None)
    sys.modules.pop("config", None)
    sys.modules.pop("auth", None)
