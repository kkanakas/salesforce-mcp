import json
import pytest
import pytest_asyncio


@pytest.fixture
def mock_tools(mocker):
    mocker.patch("tools.records.query_records", return_value=[{"Id": "001"}])
    mocker.patch("tools.records.get_record", return_value={"Id": "001", "Name": "Acme"})
    mocker.patch("tools.records.create_record", return_value={"id": "002", "success": True, "errors": []})
    mocker.patch("tools.records.update_record", return_value={"status_code": 204})
    mocker.patch("tools.records.delete_record", return_value={"status_code": 204})
    mocker.patch("tools.schema.list_objects", return_value=[{"name": "Account", "label": "Account"}])
    mocker.patch("tools.schema.describe_object", return_value={"name": "Account", "label": "Account", "fields": []})
    mocker.patch("tools.flows.invoke_flow", return_value=[{"isSuccess": True}])


@pytest.mark.asyncio
async def test_list_tools_returns_all_eight_tools(mock_tools):
    from server import handle_list_tools
    tools = await handle_list_tools()
    names = [t.name for t in tools]
    assert set(names) == {
        "query_records", "get_record", "create_record", "update_record",
        "delete_record", "list_objects", "describe_object", "invoke_flow",
    }


@pytest.mark.asyncio
async def test_call_tool_query_records(mock_tools):
    from server import handle_call_tool
    result = await handle_call_tool("query_records", {"soql": "SELECT Id FROM Account"})
    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data == [{"Id": "001"}]


@pytest.mark.asyncio
async def test_call_tool_unknown_tool_returns_error(mock_tools):
    from server import handle_call_tool
    result = await handle_call_tool("nonexistent_tool", {})
    assert "Error" in result[0].text
    assert "Unknown tool" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_salesforce_error_returned_as_text(mock_tools, mocker):
    from server import handle_call_tool
    mocker.patch("tools.records.query_records", side_effect=Exception("INVALID_FIELD: No such column 'Bogus'"))
    result = await handle_call_tool("query_records", {"soql": "SELECT Bogus FROM Account"})
    assert "Error" in result[0].text
    assert "INVALID_FIELD" in result[0].text
