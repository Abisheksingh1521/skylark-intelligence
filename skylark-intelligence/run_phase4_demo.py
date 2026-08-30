import sys
import pandas as pd
from data.normalizer import DealsNormalizer, WorkOrdersNormalizer
from analytics.service import AnalyticsService

sys.stdout.reconfigure(encoding='utf-8')

deals_path = r"C:\Users\ABI\OneDrive\Desktop\Deal funnel Data.xlsx"
wo_path = r"C:\Users\ABI\OneDrive\Desktop\Work_Order_Tracker Data.xlsx"

df_deals_raw = pd.read_excel(deals_path, sheet_name='Deal tracker', header=0)
df_wo_raw = pd.read_excel(wo_path, sheet_name='work order tracker', header=1)

deals_dicts = df_deals_raw.to_dict(orient='records')
wo_dicts = df_wo_raw.to_dict(orient='records')

deals = DealsNormalizer.normalize_list(deals_dicts)
wos = WorkOrdersNormalizer.normalize_list(wo_dicts)

svc = AnalyticsService(deals, wos)

print("=== EXECUTIVE SUMMARY ===")
exec_summary = svc.get_executive_summary()
for k, kpi in exec_summary["kpis"].items():
    print(f"{kpi['name']}: {kpi['formatted_value']} (Coverage: {kpi['coverage']})")

print("\n=== CROSS BOARD MATCH CLASSIFICATION ===")
xb_summary = svc.get_cross_board_summary()
print("Match Summary:", xb_summary["match_summary"])

print("\n=== TOP FOUNDER OPPORTUNITIES ===")
for opp in exec_summary["top_opportunities"]:
    print(f"  {opp['deal_name']} ({opp['sector']}): ₹{opp['deal_value']:,.2f} [Stage: {opp['stage']}]")

print("\n=== SECTOR EXECUTION ANOMALIES ===")
for an in exec_summary["sector_anomalies"]:
    print(f"  {an['anomaly_description']}")
