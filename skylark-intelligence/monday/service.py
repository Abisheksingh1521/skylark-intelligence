import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from config.settings import settings
from monday.client import MondayClient, MondayConfigError, MondayAPIError, MondayConnectionError
from monday.schemas import DEALS_COLUMN_MAPPING, WORK_ORDERS_COLUMN_MAPPING

logger = logging.getLogger(__name__)

class MondayService:
    """
    High-level business service for loading board data from Monday.com.
    Parses raw GraphQL item responses into dicts with column titles/values.
    """

    def __init__(self, client: Optional[MondayClient] = None):
        self.client = client or MondayClient()
        self._deals_cache: Optional[Tuple[float, List[Dict[str, Any]]]] = None
        self._wo_cache: Optional[Tuple[float, List[Dict[str, Any]]]] = None

    @staticmethod
    def validate_connection() -> Tuple[bool, str]:
        """
        Validates API connectivity to Monday.com.
        Returns (is_connected, message).
        """
        try:
            if not settings.validate_monday_config():
                return False, "Monday.com API environment variables are not configured."
            
            client = MondayClient()
            # Test query by getting schema of Deals board
            client.get_board_columns(settings.MONDAY_DEALS_BOARD_ID)
            return True, "Connected to live Monday.com API."
        except MondayConfigError as e:
            return False, f"Configuration Error: {str(e)}"
        except MondayAPIError as e:
            return False, f"Monday API Error: {str(e)}"
        except MondayConnectionError as e:
            return False, f"Connection Error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected Error: {str(e)}"

    @staticmethod
    def parse_item_column_values(item: Dict[str, Any], column_title_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Parses a raw GraphQL item object into a dictionary mapping column titles to their text values.
        """
        record = {}
        record["Item Name"] = item.get("name", "")
        col_values = item.get("column_values", [])
        for col in col_values:
            col_id = col.get("id")
            val_text = col.get("text")
            val_raw = col.get("value")
            val = val_text if val_text is not None else val_raw
            record[col_id] = val
        return record

    def get_raw_deals_data(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches raw deals board items from Monday.com API.
        Uses in-memory cache with TTL.
        """
        now = time.time()
        if not force_refresh and self._deals_cache:
            cache_time, data = self._deals_cache
            if now - cache_time < settings.CACHE_TTL_SECONDS:
                return data

        if not settings.MONDAY_DEALS_BOARD_ID:
            raise MondayConfigError("MONDAY_DEALS_BOARD_ID is not configured.")

        # Fetch items from Monday.com
        raw_items = self.client.fetch_all_items(settings.MONDAY_DEALS_BOARD_ID)
        columns = self.client.get_board_columns(settings.MONDAY_DEALS_BOARD_ID)
        col_id_to_title = {c["id"]: c["title"] for c in columns}

        parsed_records = []
        for item in raw_items:
            rec = {"Deal Name": item.get("name", "")}
            for col_val in item.get("column_values", []):
                col_title = col_id_to_title.get(col_val["id"], col_val["id"])
                rec[col_title] = col_val.get("text")
            parsed_records.append(rec)

        self._deals_cache = (now, parsed_records)
        return parsed_records

    def get_raw_work_orders_data(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches raw work orders board items from Monday.com API.
        Uses in-memory cache with TTL.
        """
        now = time.time()
        if not force_refresh and self._wo_cache:
            cache_time, data = self._wo_cache
            if now - cache_time < settings.CACHE_TTL_SECONDS:
                return data

        if not settings.MONDAY_WORK_ORDERS_BOARD_ID:
            raise MondayConfigError("MONDAY_WORK_ORDERS_BOARD_ID is not configured.")

        raw_items = self.client.fetch_all_items(settings.MONDAY_WORK_ORDERS_BOARD_ID)
        columns = self.client.get_board_columns(settings.MONDAY_WORK_ORDERS_BOARD_ID)
        col_id_to_title = {c["id"]: c["title"] for c in columns}

        parsed_records = []
        for item in raw_items:
            rec = {"Deal name masked": item.get("name", "")}
            for col_val in item.get("column_values", []):
                col_title = col_id_to_title.get(col_val["id"], col_val["id"])
                rec[col_title] = col_val.get("text")
            parsed_records.append(rec)

        self._wo_cache = (now, parsed_records)
        return parsed_records
