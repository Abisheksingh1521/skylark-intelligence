import pytest
from config.settings import settings
from monday.queries import validate_query_is_readonly, GET_BOARD_COLUMNS_QUERY, GET_BOARD_ITEMS_QUERY
from monday.client import MondayClient, ReadOnlyEnforcementError, MondayConfigError, MondayAPIError
from monday.schemas import DEALS_COLUMN_MAPPING, WORK_ORDERS_COLUMN_MAPPING
from monday.service import MondayService

def test_readonly_query_enforcement():
    """Verify that mutation queries are strictly blocked by read-only enforcement."""
    mutation_query = """
    mutation {
      create_item (board_id: 12345, item_name: "Test Deal") {
        id
      }
    }
    """
    assert not validate_query_is_readonly(mutation_query)
    
    client = MondayClient(api_token="fake_token")
    with pytest.raises(ReadOnlyEnforcementError) as exc_info:
        client.execute_query(mutation_query)
    assert "Security Violation: Only read-only queries are permitted" in str(exc_info.value)

def test_readonly_valid_queries():
    """Verify valid GraphQL select/read queries pass safety check."""
    assert validate_query_is_readonly(GET_BOARD_COLUMNS_QUERY)
    assert validate_query_is_readonly(GET_BOARD_ITEMS_QUERY)

def test_missing_credentials_raise_config_error():
    """Verify that client raises MondayConfigError when API token is empty."""
    client = MondayClient(api_token="")
    with pytest.raises(MondayConfigError) as exc_info:
        client.execute_query(GET_BOARD_COLUMNS_QUERY, variables={"board_id": ["123"]})
    assert "MONDAY_API_TOKEN is not configured" in str(exc_info.value)

def test_schema_mappings():
    """Verify board column schema mappings match required fields."""
    assert "Deal Name" in DEALS_COLUMN_MAPPING
    assert "Masked Deal value" in DEALS_COLUMN_MAPPING
    assert DEALS_COLUMN_MAPPING["Masked Deal value"] == "deal_value"
    
    assert "Serial #" in WORK_ORDERS_COLUMN_MAPPING
    assert WORK_ORDERS_COLUMN_MAPPING["Serial #"] == "serial_no"
    assert "Billed Value in Rupees (Incl of GST.) (Masked)" in WORK_ORDERS_COLUMN_MAPPING

def test_connection_validation_without_env():
    """Verify connection status returns friendly error when env vars are missing."""
    is_connected, msg = MondayService.validate_connection()
    # Should return False unless valid live keys are in environment
    if not settings.validate_monday_config():
        assert not is_connected
        assert "not configured" in msg.lower()
