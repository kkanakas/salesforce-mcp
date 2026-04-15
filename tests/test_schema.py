import pytest


@pytest.fixture
def mock_sf(mocker):
    mock = mocker.MagicMock()
    mocker.patch("client.get_client", return_value=mock)
    return mock


def test_list_objects_returns_queryable_objects(mock_sf):
    from tools.schema import list_objects
    mock_sf.describe.return_value = {
        "sobjects": [
            {"name": "Account", "label": "Account", "queryable": True},
            {"name": "Account__History", "label": "Account History", "queryable": False},
            {"name": "Contact__c", "label": "Contact Custom", "queryable": True},
        ]
    }

    result = list_objects()

    assert len(result) == 2
    assert result[0] == {"name": "Account", "label": "Account"}
    assert result[1] == {"name": "Contact__c", "label": "Contact Custom"}


def test_describe_object_returns_field_metadata(mock_sf):
    from tools.schema import describe_object
    mock_sf.Account.describe.return_value = {
        "name": "Account",
        "label": "Account",
        "fields": [
            {"name": "Id", "label": "Account ID", "type": "id"},
            {"name": "Name", "label": "Account Name", "type": "string"},
        ],
    }

    result = describe_object("Account")

    assert result["name"] == "Account"
    assert result["label"] == "Account"
    assert len(result["fields"]) == 2
    assert result["fields"][0] == {"name": "Id", "label": "Account ID", "type": "id"}
    assert result["fields"][1] == {"name": "Name", "label": "Account Name", "type": "string"}
