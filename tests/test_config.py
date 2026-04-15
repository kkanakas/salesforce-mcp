import os
import sys
import pytest


def _reload_config(overrides: dict | None = None, remove: list | None = None):
    overrides = overrides or {}
    remove = remove or []
    """Reload config module with given environment variables."""
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
