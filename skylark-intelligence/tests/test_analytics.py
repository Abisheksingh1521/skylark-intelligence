import pytest
import pandas as pd
import numpy as np
from data.normalizer import DealsNormalizer, WorkOrdersNormalizer
from analytics.pipeline import PipelineAnalytics
from analytics.work_orders import WorkOrderAnalytics
from analytics.cross_board import CrossBoardAnalytics
from analytics.executive import ExecutiveKPIService
from analytics.insights import FounderInsightsEngine
from analytics.time_series import TimeSeriesAnalytics
from analytics.service import AnalyticsService

def test_pipeline_open_and_weighted_calculations():
    """Verify open pipeline sum, weighted pipeline calculation, and NULL probability exclusion."""
    raw_deals = [
        {"Deal Name": "D1", "Deal Status": "Open", "Masked Deal value": 100000, "Closure Probability": "High", "Sector/service": "Mining"},
        {"Deal Name": "D2", "Deal Status": "Open", "Masked Deal value": 200000, "Closure Probability": "Medium", "Sector/service": "Renewables"},
        {"Deal Name": "D3", "Deal Status": "Open", "Masked Deal value": 300000, "Closure Probability": None, "Sector/service": "Mining"},
        {"Deal Name": "D4", "Deal Status": "Open", "Masked Deal value": None, "Closure Probability": None, "Sector/service": "Powerline"},
        {"Deal Name": "D5", "Deal Status": "Won", "Masked Deal value": 500000, "Closure Probability": "High", "Sector/service": "Mining"},
    ]
    deals = DealsNormalizer.normalize_list(raw_deals)
    summary = PipelineAnalytics.calculate_summary(deals, reference_date=pd.Timestamp("2026-08-30"))

    assert summary["open_deals_count"] == 4
    assert summary["won_deals_count"] == 1
    assert summary["open_pipeline_value"] == 600000.0
    assert summary["open_deals_with_value_count"] == 3
    assert summary["open_deals_missing_value_count"] == 1
    
    assert summary["weighted_pipeline_value"] == 175000.0
    assert summary["eligible_weighted_deals_count"] == 2
    assert summary["open_deals_missing_probability_count"] == 2
    assert summary["weighted_pipeline_coverage_pct"] == 50.0

def test_pipeline_sector_and_stage_breakdowns():
    """Verify sector and stage aggregation."""
    raw_deals = [
        {"Deal Name": "D1", "Deal Status": "Open", "Masked Deal value": 100000, "Closure Probability": "High", "Sector/service": "Mining", "Deal Stage": "A. Lead Generated"},
        {"Deal Name": "D2", "Deal Status": "Open", "Masked Deal value": 200000, "Closure Probability": "Low", "Sector/service": "Mining", "Deal Stage": "A. Lead Generated"},
        {"Deal Name": "D3", "Deal Status": "Open", "Masked Deal value": 400000, "Closure Probability": "Medium", "Sector/service": "Renewables", "Deal Stage": "B. Sales Qualified Leads"},
    ]
    deals = DealsNormalizer.normalize_list(raw_deals)
    
    by_sec = PipelineAnalytics.get_pipeline_by_sector(deals)
    assert len(by_sec) == 2
    assert by_sec[0]["sector"] == "Renewables"
    assert by_sec[0]["total_open_value"] == 400000.0
    assert by_sec[1]["sector"] == "Mining"
    assert by_sec[1]["total_open_value"] == 300000.0

    by_stg = PipelineAnalytics.get_pipeline_by_stage(deals)
    assert len(by_stg) == 2
    assert by_stg[0]["stage"] == "B. Sales Qualified Leads"
    assert by_stg[0]["total_value"] == 400000.0

def test_work_orders_financial_totals_and_health():
    """Verify work orders contract value, billed value, unbilled, cash collected, and receivables."""
    raw_wos = [
        {
            "Serial #": "WO-01", "Deal name masked": "Deal_A", "Sector": "Mining", "Execution Status": "Completed",
            "Amount in Rupees (Incl of GST) (Masked)": 500000,
            "Billed Value in Rupees (Incl of GST.) (Masked)": 500000,
            "Collected Amount in Rupees (Incl of GST.) (Masked)": 400000,
            "Amount to be billed in Rs. (Incl. of GST) (Masked)": 0,
            "Amount Receivable (Masked)": 100000,
            "AR Priority account": "Priority",
            "Probable End Date": "2025-12-31"
        },
        {
            "Serial #": "WO-02", "Deal name masked": "Deal_B", "Sector": "Renewables", "Execution Status": "Ongoing",
            "Amount in Rupees (Incl of GST) (Masked)": 300000,
            "Billed Value in Rupees (Incl of GST.) (Masked)": 100000,
            "Collected Amount in Rupees (Incl of GST.) (Masked)": None,
            "Amount to be billed in Rs. (Incl. of GST) (Masked)": 200000,
            "Amount Receivable (Masked)": 100000,
            "AR Priority account": None,
            "Probable End Date": "2025-05-01"
        }
    ]
    wos = WorkOrdersNormalizer.normalize_list(raw_wos)
    summary = WorkOrderAnalytics.calculate_summary(wos, reference_date=pd.Timestamp("2026-08-30"))

    assert summary["total_work_orders_count"] == 2
    assert summary["total_contract_value_incl_gst"] == 800000.0
    assert summary["total_billed_value_incl_gst"] == 600000.0
    assert summary["total_unbilled_value_incl_gst"] == 200000.0
    assert summary["total_collected_amount_incl_gst"] == 400000.0
    assert summary["recorded_collected_records_count"] == 1
    assert summary["unrecorded_collected_records_count"] == 1
    assert summary["total_amount_receivable"] == 200000.0
    assert summary["overdue_work_orders_count"] == 1
    assert summary["priority_ar_accounts_count"] == 1
    assert summary["priority_ar_total_value"] == 100000.0

def test_dynamic_reference_date_injection():
    """Verify overdue calculation accepts dynamic reference_date and defaults to system current date when None."""
    raw_wos = [
        {
            "Serial #": "WO-01", "Deal name masked": "Deal_A", "Execution Status": "Ongoing",
            "Probable End Date": "2025-01-01"
        }
    ]
    wos = WorkOrdersNormalizer.normalize_list(raw_wos)

    # Injected reference date in 2024 (WO is NOT overdue yet)
    sum_2024 = WorkOrderAnalytics.calculate_summary(wos, reference_date=pd.Timestamp("2024-01-01"))
    assert sum_2024["overdue_work_orders_count"] == 0

    # Injected reference date in 2026 (WO IS overdue)
    sum_2026 = WorkOrderAnalytics.calculate_summary(wos, reference_date=pd.Timestamp("2026-08-30"))
    assert sum_2026["overdue_work_orders_count"] == 1

    # Default (None -> current system date) should execute without error
    sum_default = WorkOrderAnalytics.calculate_summary(wos, reference_date=None)
    assert "overdue_work_orders_count" in sum_default

def test_executive_kpi_service():
    """Verify Executive KPIService output format and structure."""
    raw_deals = [{"Deal Name": "D1", "Deal Status": "Open", "Masked Deal value": 100000, "Closure Probability": "High"}]
    raw_wos = [{"Serial #": "WO-01", "Deal name masked": "D1", "Amount in Rupees (Incl of GST) (Masked)": 50000}]
    
    deals = DealsNormalizer.normalize_list(raw_deals)
    wos = WorkOrdersNormalizer.normalize_list(raw_wos)

    kpis = ExecutiveKPIService.get_executive_kpis(deals, wos, reference_date=pd.Timestamp("2026-08-30"))
    assert "open_pipeline" in kpis
    assert "weighted_pipeline" in kpis
    assert "work_order_contract_value" in kpis
    assert "outstanding_receivables" in kpis
    
    op = kpis["open_pipeline"]
    assert op["value"] == 100000.0

def test_founder_insights_engine():
    """Verify Founder Insights rules for top opportunities and high receivables."""
    raw_deals = [
        {"Deal Name": "Small Deal", "Deal Status": "Open", "Masked Deal value": 50000},
        {"Deal Name": "Mega Deal", "Deal Status": "Open", "Masked Deal value": 5000000},
    ]
    raw_wos = [
        {"Serial #": "WO-01", "Deal name masked": "Mega Deal", "Amount Receivable (Masked)": 2000000},
    ]
    deals = DealsNormalizer.normalize_list(raw_deals)
    wos = WorkOrdersNormalizer.normalize_list(raw_wos)

    top_opps = FounderInsightsEngine.get_top_opportunities(deals, top_n=1)
    assert len(top_opps) == 1
    assert top_opps[0]["deal_name"] == "Mega Deal"

    ar_risks = FounderInsightsEngine.get_high_receivable_risks(wos, threshold=1000000.0)
    assert len(ar_risks) == 1
    assert ar_risks[0]["wo_id"] == "WO-01"

def test_empty_dataset_handling():
    """Verify analytics engines safely handle empty datasets without throwing exceptions."""
    deals = []
    wos = []

    pipe_sum = PipelineAnalytics.calculate_summary(deals)
    assert pipe_sum["open_deals_count"] == 0
    assert pipe_sum["open_pipeline_value"] == 0.0

    wo_sum = WorkOrderAnalytics.calculate_summary(wos)
    assert wo_sum["total_work_orders_count"] == 0

    kpis = ExecutiveKPIService.get_executive_kpis(deals, wos)
    assert kpis["open_pipeline"]["value"] == 0.0

def test_analytics_service_facade():
    """Verify AnalyticsService interface methods."""
    deals = DealsNormalizer.normalize_list([{"Deal Name": "D1", "Deal Status": "Open", "Masked Deal value": 100000}])
    wos = WorkOrdersNormalizer.normalize_list([{"Serial #": "WO-01", "Deal name masked": "D1", "Amount in Rupees (Incl of GST) (Masked)": 50000}])

    svc = AnalyticsService(deals, wos)
    exec_summary = svc.get_executive_summary()
    assert "kpis" in exec_summary
    assert "top_opportunities" in exec_summary

    pipe_summary = svc.get_pipeline_summary()
    assert pipe_summary["open_deals_count"] == 1

    wo_summary = svc.get_work_order_summary()
    assert wo_summary["total_work_orders_count"] == 1
