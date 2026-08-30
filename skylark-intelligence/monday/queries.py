"""
Monday.com GraphQL Queries (Strictly Read-Only).
No mutation queries are defined or permitted.
"""

# Query to validate board connection and fetch board columns
GET_BOARD_COLUMNS_QUERY = """
query GetBoardColumns($board_id: [ID!]!) {
  boards(ids: $board_id) {
    id
    name
    description
    columns {
      id
      title
      type
    }
  }
}
"""

# Query to fetch paginated items from a board using items_page API (API version 2023-10+)
GET_BOARD_ITEMS_QUERY = """
query GetBoardItems($board_id: [ID!]!, $cursor: String, $limit: Int = 100) {
  boards(ids: $board_id) {
    id
    name
    items_page(limit: $limit, cursor: $cursor) {
      cursor
      items {
        id
        name
        column_values {
          id
          type
          text
          value
        }
      }
    }
  }
}
"""

def validate_query_is_readonly(query_str: str) -> bool:
    """Security check to ensure query does not contain mutation operations."""
    normalized = query_str.strip().lower()
    if "mutation" in normalized:
        return False
    return True
