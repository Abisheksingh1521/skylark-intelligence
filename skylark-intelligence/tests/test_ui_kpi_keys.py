import os
import pandas as pd
import pytest
from config.settings import get_current_date
from data.normalizer import DealsNormalizer, WorkOrdersNormalizer
from analytics.service import AnalyticsService

# Helper to load canonical data (same as app)
def load_canonical_data():
    deals_path = r"C:\Users\ABI\OneDrive\Desktop\Deal funnel Data.xlsx"
    wo_path = r"C:\Users\ABI\OneDrive\Desktop\Work_Order_Tracker Data.xlsx"
    if os.path.exists(deals_path) and os.path.exists(wo_path):
        df_deals_raw = pd.read_excel(deals_path, sheet_name='Deal tracker', header=0)
        df_wo_raw = pd.read_excel(wo_path, sheet_name='work order tracker', header=1)
        deals = DealsNormalizer.normalize_list(df_deals_raw.to_dict(orient='records'))
        wos = WorkOrdersNormalizer.normalize_list(df_wo_raw.to_dict(orient='records'))
        return deals, wos
    else:
        return [], []

@pytest.fixture(scope="module")
def analytics_service():
    deals, wos = load_canonical_data()
    svc = AnalyticsService(deals, wos, reference_date=get_current_date())
    return svc

def test_executive_kpi_keys_present(analytics_service):
    exec_summary = analytics_service.get_executive_summary()
    kpis = exec_summary["kpis"]
    required_keys = [
        "open_pipeline",
        "weighted_pipeline",
        "work_order_contract_value",
        "outstanding_receivables",
        "billed_value",
        "amount_to_be_billed"
    ]
    missing = [k for k in required_keys if k not in kpis]
    assert not missing, f"Missing KPI keys in executive summary: {missing}"
