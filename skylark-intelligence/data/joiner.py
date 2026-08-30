from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from data.normalizer import CanonicalDeal, CanonicalWorkOrder

class JoinStatus:
    STRONG_MATCH = "Strong name match"
    AMBIGUOUS_MATCH = "Ambiguous match"
    UNMATCHED = "Unmatched"

@dataclass
class AggregatedWorkOrdersByDeal:
    deal_name: str
    norm_deal_name: str
    work_order_count: int
    total_amount_incl_gst: float
    total_billed_value_incl_gst: float
    total_collected_amount_incl_gst: Optional[float]
    total_amount_to_be_billed_incl_gst: float
    total_amount_receivable: float
    join_status: str
    matching_deal_count: int
    matching_deals: List[CanonicalDeal]
    work_orders: List[CanonicalWorkOrder]
    explanation: str

class CrossBoardJoiner:
    """
    Implements cross-board linking logic.
    - Aggregates Work Orders at the normalized deal_name level.
    - Classifies join confidence into 'Strong name match', 'Ambiguous match', or 'Unmatched'.
    - Never performs Cartesian row multiplication.
    """

    @classmethod
    def classify_and_aggregate(
        cls, deals: List[CanonicalDeal], work_orders: List[CanonicalWorkOrder]
    ) -> List[AggregatedWorkOrdersByDeal]:
        
        # Build index of Deals by normalized deal_name
        deals_by_norm_name: Dict[str, List[CanonicalDeal]] = {}
        for d in deals:
            norm_name = d.deal_name.strip().lower()
            if norm_name not in deals_by_norm_name:
                deals_by_norm_name[norm_name] = []
            deals_by_norm_name[norm_name].append(d)

        # Group Work Orders by normalized deal_name
        wo_groups: Dict[str, List[CanonicalWorkOrder]] = {}
        for w in work_orders:
            norm_name = w.deal_name.strip().lower()
            if norm_name not in wo_groups:
                wo_groups[norm_name] = []
            wo_groups[norm_name].append(w)

        aggregated_results = []

        for norm_name, wo_list in wo_groups.items():
            first_raw_name = wo_list[0].deal_name
            wo_count = len(wo_list)

            # Aggregate financial metrics over work orders in this group
            sum_amount = sum(w.amount_incl_gst or 0.0 for w in wo_list)
            sum_billed = sum(w.billed_value_incl_gst or 0.0 for w in wo_list)
            
            # Collected amount: sum over non-null entries
            collected_values = [w.collected_amount_incl_gst for w in wo_list if w.collected_amount_incl_gst is not None]
            sum_collected = sum(collected_values) if collected_values else None
            
            sum_unbilled = sum(w.amount_to_be_billed_incl_gst or 0.0 for w in wo_list)
            sum_receivable = sum(w.amount_receivable or 0.0 for w in wo_list)

            matching_deals = deals_by_norm_name.get(norm_name, [])
            matching_deal_count = len(matching_deals)

            # Classification logic
            if matching_deal_count == 0:
                join_status = JoinStatus.UNMATCHED
                explanation = f"No corresponding deal record found in Deals board for deal name '{first_raw_name}'."
            elif matching_deal_count == 1:
                join_status = JoinStatus.STRONG_MATCH
                explanation = f"Unique exact match found with single deal record in Deals board."
            else:
                join_status = JoinStatus.AMBIGUOUS_MATCH
                explanation = f"Ambiguous match: {matching_deal_count} duplicate deal records exist in Deals board sharing the deal name '{first_raw_name}'."

            aggregated_results.append(
                AggregatedWorkOrdersByDeal(
                    deal_name=first_raw_name,
                    norm_deal_name=norm_name,
                    work_order_count=wo_count,
                    total_amount_incl_gst=sum_amount,
                    total_billed_value_incl_gst=sum_billed,
                    total_collected_amount_incl_gst=sum_collected,
                    total_amount_to_be_billed_incl_gst=sum_unbilled,
                    total_amount_receivable=sum_receivable,
                    join_status=join_status,
                    matching_deal_count=matching_deal_count,
                    matching_deals=matching_deals,
                    work_orders=wo_list,
                    explanation=explanation
                )
            )

        return aggregated_results
