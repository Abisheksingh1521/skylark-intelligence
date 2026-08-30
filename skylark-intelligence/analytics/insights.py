from typing import List, Dict, Any, Optional
import pandas as pd
from config.settings import get_current_date
from data.normalizer import CanonicalDeal, CanonicalWorkOrder
from analytics.pipeline import PipelineAnalytics
from analytics.work_orders import WorkOrderAnalytics
from analytics.cross_board import CrossBoardAnalytics

class FounderInsightsEngine:
    """
    Rule-based Executive Insights Engine.
    Identifies strategic opportunities, operational bottlenecks, financial risks,
    and cross-board anomalies using strictly documented deterministic business rules.
    """

    @classmethod
    def get_top_opportunities(cls, deals: List[CanonicalDeal], top_n: int = 5) -> List[Dict[str, Any]]:
        open_with_val = [d for d in deals if d.status == "Open" and d.deal_value is not None]
        open_with_val.sort(key=lambda x: x.deal_value, reverse=True)

        return [
            {
                "deal_name": d.deal_name,
                "sector": d.sector,
                "owner_code": d.owner_code,
                "client_code": d.client_code,
                "deal_value": d.deal_value,
                "stage": d.stage,
                "closure_probability": d.closure_probability_label,
                "tentative_close_date": d.tentative_close_date.strftime("%Y-%m-%d") if d.tentative_close_date else "Unspecified"
            }
            for d in open_with_val[:top_n]
        ]

    @classmethod
    def get_high_receivable_risks(cls, work_orders: List[CanonicalWorkOrder], threshold: float = 1000000.0) -> List[Dict[str, Any]]:
        ar_risks = [w for w in work_orders if (w.amount_receivable or 0.0) >= threshold]
        ar_risks.sort(key=lambda x: x.amount_receivable or 0.0, reverse=True)

        return [
            {
                "wo_id": w.wo_id,
                "deal_name": w.deal_name,
                "customer_code": w.customer_code,
                "sector": w.sector,
                "amount_receivable": w.amount_receivable,
                "amount_incl_gst": w.amount_incl_gst,
                "billed_value_incl_gst": w.billed_value_incl_gst,
                "is_ar_priority": w.is_ar_priority,
                "execution_status": w.execution_status
            }
            for w in ar_risks
        ]

    @classmethod
    def get_sector_execution_anomalies(
        cls, deals: List[CanonicalDeal], work_orders: List[CanonicalWorkOrder], reference_date: Optional[pd.Timestamp] = None
    ) -> List[Dict[str, Any]]:
        """
        Rule: Sector Anomaly occurs when a Sector has Open Pipeline > ₹1 Crore
        BUT has >20% overdue work orders OR > ₹50 Lakhs in outstanding receivables.
        """
        ref_dt = reference_date or get_current_date()
        sector_comp = CrossBoardAnalytics.get_sector_cross_board_comparison(deals, work_orders)
        
        wo_by_sec: Dict[str, List[CanonicalWorkOrder]] = {}
        for w in work_orders:
            wo_by_sec.setdefault(w.sector, []).append(w)

        anomalies = []

        for sec_data in sector_comp:
            sec = sec_data["sector"]
            pipeline_val = sec_data["open_pipeline_value"]
            sec_wos = wo_by_sec.get(sec, [])

            if pipeline_val >= 10000000.0 and len(sec_wos) > 0:
                overdue_cnt = sum(
                    1 for w in sec_wos 
                    if w.probable_end_date is not None and w.probable_end_date < ref_dt and w.execution_status != "Completed"
                )
                overdue_pct = round(overdue_cnt / len(sec_wos) * 100, 2)
                receivable_val = sec_data["work_order_receivables"]

                if overdue_pct > 20.0 or receivable_val >= 5000000.0:
                    anomalies.append({
                        "sector": sec,
                        "open_pipeline_value": pipeline_val,
                        "work_orders_count": len(sec_wos),
                        "overdue_work_orders_count": overdue_cnt,
                        "overdue_percentage": overdue_pct,
                        "work_order_receivables": receivable_val,
                        "anomaly_description": f"Sector '{sec}' has strong sales pipeline (₹{pipeline_val:,.2f}) but suffers from operational friction ({overdue_pct}% overdue work orders, ₹{receivable_val:,.2f} in outstanding AR)."
                    })

        return anomalies

    @classmethod
    def get_deals_missing_critical_info(cls, deals: List[CanonicalDeal]) -> Dict[str, Any]:
        open_deals = [d for d in deals if d.status == "Open"]
        
        missing_val = [d for d in open_deals if d.deal_value is None]
        missing_prob = [d for d in open_deals if d.closure_probability_pct is None]
        missing_date = [d for d in open_deals if d.tentative_close_date is None]

        return {
            "total_open_deals": len(open_deals),
            "missing_value_count": len(missing_val),
            "missing_probability_count": len(missing_prob),
            "missing_tentative_date_count": len(missing_date),
            "sample_missing_value_deals": [d.deal_name for d in missing_val[:5]],
            "sample_missing_prob_deals": [d.deal_name for d in missing_prob[:5]]
        }
