from typing import List, Dict, Any
from data.normalizer import CanonicalDeal, CanonicalWorkOrder
from data.joiner import CrossBoardJoiner, JoinStatus, AggregatedWorkOrdersByDeal

class CrossBoardAnalytics:
    """
    Deterministic cross-board analytics engine combining Deals and Work Orders.
    Uses Phase 3 pre-aggregation strategy (Work Orders grouped by normalized deal_name)
    and strictly enforces join status classifications:
    - 'Strong name match'
    - 'Ambiguous match'
    - 'Unmatched'
    """

    @classmethod
    def calculate_summary(cls, deals: List[CanonicalDeal], work_orders: List[CanonicalWorkOrder]) -> Dict[str, Any]:
        # Pre-aggregate Work Orders by deal_name
        agg_wo_list = CrossBoardJoiner.classify_and_aggregate(deals, work_orders)
        
        strong_matches = [a for a in agg_wo_list if a.join_status == JoinStatus.STRONG_MATCH]
        ambiguous_matches = [a for a in agg_wo_list if a.join_status == JoinStatus.AMBIGUOUS_MATCH]
        unmatched_wos = [a for a in agg_wo_list if a.join_status == JoinStatus.UNMATCHED]

        # Financial totals across classifications
        strong_contract_val = sum(a.total_amount_incl_gst for a in strong_matches)
        ambiguous_contract_val = sum(a.total_amount_incl_gst for a in ambiguous_matches)
        unmatched_contract_val = sum(a.total_amount_incl_gst for a in unmatched_wos)

        strong_ar_val = sum(a.total_amount_receivable for a in strong_matches)
        ambiguous_ar_val = sum(a.total_amount_receivable for a in ambiguous_matches)
        unmatched_ar_val = sum(a.total_amount_receivable for a in unmatched_wos)

        caveat_msg = (
            f"Cross-Board Match Classification: Out of {len(agg_wo_list)} distinct Work Order deal names, "
            f"{len(strong_matches)} are Strong name matches (₹{strong_contract_val:,.2f} contract value), "
            f"{len(ambiguous_matches)} are Ambiguous matches ({sum(a.matching_deal_count for a in ambiguous_matches)} duplicate deal opportunities), "
            f"and {len(unmatched_wos)} are Unmatched work orders (₹{unmatched_contract_val:,.2f} contract value)."
        )

        return {
            "total_distinct_wo_deal_names": len(agg_wo_list),
            "strong_matches_count": len(strong_matches),
            "strong_matches_contract_value": strong_contract_val,
            "strong_matches_ar_value": strong_ar_val,
            "ambiguous_matches_count": len(ambiguous_matches),
            "ambiguous_matches_contract_value": ambiguous_contract_val,
            "ambiguous_matches_ar_value": ambiguous_ar_val,
            "unmatched_work_orders_count": len(unmatched_wos),
            "unmatched_contract_value": unmatched_contract_val,
            "unmatched_ar_value": unmatched_ar_val,
            "data_quality_caveat": caveat_msg
        }

    @classmethod
    def get_sector_cross_board_comparison(cls, deals: List[CanonicalDeal], work_orders: List[CanonicalWorkOrder]) -> List[Dict[str, Any]]:
        """
        Compare Sales Pipeline vs Work Order contracted value & AR broken down by Sector.
        Aggregates Work Orders by Sector independently from Deals by Sector to prevent join distortion.
        """
        open_deals = [d for d in deals if d.status == "Open"]
        
        deals_by_sector: Dict[str, List[CanonicalDeal]] = {}
        for d in open_deals:
            sec = d.sector
            deals_by_sector.setdefault(sec, []).append(d)

        wo_by_sector: Dict[str, List[CanonicalWorkOrder]] = {}
        for w in work_orders:
            sec = w.sector
            wo_by_sector.setdefault(sec, []).append(w)

        all_sectors = set(deals_by_sector.keys()).union(set(wo_by_sector.keys()))
        results = []

        for sec in all_sectors:
            sec_deals = deals_by_sector.get(sec, [])
            sec_wos = wo_by_sector.get(sec, [])

            open_pipeline_val = sum(d.deal_value for d in sec_deals if d.deal_value is not None)
            wo_contract_val = sum(w.amount_incl_gst or 0.0 for w in sec_wos)
            wo_billed_val = sum(w.billed_value_incl_gst or 0.0 for w in sec_wos)
            wo_ar_val = sum(w.amount_receivable or 0.0 for w in sec_wos)

            results.append({
                "sector": sec,
                "open_deals_count": len(sec_deals),
                "open_pipeline_value": open_pipeline_val,
                "work_orders_count": len(sec_wos),
                "work_order_contract_value": wo_contract_val,
                "work_order_billed_value": wo_billed_val,
                "work_order_receivables": wo_ar_val
            })

        results.sort(key=lambda x: x["open_pipeline_value"], reverse=True)
        return results
