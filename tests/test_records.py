import pytest


@pytest.fixture
def mock_sf(mocker):
    mock = mocker.MagicMock()
    mocker.patch("client.get_client", return_value=mock)
    return mock


def test_query_records_returns_record_list(mock_sf):
    from tools.records import query_records
    mock_sf.query_all.return_value = {
        "records": [{"Id": "001", "Name": "Acme"}, {"Id": "002", "Name": "Globex"}]
    }

    result = query_records("SELECT Id, Name FROM Account")

    mock_sf.query_all.assert_called_once_with("SELECT Id, Name FROM Account")
    assert result == [{"Id": "001", "Name": "Acme"}, {"Id": "002", "Name": "Globex"}]


def test_query_records_returns_empty_list_when_no_results(mock_sf):
    from tools.records import query_records
    mock_sf.query_all.return_value = {"records": []}

    result = query_records("SELECT Id FROM Account WHERE Name = 'Nobody'")

    assert result == []


def test_get_record_fetches_by_id(mock_sf):
    from tools.records import get_record
    mock_sf.Account.get.return_value = {"Id": "001", "Name": "Acme"}

    result = get_record("Account", "001")

    mock_sf.Account.get.assert_called_once_with("001")
    assert result["Id"] == "001"
    assert result["Name"] == "Acme"


def test_create_record_calls_create_and_returns_result(mock_sf):
    from tools.records import create_record
    mock_sf.Contact.create.return_value = {"id": "003", "success": True, "errors": []}

    result = create_record("Contact", {"FirstName": "Jane", "LastName": "Doe"})

    mock_sf.Contact.create.assert_called_once_with({"FirstName": "Jane", "LastName": "Doe"})
    assert result == {"id": "003", "success": True, "errors": []}


def test_update_record_calls_update_and_returns_status(mock_sf):
    from tools.records import update_record
    mock_sf.Contact.update.return_value = 204

    result = update_record("Contact", "003", {"LastName": "Smith"})

    mock_sf.Contact.update.assert_called_once_with("003", {"LastName": "Smith"})
    assert result == {"status_code": 204}


def test_delete_record_calls_delete_and_returns_status(mock_sf):
    from tools.records import delete_record
    mock_sf.Contact.delete.return_value = 204

    result = delete_record("Contact", "003")

    mock_sf.Contact.delete.assert_called_once_with("003")
    assert result == {"status_code": 204}
