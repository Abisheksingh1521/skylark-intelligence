from typing import List, Dict, Any
from data.normalizer import CanonicalDeal, CanonicalWorkOrder

class DataQualityEngine:
    """
    Computes data quality metrics, missing value statistics, duplicate checks,
    and executive caveats for Deals and Work Orders.
    """

    @staticmethod
    def audit_deals(deals: List[CanonicalDeal]) -> Dict[str, Any]:
        total = len(deals)
        if total == 0:
            return {"total_records": 0, "caveats": ["No deals data available."]}

        missing_value_count = sum(1 for d in deals if d.deal_value is None)
        missing_prob_count = sum(1 for d in deals if d.closure_probability_pct is None)
        missing_tentative_date = sum(1 for d in deals if d.tentative_close_date is None)

        open_deals = [d for d in deals if d.status == "Open"]
        open_total = len(open_deals)
        open_with_val = [d for d in open_deals if d.deal_value is not None]
        open_with_val_and_prob = [d for d in open_deals if d.deal_value is not None and d.closure_probability_pct is not None]

        # Duplicate check on deal names
        name_counts = {}
        for d in deals:
            name_counts[d.deal_name] = name_counts.get(d.deal_name, 0) + 1
        duplicate_names = {k: v for k, v in name_counts.items() if v > 1}

        caveats = []
        if missing_value_count > 0:
            pct = (missing_value_count / total) * 100
            caveats.append(
                f"Data Quality Warning: {missing_value_count} out of {total} deals ({pct:.1f}%) have unrecorded deal values and were excluded from monetary aggregation."
            )
        
        if open_total > 0:
            caveats.append(
                f"Weighted Pipeline Coverage: Calculated across {len(open_with_val_and_prob)} of {open_total} open deals with recorded value and probability. {open_total - len(open_with_val_and_prob)} open deals have missing value or probability."
            )

        return {
            "total_records": total,
            "missing_value_count": missing_value_count,
            "missing_value_pct": round(missing_value_count / total * 100, 2),
            "missing_prob_count": missing_prob_count,
            "missing_prob_pct": round(missing_prob_count / total * 100, 2),
            "open_deals_total": open_total,
            "open_deals_with_value_and_prob": len(open_with_val_and_prob),
            "duplicate_deal_names_count": len(duplicate_names),
            "caveats": caveats
        }

    @staticmethod
    def audit_work_orders(work_orders: List[CanonicalWorkOrder]) -> Dict[str, Any]:
        total = len(work_orders)
        if total == 0:
            return {"total_records": 0, "caveats": ["No work orders data available."]}

        missing_collected = sum(1 for w in work_orders if w.collected_amount_incl_gst is None)
        missing_end_date = sum(1 for w in work_orders if w.probable_end_date is None)
        unbilled_count = sum(1 for w in work_orders if w.billed_value_incl_gst == 0.0)
        negative_ar_count = sum(1 for w in work_orders if w.amount_receivable is not None and w.amount_receivable < 0)

        # Primary Key (Serial #) uniqueness check
        serial_counts = {}
        for w in work_orders:
            serial_counts[w.wo_id] = serial_counts.get(w.wo_id, 0) + 1
        duplicate_serials = {k: v for k, v in serial_counts.items() if v > 1}

        caveats = []
        if missing_collected > 0:
            pct = (missing_collected / total) * 100
            caveats.append(
                f"Collection Caveat: {missing_collected} out of {total} work orders ({pct:.1f}%) have unrecorded cash collections."
            )
        
        caveats.append(
            "Collection Status Notice: Collection status & collection date columns are 100% empty in Monday source board; collection health is derived deterministically from cash collected vs billed value."
        )

        if len(duplicate_serials) > 0:
            caveats.append(
                f"Data Integrity Alert: Found {len(duplicate_serials)} duplicate Work Order Serial IDs."
            )

        return {
            "total_records": total,
            "missing_collected_count": missing_collected,
            "missing_collected_pct": round(missing_collected / total * 100, 2),
            "missing_end_date_count": missing_end_date,
            "unbilled_work_orders_count": unbilled_count,
            "negative_ar_count": negative_ar_count,
            "duplicate_serials_count": len(duplicate_serials),
            "caveats": caveats
        }
