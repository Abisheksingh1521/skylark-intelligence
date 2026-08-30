import pytest
import pandas as pd
import numpy as np
from data.normalizer import (
    normalize_date,
    normalize_money,
    normalize_probability,
    normalize_text,
    normalize_sector,
    DealsNormalizer,
    WorkOrdersNormalizer
)
from data.quality import DataQualityEngine
from data.joiner import CrossBoardJoiner, JoinStatus

def test_missing_values_preserved_as_null():
    """Requirement 1 & 2: Missing values must remain None/NULL, never converted to 0.0."""
    val_none, valid1 = normalize_money(None)
    assert val_none is None
    assert valid1 is True

    val_nan, valid2 = normalize_money(np.nan)
    assert val_nan is None
    assert valid2 is True

    val_str_null, valid3 = normalize_money("nan")
    assert val_str_null is None
    assert valid3 is True

def test_zero_vs_null_distinction():
    """Requirement 2: Zero (0.0) is a valid numeric value, distinct from None/NULL."""
    zero_val, valid_zero = normalize_money(0)
    assert zero_val == 0.0
    assert valid_zero is True

    zero_str, valid_zero_str = normalize_money("₹ 0.00")
    assert zero_str == 0.0
    assert valid_zero_str is True

    assert zero_val is not None
    assert zero_val != val_none_test()

def val_none_test():
    val, _ = normalize_money(None)
    return val

def test_missing_probability_preserved():
    """Requirement 3: Missing closure probability maps to None, NOT 0.0."""
    label_high, pct_high = normalize_probability("High")
    assert label_high == "High"
    assert pct_high == 0.75

    label_med, pct_med = normalize_probability("Medium")
    assert pct_med == 0.50

    label_low, pct_low = normalize_probability("Low")
    assert pct_low == 0.25

    label_null, pct_null = normalize_probability(None)
    assert label_null is None
    assert pct_null is None  # MUST BE None, NOT 0.0!

    label_nan, pct_nan = normalize_probability(np.nan)
    assert pct_nan is None

def test_date_normalization():
    """Requirement 4: Date parsing for valid dates, headers, and invalid values."""
    dt_iso, valid_iso = normalize_date("2026-02-26 00:00:00")
    assert valid_iso is True
    assert dt_iso == pd.Timestamp("2026-02-26")

    dt_hdr, valid_hdr = normalize_date("Close Date (A)")
    assert dt_hdr is None
    assert valid_hdr is False

    dt_none, valid_none = normalize_date(None)
    assert dt_none is None
    assert valid_none is True

def test_monetary_formatting_and_malformed_values():
    """Requirement 5: Currency symbol stripping & malformed string handling."""
    val_inr, v1 = normalize_money("₹ 1,25,00,000.50")
    assert v1 is True
    assert val_inr == 12500000.50

    val_neg, v2 = normalize_money("-82907.30")
    assert v2 is True
    assert val_neg == -82907.30

    val_mal, v_mal = normalize_money("INVALID_PRICE")
    assert val_mal is None
    assert v_mal is False

def test_duplicate_and_pk_preservation():
    """Requirement 8 & 9: Serial # is preserved as Work Order PK."""
    raw_wo_1 = {
        "Serial #": "SDPLDEAL-001",
        "Deal name masked": "Sasuke",
        "Customer Name Code": "WOCOMPANY_001",
        "Amount in Rupees (Incl of GST) (Masked)": "100000"
    }
    raw_wo_2 = {
        "Serial #": "SDPLDEAL-002",
        "Deal name masked": "Sasuke",
        "Customer Name Code": "WOCOMPANY_001",
        "Amount in Rupees (Incl of GST) (Masked)": "200000"
    }

    wo1 = WorkOrdersNormalizer.normalize_record(raw_wo_1, 1)
    wo2 = WorkOrdersNormalizer.normalize_record(raw_wo_2, 2)

    assert wo1.wo_id == "SDPLDEAL-001"
    assert wo2.wo_id == "SDPLDEAL-002"
    assert wo1.deal_name == wo2.deal_name == "Sasuke"

def test_cross_board_join_safety_aggregation():
    """Requirement 10 & 11: Prevent Cartesian multiplication by grouping Work Orders before joining."""
    deals = [
        DealsNormalizer.normalize_record({"Deal Name": "Naruto", "Masked Deal value": 500000, "Deal Status": "Open"}, 1),
        DealsNormalizer.normalize_record({"Deal Name": "Naruto", "Masked Deal value": 300000, "Deal Status": "Open"}, 2),
    ]

    work_orders = [
        WorkOrdersNormalizer.normalize_record({"Serial #": "WO-01", "Deal name masked": "Naruto", "Amount in Rupees (Incl of GST) (Masked)": 100000}, 1),
        WorkOrdersNormalizer.normalize_record({"Serial #": "WO-02", "Deal name masked": "Naruto", "Amount in Rupees (Incl of GST) (Masked)": 150000}, 2),
    ]

    aggregated = CrossBoardJoiner.classify_and_aggregate(deals, work_orders)
    assert len(aggregated) == 1
    agg = aggregated[0]

    assert agg.deal_name == "Naruto"
    assert agg.work_order_count == 2
    assert agg.total_amount_incl_gst == 250000.0

def test_join_classification_unique_name_match():
    """Correction test 1: Unique deal name match classifies as 'Strong name match'."""
    deals = [
        DealsNormalizer.normalize_record({"Deal Name": "Unique_Deal_A", "Masked Deal value": 500000}, 1),
    ]
    wos = [
        WorkOrdersNormalizer.normalize_record({"Serial #": "WO-100", "Deal name masked": "Unique_Deal_A", "Amount in Rupees (Incl of GST) (Masked)": 200000}, 1),
    ]

    res = CrossBoardJoiner.classify_and_aggregate(deals, wos)
    assert len(res) == 1
    assert res[0].join_status == JoinStatus.STRONG_MATCH
    assert res[0].matching_deal_count == 1

def test_join_classification_duplicate_name_match():
    """Correction test 2 & 4: Multiple deals with same name classify as 'Ambiguous match'."""
    deals = [
        DealsNormalizer.normalize_record({"Deal Name": "Sasuke", "Masked Deal value": 500000}, 1),
        DealsNormalizer.normalize_record({"Deal Name": "Sasuke", "Masked Deal value": 300000}, 2),
    ]
    wos = [
        WorkOrdersNormalizer.normalize_record({"Serial #": "WO-101", "Deal name masked": "Sasuke", "Amount in Rupees (Incl of GST) (Masked)": 200000}, 1),
    ]

    res = CrossBoardJoiner.classify_and_aggregate(deals, wos)
    assert len(res) == 1
    assert res[0].join_status == JoinStatus.AMBIGUOUS_MATCH
    assert res[0].matching_deal_count == 2

def test_join_classification_unmatched_name():
    """Correction test 3: Work Order with no matching deal classifies as 'Unmatched'."""
    deals = [
        DealsNormalizer.normalize_record({"Deal Name": "Existing_Deal", "Masked Deal value": 500000}, 1),
    ]
    wos = [
        WorkOrdersNormalizer.normalize_record({"Serial #": "WO-999", "Deal name masked": "Orphan_Deal", "Amount in Rupees (Incl of GST) (Masked)": 150000}, 1),
    ]

    res = CrossBoardJoiner.classify_and_aggregate(deals, wos)
    assert len(res) == 1
    assert res[0].join_status == JoinStatus.UNMATCHED
    assert res[0].matching_deal_count == 0

def test_data_quality_engine():
    """Requirement 14: Data quality engine diagnostics & caveats."""
    deals = [
        DealsNormalizer.normalize_record({"Deal Name": "D1", "Masked Deal value": None, "Closure Probability": None}, 1),
        DealsNormalizer.normalize_record({"Deal Name": "D2", "Masked Deal value": 100000, "Closure Probability": "High"}, 2),
    ]
    audit = DataQualityEngine.audit_deals(deals)
    assert audit["missing_value_count"] == 1
    assert audit["missing_prob_count"] == 1
    assert len(audit["caveats"]) >= 1
