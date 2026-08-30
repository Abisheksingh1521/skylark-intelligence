from typing import List, Dict, Any, Optional
import pandas as pd
from data.normalizer import CanonicalDeal, CanonicalWorkOrder

class TimeSeriesAnalytics:
    """
    Deterministic time-based analytics engine.
    Calculates closing milestones, pipeline distribution by month, and
    work order expected completion schedules using explicit, timezone-safe date logic.
    """

    @staticmethod
    def get_deals_closing_next_30_days(
        deals: List[CanonicalDeal], reference_date: Optional[pd.Timestamp] = None
    ) -> List[Dict[str, Any]]:
        ref_dt = reference_date or pd.Timestamp("2026-08-30")
        target_end_dt = ref_dt + pd.Timedelta(days=30)

        results = []
        for d in deals:
            if d.status != "Open" or d.tentative_close_date is None:
                continue
            if ref_dt <= d.tentative_close_date <= target_end_dt:
                days_left = (d.tentative_close_date - ref_dt).days
                results.append({
                    "deal_name": d.deal_name,
                    "sector": d.sector,
                    "owner_code": d.owner_code,
                    "deal_value": d.deal_value,
                    "closure_probability": d.closure_probability_label,
                    "tentative_close_date": d.tentative_close_date.strftime("%Y-%m-%d"),
                    "days_remaining": days_left
                })

        results.sort(key=lambda x: x["days_remaining"])
        return results

    @staticmethod
    def get_pipeline_by_month(deals: List[CanonicalDeal], open_only: bool = True) -> List[Dict[str, Any]]:
        target_deals = [d for d in deals if d.status == "Open"] if open_only else deals

        month_groups: Dict[str, List[CanonicalDeal]] = {}
        for d in target_deals:
            if d.tentative_close_date is not None:
                m_str = d.tentative_close_date.strftime("%Y-%m")
            else:
                m_str = "Unscheduled / Null"
            month_groups.setdefault(m_str, []).append(d)

        results = []
        for m_str, m_deals in month_groups.items():
            total_val = sum(d.deal_value for d in m_deals if d.deal_value is not None)
            results.append({
                "month": m_str,
                "deal_count": len(m_deals),
                "total_open_value": total_val
            })

        # Sort chronologically (with Unscheduled at end)
        results.sort(key=lambda x: (x["month"] == "Unscheduled / Null", x["month"]))
        return results

    @staticmethod
    def get_work_orders_by_expected_end_month(work_orders: List[CanonicalWorkOrder]) -> List[Dict[str, Any]]:
        month_groups: Dict[str, List[CanonicalWorkOrder]] = {}
        for w in work_orders:
            if w.probable_end_date is not None:
                m_str = w.probable_end_date.strftime("%Y-%m")
            else:
                m_str = "Unscheduled / Null"
            month_groups.setdefault(m_str, []).append(w)

        results = []
        for m_str, w_list in month_groups.items():
            tot_contract = sum(w.amount_incl_gst or 0.0 for w in w_list)
            results.append({
                "month": m_str,
                "work_order_count": len(w_list),
                "total_contract_value": tot_contract
            })

        results.sort(key=lambda x: (x["month"] == "Unscheduled / Null", x["month"]))
        return results
