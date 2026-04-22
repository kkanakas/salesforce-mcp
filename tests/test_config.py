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


def test_config_raises_on_missing_instance_url():
    with pytest.raises(KeyError, match="SALESFORCE_INSTANCE_URL"):
        _reload_config(
            overrides={
                "SALESFORCE_CLIENT_ID": "cid",
                "SALESFORCE_CLIENT_SECRET": "csecret",
            },
            remove=["SALESFORCE_INSTANCE_URL"],
        )


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
