"""
Integration tests — require a live Salesforce sandbox.

Setup:
1. Copy .env.example to .env and fill in your Connected App credentials.
2. Delete ~/.salesforce-mcp/tokens.json to force a fresh OAuth flow, or ensure valid tokens exist.
3. Run: pytest tests/test_integration.py -v -s

These tests create and then delete a Contact record in your sandbox.
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def sf_client():
    """Real Salesforce client using live credentials."""
    import client
    client.reset_client()
    return client.get_client()


def test_query_accounts(sf_client):
    from tools.records import query_records
    results = query_records("SELECT Id, Name FROM Account LIMIT 5")
    assert isinstance(results, list)
    # Sandbox may be empty — just verify structure
    for record in results:
        assert "Id" in record
        assert "Name" in record


def test_list_objects_includes_account(sf_client):
    from tools.schema import list_objects
    objects = list_objects()
    names = [o["name"] for o in objects]
    assert "Account" in names
    assert "Contact" in names


def test_describe_contact_has_expected_fields(sf_client):
    from tools.schema import describe_object
    desc = describe_object("Contact")
    field_names = [f["name"] for f in desc["fields"]]
    assert "Id" in field_names
    assert "FirstName" in field_names
    assert "LastName" in field_names
    assert "Email" in field_names


def test_create_get_update_delete_contact(sf_client):
    from tools.records import create_record, delete_record, get_record, update_record

    # Create
    created = create_record("Contact", {"FirstName": "MCP", "LastName": "TestContact"})
    assert created["success"] is True
    record_id = created["id"]

    try:
        # Get
        record = get_record("Contact", record_id)
        assert record["FirstName"] == "MCP"
        assert record["LastName"] == "TestContact"

        # Update
        update_result = update_record("Contact", record_id, {"LastName": "UpdatedContact"})
        assert update_result["status_code"] == 204

        # Verify update
        updated = get_record("Contact", record_id)
        assert updated["LastName"] == "UpdatedContact"

    finally:
        # Delete (always clean up)
        delete_result = delete_record("Contact", record_id)
        assert delete_result["status_code"] == 204
