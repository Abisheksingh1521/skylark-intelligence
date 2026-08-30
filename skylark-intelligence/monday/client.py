import requests
import time
import logging
from typing import Dict, Any, List, Optional
from config.settings import settings
from monday.queries import validate_query_is_readonly, GET_BOARD_COLUMNS_QUERY, GET_BOARD_ITEMS_QUERY

logger = logging.getLogger(__name__)

class MondayAPIError(Exception):
    """Raised when Monday.com API returns an error payload."""
    pass

class MondayConnectionError(Exception):
    """Raised when connection to Monday.com fails or times out."""
    pass

class MondayConfigError(Exception):
    """Raised when Monday API environment variables are missing."""
    pass

class ReadOnlyEnforcementError(Exception):
    """Raised if an illegal mutation query is attempted."""
    pass


class MondayClient:
    """
    Read-only Monday.com GraphQL API Client.
    Supports cursor pagination, retry handling, timeouts, and error handling.
    """
    
    def __init__(self, api_token: Optional[str] = None, api_url: str = "https://api.monday.com/v2"):
        # Store provided token; if None, fallback to env var. Empty string is kept to trigger credential check later.
        self.api_token = api_token if api_token is not None else settings.MONDAY_API_TOKEN
        self.api_url = api_url
        self.headers = {
            "Authorization": self.api_token,
            "API-Version": "2023-10",
            "Content-Type": "application/json"
        }
    
    def _check_credentials(self):
        if not self.api_token:
            raise MondayConfigError("MONDAY_API_TOKEN is not configured in environment variables.")

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Dict[str, Any]:
        """
        Executes a read-only GraphQL query against Monday.com API.
        Enforces read-only constraint and performs retries on transient errors.
        """
        self._check_credentials()
        
        # Enforce read-only constraint
        if not validate_query_is_readonly(query):
            raise ReadOnlyEnforcementError("Security Violation: Only read-only queries are permitted. Mutation queries are strictly forbidden.")
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        max_retries = settings.MAX_RETRIES
        backoff = 1.0
        
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=timeout
                )
                
                # Handle Rate Limiting (429) and Server Errors (5xx)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < max_retries:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    response.raise_for_status()
                
                if response.status_code == 401:
                    raise MondayAPIError("Invalid Monday.com API Token (401 Unauthorized).")
                
                response.raise_for_status()
                res_data = response.json()
                
                # Check for GraphQL errors
                if "errors" in res_data:
                    error_msgs = [err.get("message", "Unknown GraphQL error") for err in res_data["errors"]]
                    raise MondayAPIError(f"Monday API Error: {'; '.join(error_msgs)}")
                
                return res_data.get("data", {})
                
            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise MondayConnectionError(f"Request to Monday.com API timed out after {timeout}s.") from e
            except requests.exceptions.RequestException as e:
                if attempt < max_retries and not isinstance(e, requests.exceptions.HTTPError):
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise MondayConnectionError(f"Failed to connect to Monday.com API: {str(e)}") from e

    def get_board_columns(self, board_id: str) -> List[Dict[str, Any]]:
        """Fetch board metadata and column definitions."""
        data = self.execute_query(GET_BOARD_COLUMNS_QUERY, variables={"board_id": [board_id]})
        boards = data.get("boards", [])
        if not boards:
            raise MondayAPIError(f"Board with ID '{board_id}' not found or accessible.")
        return boards[0].get("columns", [])

    def fetch_all_items(self, board_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all items from a board using cursor-based pagination.
        Handles cursor loops until all pages are retrieved.
        """
        all_items = []
        cursor = None
        
        while True:
            variables = {"board_id": [board_id], "limit": limit}
            if cursor:
                variables["cursor"] = cursor
                
            data = self.execute_query(GET_BOARD_ITEMS_QUERY, variables=variables)
            boards = data.get("boards", [])
            if not boards:
                raise MondayAPIError(f"Board with ID '{board_id}' not found or accessible.")
            
            items_page = boards[0].get("items_page", {})
            page_items = items_page.get("items", [])
            all_items.extend(page_items)
            
            new_cursor = items_page.get("cursor")
            if not new_cursor or not page_items:
                break
            cursor = new_cursor
            
        return all_items
