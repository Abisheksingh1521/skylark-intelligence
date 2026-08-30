from typing import List, Dict, Any, Optional
import pandas as pd
from config.settings import get_current_date
from data.normalizer import CanonicalWorkOrder

class WorkOrderAnalytics:
    """
    Deterministic analytics engine for Work Orders operations & financials.
    Calculates total contract value, billed value, unbilled balance, cash collected,
    receivables, execution status, and health indicators.
    """

    @staticmethod
    def calculate_summary(work_orders: List[CanonicalWorkOrder], reference_date: Optional[pd.Timestamp] = None) -> Dict[str, Any]:
        ref_dt = reference_date or get_current_date()
        total_count = len(work_orders)
        if total_count == 0:
            return {
                "total_work_orders_count": 0,
                "total_contract_value_incl_gst": 0.0,
                "total_billed_value_incl_gst": 0.0,
                "total_unbilled_value_incl_gst": 0.0,
                "total_collected_amount_incl_gst": None,
                "recorded_collected_records_count": 0,
                "unrecorded_collected_records_count": 0,
                "collected_amount_coverage_pct": 0.0,
                "total_amount_receivable": 0.0,
                "overall_billing_rate_pct": 0.0,
                "overall_collection_rate_pct": None,
                "overdue_work_orders_count": 0,
                "priority_ar_accounts_count": 0,
                "priority_ar_total_value": 0.0,
                "data_quality_caveat": "No work orders data available."
            }

        total_contract_val = sum(w.amount_incl_gst or 0.0 for w in work_orders)
        total_billed_val = sum(w.billed_value_incl_gst or 0.0 for w in work_orders)
        total_unbilled_val = sum(w.amount_to_be_billed_incl_gst or 0.0 for w in work_orders)
        total_receivable_val = sum(w.amount_receivable or 0.0 for w in work_orders)

        recorded_collected = [w.collected_amount_incl_gst for w in work_orders if w.collected_amount_incl_gst is not None]
        total_collected_val = sum(recorded_collected) if recorded_collected else None
        collected_coverage_pct = round((len(recorded_collected) / total_count * 100), 2)

        overall_billing_rate_pct = round((total_billed_val / total_contract_val * 100), 2) if total_contract_val > 0 else 0.0

        overall_collection_rate_pct = (
            round((total_collected_val / total_billed_val * 100), 2)
            if (total_collected_val is not None and total_billed_val > 0)
            else None
        )

        overdue_wos = [
            w for w in work_orders
            if w.probable_end_date is not None 
            and w.probable_end_date < ref_dt 
            and w.execution_status != "Completed"
        ]
        overdue_count = len(overdue_wos)

        priority_ar_wos = [w for w in work_orders if w.is_ar_priority and (w.amount_receivable or 0.0) > 0]
        priority_ar_val = sum(w.amount_receivable or 0.0 for w in priority_ar_wos)

        collected_str = f"₹{total_collected_val:,.2f}" if total_collected_val is not None else "N/A"
        caveat_msg = (
            f"Total Contract Value: ₹{total_contract_val:,.2f} across {total_count} work orders. "
            f"Billed: ₹{total_billed_val:,.2f} ({overall_billing_rate_pct}% of total contract). "
            f"Cash Collected: {collected_str} ({collected_coverage_pct}% data coverage). "
            f"Outstanding Receivables: ₹{total_receivable_val:,.2f} (including ₹{priority_ar_val:,.2f} in high-priority AR accounts)."
        )

        return {
            "total_work_orders_count": total_count,
            "total_contract_value_incl_gst": total_contract_val,
            "total_billed_value_incl_gst": total_billed_val,
            "total_unbilled_value_incl_gst": total_unbilled_val,
            "total_collected_amount_incl_gst": total_collected_val,
            "recorded_collected_records_count": len(recorded_collected),
            "unrecorded_collected_records_count": total_count - len(recorded_collected),
            "collected_amount_coverage_pct": collected_coverage_pct,
            "total_amount_receivable": total_receivable_val,
            "overall_billing_rate_pct": overall_billing_rate_pct,
            "overall_collection_rate_pct": overall_collection_rate_pct,
            "overdue_work_orders_count": overdue_count,
            "priority_ar_accounts_count": len(priority_ar_wos),
            "priority_ar_total_value": priority_ar_val,
            "data_quality_caveat": caveat_msg
        }

    @staticmethod
    def get_execution_status_distribution(work_orders: List[CanonicalWorkOrder]) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for w in work_orders:
            st = w.execution_status
            counts[st] = counts.get(st, 0) + 1
        
        total = len(work_orders)
        results = [
            {
                "execution_status": st,
                "count": cnt,
                "percentage": round(cnt / total * 100, 2) if total > 0 else 0.0
            }
            for st, cnt in counts.items()
        ]
        results.sort(key=lambda x: x["count"], reverse=True)
        return results

    @staticmethod
    def get_invoice_status_distribution(work_orders: List[CanonicalWorkOrder]) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for w in work_orders:
            st = w.invoice_status or "Unspecified / Null"
            counts[st] = counts.get(st, 0) + 1

        total = len(work_orders)
        results = [
            {
                "invoice_status": st,
                "count": cnt,
                "percentage": round(cnt / total * 100, 2) if total > 0 else 0.0
            }
            for st, cnt in counts.items()
        ]
        results.sort(key=lambda x: x["count"], reverse=True)
        return results

    @staticmethod
    def get_overdue_work_orders(work_orders: List[CanonicalWorkOrder], reference_date: Optional[pd.Timestamp] = None) -> List[Dict[str, Any]]:
        ref_dt = reference_date or get_current_date()
        overdue_list = []
        for w in work_orders:
            if w.probable_end_date is not None and w.probable_end_date < ref_dt and w.execution_status != "Completed":
                days_overdue = (ref_dt - w.probable_end_date).days
                overdue_list.append({
                    "wo_id": w.wo_id,
                    "deal_name": w.deal_name,
                    "customer_code": w.customer_code,
                    "execution_status": w.execution_status,
                    "sector": w.sector,
                    "amount_incl_gst": w.amount_incl_gst,
                    "probable_end_date": w.probable_end_date.strftime("%Y-%m-%d"),
                    "days_overdue": days_overdue
                })

        overdue_list.sort(key=lambda x: x["days_overdue"], reverse=True)
        return overdue_list
