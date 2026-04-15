import pytest
import requests as req


@pytest.fixture
def mock_sf_client(mocker):
    mock = mocker.MagicMock()
    mock.session_id = "at"
    mocker.patch("client.get_client", return_value=mock)
    return mock


def test_invoke_flow_posts_to_flow_endpoint(mocker, mock_sf_client):
    from tools.flows import invoke_flow
    mock_post = mocker.patch("tools.flows.requests.post")
    mock_post.return_value.json.return_value = [{"outputValues": {}, "isSuccess": True}]
    mock_post.return_value.raise_for_status = lambda: None

    result = invoke_flow("My_Flow", {"recordId": "001"})

    mock_post.assert_called_once_with(
        "https://test.salesforce.com/services/data/v62.0/actions/custom/flow/My_Flow",
        json={"inputs": [{"recordId": "001"}]},
        headers={
            "Authorization": "Bearer at",
            "Content-Type": "application/json",
        },
    )
    assert result == [{"outputValues": {}, "isSuccess": True}]


def test_invoke_flow_raises_on_http_error(mocker, mock_sf_client):
    from tools.flows import invoke_flow
    mock_post = mocker.patch("tools.flows.requests.post")
    mock_post.return_value.raise_for_status.side_effect = req.HTTPError("404")

    with pytest.raises(req.HTTPError):
        invoke_flow("Nonexistent_Flow", {})
