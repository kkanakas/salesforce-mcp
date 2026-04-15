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
