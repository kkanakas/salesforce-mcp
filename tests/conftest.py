import os
import pytest

# Set env vars at module scope so they are available before any import.
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


@pytest.fixture(autouse=True)
def restore_env():
    """Restore required env vars before each test so test_config teardown doesn't break later tests."""
    for key, val in _REQUIRED_ENV.items():
        os.environ[key] = val
    yield
    for key, val in _REQUIRED_ENV.items():
        os.environ[key] = val
