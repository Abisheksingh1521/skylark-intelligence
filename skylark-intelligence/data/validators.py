"""
Data validation functions to check raw data structures before normalization.
"""
from typing import Dict, Any, List, Tuple

def validate_deals_raw_schema(raw_records: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Verify raw Deals dictionary list contains required fields."""
    errors = []
    if not raw_records:
        return False, ["Deals raw records list is empty."]
    
    sample = raw_records[0]
    required_cols = ["Deal Name", "Owner code", "Client Code", "Deal Status"]
    for col in required_cols:
        if col not in sample and "Item Name" not in sample:
            errors.append(f"Missing required column '{col}' in raw Deals items.")

    return len(errors) == 0, errors

def validate_work_orders_raw_schema(raw_records: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Verify raw Work Orders dictionary list contains required fields."""
    errors = []
    if not raw_records:
        return False, ["Work Orders raw records list is empty."]
    
    sample = raw_records[0]
    required_cols = ["Serial #", "Deal name masked", "Customer Name Code"]
    for col in required_cols:
        if col not in sample and "Item Name" not in sample:
            errors.append(f"Missing required column '{col}' in raw Work Orders items.")

    return len(errors) == 0, errors
