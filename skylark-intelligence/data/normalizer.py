import pandas as pd
import numpy as np
import re
from dataclasses import dataclass
from typing import Optional, Any, Dict, List, Tuple
from data.mappings import CANONICAL_SECTORS, CLOSURE_PROBABILITY_MAP, DEAL_STATUS_MAP, EXECUTION_STATUS_MAP

@dataclass
class CanonicalDeal:
    deal_id: str
    deal_name: str
    owner_code: str
    client_code: str
    status: str                         # 'Won', 'Open', 'Dead', 'On Hold'
    stage: str
    closure_probability_label: Optional[str]  # 'High', 'Medium', 'Low', or None
    closure_probability_pct: Optional[float]  # 0.75, 0.50, 0.25, or None (NOT 0.0!)
    deal_value: Optional[float]          # Nullable float (NOT 0.0 when missing!)
    close_date: Optional[pd.Timestamp]
    tentative_close_date: Optional[pd.Timestamp]
    created_date: Optional[pd.Timestamp]
    product: Optional[str]
    sector: str
    raw_record: Dict[str, Any]           # Preserves raw data for provenance & auditability

@dataclass
class CanonicalWorkOrder:
    wo_id: str                          # Primary Key: 'Serial #' (e.g. 'SDPLDEAL-075')
    deal_name: str                      # Foreign identifier: 'Deal name masked'
    customer_code: str
    nature_of_work: str
    execution_status: str               # 'Completed', 'Ongoing', 'Not Started', 'Paused'
    sector: str
    owner_code: str
    po_date: Optional[pd.Timestamp]
    probable_start_date: Optional[pd.Timestamp]
    probable_end_date: Optional[pd.Timestamp]
    data_delivery_date: Optional[pd.Timestamp]
    last_invoice_date: Optional[pd.Timestamp]
    amount_excl_gst: Optional[float]
    amount_incl_gst: Optional[float]     # Contract Value
    billed_value_excl_gst: Optional[float]
    billed_value_incl_gst: Optional[float]
    collected_amount_incl_gst: Optional[float] # Cash collected (Nullable!)
    amount_to_be_billed_incl_gst: Optional[float]
    amount_receivable: Optional[float]   # Outstanding AR
    is_ar_priority: bool
    invoice_status: Optional[str]
    wo_status_billed: Optional[str]
    raw_record: Dict[str, Any]           # Preserves raw data for provenance & auditability


def normalize_text(val: Any) -> Optional[str]:
    """Clean whitespace and string representation. Returns None for empty/null."""
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    return s if s else None


def normalize_sector(val: Any) -> str:
    """Map raw sector strings to canonical sector names."""
    clean = normalize_text(val)
    if not clean:
        return "Others"
    key = clean.lower()
    return CANONICAL_SECTORS.get(key, clean.title())


def normalize_probability(val: Any) -> Tuple[Optional[str], Optional[float]]:
    """
    Normalizes closure probability label and percentage weight.
    CRITICAL: Preserves NULL as None (NOT 0.0) when missing/unrecorded.
    Returns (label, float_pct_or_None).
    """
    label = normalize_text(val)
    if not label:
        return None, None
    key = label.lower()
    pct = CLOSURE_PROBABILITY_MAP.get(key)
    if pct is not None:
        return label.title(), pct
    return label, None


def normalize_money(val: Any) -> Tuple[Optional[float], bool]:
    """
    Safely parses monetary values.
    Returns (float_val, is_valid).
    CRITICAL: Preserves NULL/missing as None (never converts missing to 0.0).
    Explicitly distinguishes actual 0.0 from missing/null.
    """
    if pd.isna(val) or val is None:
        return None, True
    
    if isinstance(val, (int, float, np.number)):
        if np.isnan(val):
            return None, True
        return float(val), True

    # String cleaning
    s = str(val).strip()
    if not s or s.lower() in ['nan', 'none', 'null', '-', '']:
        return None, True

    # Strip currency symbols, commas, spaces
    cleaned = re.sub(r'[₹$  ,]', '', s)
    try:
        parsed = float(cleaned)
        return parsed, True
    except ValueError:
        return None, False


def normalize_date(val: Any) -> Tuple[Optional[pd.Timestamp], bool]:
    """
    Safely parses dates into pd.Timestamp.
    Handles ISO strings, DD/MM/YYYY, Excel timestamps, None/NaN.
    Returns (pd_timestamp_or_None, is_valid).
    """
    if pd.isna(val) or val is None:
        return None, True
    
    if isinstance(val, pd.Timestamp):
        return val, True
    
    if hasattr(val, 'strftime'): # datetime.date or datetime.datetime
        return pd.Timestamp(val), True

    s = str(val).strip()
    if not s or s.lower() in ['nan', 'none', 'null', '-', 'nat']:
        return None, True

    # Handle string headers accidentally passed as dates
    if s.lower() in ['close date (a)', 'tentative close date', 'created date']:
        return None, False

    try:
        parsed = pd.to_datetime(s, errors='coerce')
        if pd.isna(parsed):
            return None, False
        return parsed, True
    except Exception:
        return None, False


class DealsNormalizer:
    """Normalizes raw Deals data into canonical Deal records and DataFrames."""

    @classmethod
    def normalize_record(cls, raw: Dict[str, Any], idx: int = 0) -> CanonicalDeal:
        deal_name = normalize_text(raw.get("Deal Name")) or f"Deal_{idx}"
        owner_code = normalize_text(raw.get("Owner code")) or "UNKNOWN_OWNER"
        client_code = normalize_text(raw.get("Client Code")) or "UNKNOWN_CLIENT"
        
        raw_status = normalize_text(raw.get("Deal Status")) or "Open"
        status = DEAL_STATUS_MAP.get(raw_status.lower(), raw_status)
        
        stage = normalize_text(raw.get("Deal Stage")) or "Unspecified Stage"
        
        prob_label, prob_pct = normalize_probability(raw.get("Closure Probability"))
        
        val, val_valid = normalize_money(raw.get("Masked Deal value"))
        
        close_dt, _ = normalize_date(raw.get("Close Date (A)"))
        tent_dt, _ = normalize_date(raw.get("Tentative Close Date"))
        created_dt, _ = normalize_date(raw.get("Created Date"))
        
        product = normalize_text(raw.get("Product deal"))
        sector = normalize_sector(raw.get("Sector/service"))

        return CanonicalDeal(
            deal_id=f"DEAL_{idx:04d}",
            deal_name=deal_name,
            owner_code=owner_code,
            client_code=client_code,
            status=status,
            stage=stage,
            closure_probability_label=prob_label,
            closure_probability_pct=prob_pct,
            deal_value=val,
            close_date=close_dt,
            tentative_close_date=tent_dt,
            created_date=created_dt,
            product=product,
            sector=sector,
            raw_record=raw
        )

    @classmethod
    def normalize_list(cls, raw_records: List[Dict[str, Any]]) -> List[CanonicalDeal]:
        clean_list = []
        for i, r in enumerate(raw_records):
            # Filter out re-declared header rows
            if str(r.get("Deal Name", "")).strip().lower() in ["deal name", "deal status"]:
                continue
            clean_list.append(cls.normalize_record(r, i + 1))
        return clean_list


class WorkOrdersNormalizer:
    """Normalizes raw Work Orders data into canonical Work Order records and DataFrames."""

    @classmethod
    def normalize_record(cls, raw: Dict[str, Any], idx: int = 0) -> CanonicalWorkOrder:
        serial_no = normalize_text(raw.get("Serial #")) or f"WO_SERIAL_{idx:04d}"
        deal_name = normalize_text(raw.get("Deal name masked")) or "UNLINKED_WO"
        customer_code = normalize_text(raw.get("Customer Name Code")) or "UNKNOWN_CUST"
        nature_of_work = normalize_text(raw.get("Nature of Work")) or "Unspecified"
        
        raw_exec = normalize_text(raw.get("Execution Status")) or "Ongoing"
        exec_status = EXECUTION_STATUS_MAP.get(raw_exec.lower(), raw_exec)
        
        sector = normalize_sector(raw.get("Sector"))
        owner_code = normalize_text(raw.get("BD/KAM Personnel code")) or "UNKNOWN_BD"
        
        po_dt, _ = normalize_date(raw.get("Date of PO/LOI"))
        start_dt, _ = normalize_date(raw.get("Probable Start Date"))
        end_dt, _ = normalize_date(raw.get("Probable End Date"))
        deliv_dt, _ = normalize_date(raw.get("Data Delivery Date"))
        inv_dt, _ = normalize_date(raw.get("Last invoice date"))

        amt_excl, _ = normalize_money(raw.get("Amount in Rupees (Excl of GST) (Masked)"))
        amt_incl, _ = normalize_money(raw.get("Amount in Rupees (Incl of GST) (Masked)"))
        billed_excl, _ = normalize_money(raw.get("Billed Value in Rupees (Excl of GST.) (Masked)"))
        billed_incl, _ = normalize_money(raw.get("Billed Value in Rupees (Incl of GST.) (Masked)"))
        collected_incl, _ = normalize_money(raw.get("Collected Amount in Rupees (Incl of GST.) (Masked)"))
        unbilled_incl, _ = normalize_money(raw.get("Amount to be billed in Rs. (Incl. of GST) (Masked)"))
        receivable, _ = normalize_money(raw.get("Amount Receivable (Masked)"))

        ar_prio_str = normalize_text(raw.get("AR Priority account"))
        is_priority = bool(ar_prio_str and ar_prio_str.lower() == "priority")

        inv_status = normalize_text(raw.get("Invoice Status"))
        wo_status = normalize_text(raw.get("WO Status (billed)"))

        return CanonicalWorkOrder(
            wo_id=serial_no,
            deal_name=deal_name,
            customer_code=customer_code,
            nature_of_work=nature_of_work,
            execution_status=exec_status,
            sector=sector,
            owner_code=owner_code,
            po_date=po_dt,
            probable_start_date=start_dt,
            probable_end_date=end_dt,
            data_delivery_date=deliv_dt,
            last_invoice_date=inv_dt,
            amount_excl_gst=amt_excl,
            amount_incl_gst=amt_incl,
            billed_value_excl_gst=billed_excl,
            billed_value_incl_gst=billed_incl,
            collected_amount_incl_gst=collected_incl,
            amount_to_be_billed_incl_gst=unbilled_incl,
            amount_receivable=receivable,
            is_ar_priority=is_priority,
            invoice_status=inv_status,
            wo_status_billed=wo_status,
            raw_record=raw
        )

    @classmethod
    def normalize_list(cls, raw_records: List[Dict[str, Any]]) -> List[CanonicalWorkOrder]:
        clean_list = []
        for i, r in enumerate(raw_records):
            clean_list.append(cls.normalize_record(r, i + 1))
        return clean_list
