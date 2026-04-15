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


def test_load_tokens_returns_none_when_file_is_corrupt(tmp_path, monkeypatch):
    import auth
    token_file = tmp_path / "tokens.json"
    token_file.write_text("not valid json{{{")
    monkeypatch.setattr(auth, "TOKEN_PATH", str(token_file))
    assert auth.load_tokens() is None


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
