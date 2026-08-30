from typing import List, Dict, Any, Optional
import pandas as pd
from config.settings import get_current_date
from data.normalizer import CanonicalDeal

class PipelineAnalytics:
    """
    Deterministic analytics engine for Sales Pipeline metrics.
    Calculates Open Pipeline, Weighted Pipeline, Sector/Stage breakdowns,
    Closing Soon opportunities, and Data Coverage statistics.
    """

    @staticmethod
    def calculate_summary(deals: List[CanonicalDeal], reference_date: Optional[pd.Timestamp] = None) -> Dict[str, Any]:
        ref_dt = reference_date or get_current_date()
        total_deals = len(deals)
        
        open_deals = [d for d in deals if d.status == "Open"]
        open_count = len(open_deals)
        
        won_deals = [d for d in deals if d.status == "Won"]
        won_count = len(won_deals)
        
        dead_deals = [d for d in deals if d.status == "Dead"]
        dead_count = len(dead_deals)

        open_with_val = [d for d in open_deals if d.deal_value is not None]
        open_pipeline_val = sum(d.deal_value for d in open_with_val)
        val_coverage_pct = round((len(open_with_val) / open_count * 100), 2) if open_count > 0 else 0.0

        eligible_weighted_deals = [
            d for d in open_deals 
            if d.deal_value is not None and d.closure_probability_pct is not None
        ]
        weighted_pipeline_val = sum(d.deal_value * d.closure_probability_pct for d in eligible_weighted_deals)
        prob_coverage_pct = round((len(eligible_weighted_deals) / open_count * 100), 2) if open_count > 0 else 0.0

        avg_open_deal_val = (open_pipeline_val / len(open_with_val)) if open_with_val else None

        missing_val_cnt = open_count - len(open_with_val)
        missing_prob_cnt = open_count - len(eligible_weighted_deals)
        
        caveat_msg = (
            f"Open Pipeline of ₹{open_pipeline_val:,.2f} calculated across {len(open_with_val)}/{open_count} open deals with known deal values. "
            f"Weighted Pipeline of ₹{weighted_pipeline_val:,.2f} calculated across {len(eligible_weighted_deals)}/{open_count} deals with known deal value and probability ({prob_coverage_pct}% coverage). "
            f"{missing_prob_cnt} open deals lack recorded probability."
        )

        return {
            "total_deals_count": total_deals,
            "open_deals_count": open_count,
            "won_deals_count": won_count,
            "dead_deals_count": dead_count,
            "open_pipeline_value": open_pipeline_val,
            "open_deals_with_value_count": len(open_with_val),
            "open_deals_missing_value_count": missing_val_cnt,
            "open_pipeline_value_coverage_pct": val_coverage_pct,
            "weighted_pipeline_value": weighted_pipeline_val,
            "eligible_weighted_deals_count": len(eligible_weighted_deals),
            "open_deals_missing_probability_count": missing_prob_cnt,
            "weighted_pipeline_coverage_pct": prob_coverage_pct,
            "avg_open_deal_value": avg_open_deal_val,
            "data_quality_caveat": caveat_msg
        }

    @staticmethod
    def get_pipeline_by_sector(deals: List[CanonicalDeal], open_only: bool = True) -> List[Dict[str, Any]]:
        target_deals = [d for d in deals if d.status == "Open"] if open_only else deals
        
        sector_groups: Dict[str, List[CanonicalDeal]] = {}
        for d in target_deals:
            sec = d.sector
            if sec not in sector_groups:
                sector_groups[sec] = []
            sector_groups[sec].append(d)

        results = []
        for sec, sec_deals in sector_groups.items():
            count = len(sec_deals)
            deals_with_val = [d for d in sec_deals if d.deal_value is not None]
            total_val = sum(d.deal_value for d in deals_with_val)
            
            eligible_weighted = [
                d for d in sec_deals 
                if d.deal_value is not None and d.closure_probability_pct is not None
            ]
            weighted_val = sum(d.deal_value * d.closure_probability_pct for d in eligible_weighted)

            results.append({
                "sector": sec,
                "deal_count": count,
                "total_open_value": total_val,
                "deals_with_value_count": len(deals_with_val),
                "weighted_open_value": weighted_val,
                "eligible_weighted_count": len(eligible_weighted)
            })

        results.sort(key=lambda x: x["total_open_value"], reverse=True)
        return results

    @staticmethod
    def get_pipeline_by_stage(deals: List[CanonicalDeal], open_only: bool = True) -> List[Dict[str, Any]]:
        target_deals = [d for d in deals if d.status == "Open"] if open_only else deals
        
        stage_groups: Dict[str, List[CanonicalDeal]] = {}
        for d in target_deals:
            stg = d.stage
            if stg not in stage_groups:
                stage_groups[stg] = []
            stage_groups[stg].append(d)

        results = []
        for stg, stg_deals in stage_groups.items():
            count = len(stg_deals)
            deals_with_val = [d for d in stg_deals if d.deal_value is not None]
            total_val = sum(d.deal_value for d in deals_with_val)

            results.append({
                "stage": stg,
                "deal_count": count,
                "total_value": total_val,
                "deals_with_value_count": len(deals_with_val)
            })

        results.sort(key=lambda x: x["total_value"], reverse=True)
        return results

    @staticmethod
    def get_closing_soon_deals(
        deals: List[CanonicalDeal], 
        reference_date: Optional[pd.Timestamp] = None, 
        days_ahead: int = 60
    ) -> List[Dict[str, Any]]:
        ref_dt = reference_date or get_current_date()
        target_end_dt = ref_dt + pd.Timedelta(days=days_ahead)

        closing_soon = []
        for d in deals:
            if d.status != "Open":
                continue
            if d.tentative_close_date is not None:
                if ref_dt <= d.tentative_close_date <= target_end_dt or d.tentative_close_date < ref_dt:
                    days_diff = (d.tentative_close_date - ref_dt).days
                    closing_soon.append({
                        "deal_name": d.deal_name,
                        "owner_code": d.owner_code,
                        "client_code": d.client_code,
                        "sector": d.sector,
                        "deal_value": d.deal_value,
                        "tentative_close_date": d.tentative_close_date.strftime("%Y-%m-%d"),
                        "days_until_close": days_diff,
                        "is_overdue_close": days_diff < 0,
                        "closure_probability": d.closure_probability_label
                    })

        closing_soon.sort(key=lambda x: x["days_until_close"])
        return closing_soon
