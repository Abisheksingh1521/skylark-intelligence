import sys
import pandas as pd
from data.normalizer import DealsNormalizer, WorkOrdersNormalizer
from analytics.service import AnalyticsService
from ai.agent import SkylarkBIAgent
from ai.provider import MockAIProvider

sys.stdout.reconfigure(encoding='utf-8')

deals_path = r"C:\Users\ABI\OneDrive\Desktop\Deal funnel Data.xlsx"
wo_path = r"C:\Users\ABI\OneDrive\Desktop\Work_Order_Tracker Data.xlsx"

df_deals_raw = pd.read_excel(deals_path, sheet_name='Deal tracker', header=0)
df_wo_raw = pd.read_excel(wo_path, sheet_name='work order tracker', header=1)

deals = DealsNormalizer.normalize_list(df_deals_raw.to_dict(orient='records'))
wos = WorkOrdersNormalizer.normalize_list(df_wo_raw.to_dict(orient='records'))

svc = AnalyticsService(deals, wos)
agent = SkylarkBIAgent(svc, provider=MockAIProvider())

sample_queries = [
    "What is our open and weighted pipeline?",
    "Which sector has the strongest pipeline?",
    "How much money are we waiting to collect in receivables?",
    "What are the biggest risks and sector execution anomalies?",
    "vague_query_test: show me pipeline"
]

print("=== SKYLARK BI AGENT DEMO ===")
for q in sample_queries:
    agent.reset_conversation()
    print(f"\nUser: {q}")
    resp = agent.ask(q)
    print(f"Agent ({'Clarification' if resp.clarification_needed else 'Answer'}):")
    print(resp.answer[:250] + "..." if len(resp.answer) > 250 else resp.answer)
    print(f"Tools Used: {resp.tools_used}")
    if resp.caveats:
        print(f"Caveats ({len(resp.caveats)}): {resp.caveats[0][:120]}...")
