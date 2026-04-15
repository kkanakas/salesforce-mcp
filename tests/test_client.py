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
    client.reset_client()
    mocker.patch("client.auth.get_valid_tokens", return_value={"access_token": "at", "refresh_token": "rt"})
    mock_sf_class = mocker.patch("client.Salesforce")
    mock_sf_class.return_value = mock_sf_class

    client.get_client()
    client.reset_client()
    client.get_client()

    assert mock_sf_class.call_count == 2
