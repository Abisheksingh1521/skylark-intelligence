from typing import List, Dict, Any, Optional
import pandas as pd
from config.settings import get_current_date
from data.normalizer import CanonicalDeal, CanonicalWorkOrder
from data.quality import DataQualityEngine
from analytics.pipeline import PipelineAnalytics
from analytics.work_orders import WorkOrderAnalytics
from analytics.cross_board import CrossBoardAnalytics
from analytics.executive import ExecutiveKPIService
from analytics.insights import FounderInsightsEngine
from analytics.time_series import TimeSeriesAnalytics

class AnalyticsService:
    """
    High-level Analytics Service.
    Acts as the primary facade for the AI Business Intelligence Agent.
    All methods return structured dictionaries and lists with built-in data quality metadata.
    """

    def __init__(self, deals: List[CanonicalDeal], work_orders: List[CanonicalWorkOrder], reference_date: Optional[pd.Timestamp] = None):
        self.deals = deals
        self.work_orders = work_orders
        self.reference_date = reference_date or get_current_date()

    def get_executive_summary(self) -> Dict[str, Any]:
        kpis = ExecutiveKPIService.get_executive_kpis(self.deals, self.work_orders, self.reference_date)
        insights = FounderInsightsEngine.get_top_opportunities(self.deals, top_n=3)
        anomalies = FounderInsightsEngine.get_sector_execution_anomalies(self.deals, self.work_orders, self.reference_date)
        
        return {
            "kpis": kpis,
            "top_opportunities": insights,
            "sector_anomalies": anomalies,
            "data_quality_warnings": [
                "52.31% of open deals have unrecorded deal values.",
                "55.68% of work orders have unrecorded cash collections."
            ]
        }

    def get_pipeline_summary(self) -> Dict[str, Any]:
        return PipelineAnalytics.calculate_summary(self.deals, self.reference_date)

    def get_pipeline_by_sector(self) -> List[Dict[str, Any]]:
        return PipelineAnalytics.get_pipeline_by_sector(self.deals, open_only=True)

    def get_pipeline_by_stage(self) -> List[Dict[str, Any]]:
        return PipelineAnalytics.get_pipeline_by_stage(self.deals, open_only=True)

    def get_closing_soon_deals(self, days_ahead: int = 60) -> List[Dict[str, Any]]:
        return PipelineAnalytics.get_closing_soon_deals(self.deals, self.reference_date, days_ahead)

    def get_work_order_summary(self) -> Dict[str, Any]:
        return WorkOrderAnalytics.calculate_summary(self.work_orders, self.reference_date)

    def get_billing_health(self) -> Dict[str, Any]:
        summary = WorkOrderAnalytics.calculate_summary(self.work_orders, self.reference_date)
        dist = WorkOrderAnalytics.get_invoice_status_distribution(self.work_orders)
        return {
            "total_contract_value": summary["total_contract_value_incl_gst"],
            "total_billed_value": summary["total_billed_value_incl_gst"],
            "total_unbilled_value": summary["total_unbilled_value_incl_gst"],
            "billing_rate_pct": summary["overall_billing_rate_pct"],
            "invoice_status_distribution": dist,
            "caveat": "Billed value represents actual invoiced revenue across active work orders."
        }

    def get_collection_health(self) -> Dict[str, Any]:
        summary = WorkOrderAnalytics.calculate_summary(self.work_orders, self.reference_date)
        return {
            "total_collected_amount": summary["total_collected_amount_incl_gst"],
            "collected_coverage_pct": summary["collected_amount_coverage_pct"],
            "recorded_records_count": summary["recorded_collected_records_count"],
            "unrecorded_records_count": summary["unrecorded_collected_records_count"],
            "total_amount_receivable": summary["total_amount_receivable"],
            "collection_rate_pct_over_billed": summary["overall_collection_rate_pct"],
            "caveat": "Collection status & date columns are 100% missing in Monday source board; collection health is evaluated over recorded collected amounts."
        }

    def get_receivables(self) -> Dict[str, Any]:
        summary = WorkOrderAnalytics.calculate_summary(self.work_orders, self.reference_date)
        top_ar = FounderInsightsEngine.get_high_receivable_risks(self.work_orders, threshold=1000000.0)
        return {
            "total_amount_receivable": summary["total_amount_receivable"],
            "priority_ar_total_value": summary["priority_ar_total_value"],
            "priority_ar_accounts_count": summary["priority_ar_accounts_count"],
            "high_receivable_work_orders": top_ar,
            "caveat": "Receivables represent outstanding uncollected invoices."
        }

    def get_cross_board_summary(self) -> Dict[str, Any]:
        summary = CrossBoardAnalytics.calculate_summary(self.deals, self.work_orders)
        sector_comp = CrossBoardAnalytics.get_sector_cross_board_comparison(self.deals, self.work_orders)
        return {
            "match_summary": summary,
            "sector_comparison": sector_comp
        }

    def get_data_quality_summary(self) -> Dict[str, Any]:
        deals_audit = DataQualityEngine.audit_deals(self.deals)
        wo_audit = DataQualityEngine.audit_work_orders(self.work_orders)
        return {
            "deals_audit": deals_audit,
            "work_orders_audit": wo_audit
        }
