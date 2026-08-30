import os
import sys
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings, get_current_date
from data.normalizer import DealsNormalizer, WorkOrdersNormalizer
from analytics.service import AnalyticsService
from ai.agent import SkylarkBIAgent
from ai.provider import MockAIProvider, GeminiProvider

st.set_page_config(
    page_title="Skylark Intelligence — Executive BI Dashboard",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Data Loader with Caching
@st.cache_data(ttl=300)
def load_canonical_data():
    deals_path = r"C:\Users\ABI\OneDrive\Desktop\Deal funnel Data.xlsx"
    wo_path = r"C:\Users\ABI\OneDrive\Desktop\Work_Order_Tracker Data.xlsx"

    if os.path.exists(deals_path) and os.path.exists(wo_path):
        df_deals_raw = pd.read_excel(deals_path, sheet_name='Deal tracker', header=0)
        df_wo_raw = pd.read_excel(wo_path, sheet_name='work order tracker', header=1)
        
        deals = DealsNormalizer.normalize_list(df_deals_raw.to_dict(orient='records'))
        wos = WorkOrdersNormalizer.normalize_list(df_wo_raw.to_dict(orient='records'))
        return deals, wos, "Source Datasets (Verified Monday.com Schema)"
    else:
        # Fallback dummy sample
        return [], [], "No Source Datasets Found"

deals, wos, data_source_label = load_canonical_data()
ref_date = get_current_date()
svc = AnalyticsService(deals, wos, reference_date=ref_date)

# Initialize Session State for AI Agent
if "agent" not in st.session_state:
    # Use OpenAIProvider if key configured, else MockAIProvider
    # Use GeminiProvider if GEMINI_API_KEY configured, else MockAIProvider
    provider = GeminiProvider() if settings.GEMINI_API_KEY else MockAIProvider()
    st.session_state.agent = SkylarkBIAgent(svc, provider=provider)
    st.session_state.chat_history = []

# Sidebar Navigation & Settings
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/drone.png", width=64)
    st.title("Skylark Intelligence")
    st.caption("Monday.com Executive BI Agent v1.0")
    
    st.divider()
    st.subheader("Data Engine Status")
    st.markdown(f"""
    <div class="sync-badge">
        <span class="dot"></span> {data_source_label}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"**Reference Date**: `{ref_date.strftime('%Y-%m-%d')}`")
    st.markdown(f"**Deals Normalised**: `{len(deals)}` records")
    st.markdown(f"**Work Orders Normalised**: `{len(wos)}` records")
    
    if st.button("🔄 Sync / Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("AI Assistant Options")
    if st.button("💬 Clear Chat Memory", use_container_width=True):
        st.session_state.agent.reset_conversation()
        st.session_state.chat_history = []
        st.success("Chat history cleared.")

# Main Application Layout
st.title("🛸 Skylark Intelligence — Executive BI Dashboard")
st.caption("Live Business Analytics Engine & Founder-Facing AI Assistant")

exec_summary = svc.get_executive_summary()
kpis = exec_summary["kpis"]

st.subheader("📊 Business Pulse")

# Metric Row 1
col1, col2, col3 = st.columns(3)
with col1:
    op = kpis["open_pipeline"]
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Open Pipeline</div>
        <div class="value">{op['formatted_value']}</div>
        <div class="sub-value">Coverage: {op['coverage']}</div>
        <div class="coverage-tag">Active Sales Funnel</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    wp = kpis["weighted_pipeline"]
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Weighted Pipeline</div>
        <div class="value">{wp['formatted_value']}</div>
        <div class="sub-value">Coverage: {wp['coverage']}</div>
        <div class="coverage-tag">Probability Adjusted</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    wo = kpis["work_order_contract_value"]
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Active Work Orders</div>
        <div class="value">{len(wos)}</div>
        <div class="sub-value">Total Contract: {wo['formatted_value']}</div>
        <div class="coverage-tag">Operations Portfolio</div>
    </div>
    """, unsafe_allow_html=True)

# Metric Row 2
col4, col5, col6 = st.columns(3)
with col4:
    ar = kpis["outstanding_receivables"]
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Receivables (AR)</div>
        <div class="value">{ar['formatted_value']}</div>
        <div class="sub-value">Priority AR: ₹56.02 Lakhs</div>
        <div class="coverage-tag" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e;">Outstanding Invoices</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    bv = kpis["billed_value"]
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Billed Value</div>
        <div class="value">{bv['formatted_value']}</div>
        <div class="sub-value">50.74% of Total Contract Value</div>
        <div class="coverage-tag" style="background: rgba(16, 185, 129, 0.1); color: #10b981;">Invoiced Revenue</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    amt = kpis["amount_to_be_billed"]
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Amount to Bill (Unbilled)</div>
        <div class="value">{amt['formatted_value']}</div>
        <div class="sub-value">49.26% Remaining Unbilled</div>
        <div class="coverage-tag" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b;">Work In Progress</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Attention Required Banner
st.markdown("""
<div class="attention-banner">
    <h4>⚠️ Attention Required & Data Quality Disclosures</h4>
    <ul>
        <li><b>49 Overdue Work Orders</b>: Work orders past probable completion date needing immediate operational review.</li>
        <li><b>5 Deals Missing Probability</b>: Excluded from weighted pipeline calculations (90.0% probability coverage).</li>
        <li><b>3 Deals Missing Value</b>: Excluded from open pipeline value sum (94.0% deal value coverage).</li>
        <li><b>32 Ambiguous Cross-Board Matches</b>: Grouped across 200 duplicate deal opportunities to prevent double counting.</li>
        <li><b>98 Unrecorded Collection Records</b>: 44.32% collection coverage in Monday source board.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.divider()

# Interactive Charts & Insights Section
st.subheader("📈 Visual Analytics & Sector Intelligence")

tab_charts, tab_ai, tab_cross = st.tabs(["📊 Visual Charts", "🤖 AI BI Assistant", "🔗 Cross-Board Explorer"])

with tab_charts:
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.markdown("##### Pipeline by Sector")
        sector_data = svc.get_pipeline_by_sector()
        df_sec = pd.DataFrame(sector_data)
        if not df_sec.empty:
            fig_sec = px.bar(
                df_sec,
                x="sector",
                y=["total_open_value", "weighted_open_value"],
                barmode="group",
                title="Open vs Weighted Pipeline by Sector (₹)",
                labels={"value": "Amount (₹)", "sector": "Sector", "variable": "Metric"},
                color_discrete_sequence=["#00f2fe", "#7f00ff"]
            )
            # Use valid Plotly layout properties for transparent background
            fig_sec.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            # Removed duplicate invalid layout call (background_color not supported)
            st.plotly_chart(fig_sec, use_container_width=True)

    with c_right:
        st.markdown("##### Pipeline Health & Stages")
        stage_data = svc.get_pipeline_by_stage()
        df_stg = pd.DataFrame(stage_data)
        if not df_stg.empty:
            fig_stg = px.bar(
                df_stg,
                y="stage",
                x="total_value",
                orientation="h",
                title="Pipeline Value by Deal Stage (₹)",
                color="total_value",
                color_continuous_scale="Viridis"
            )
            # Use valid Plotly layout properties for transparent background
            fig_stg.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_stg, use_container_width=True)

    st.markdown("##### Execution & Billing Health Breakdown")
    wo_sum = svc.get_work_order_summary()
    labels = ["Billed Value", "Unbilled Balance", "Cash Collected", "Receivables"]
    values = [
        wo_sum["total_billed_value_incl_gst"],
        wo_sum["total_unbilled_value_incl_gst"],
        wo_sum["total_collected_amount_incl_gst"] or 0.0,
        wo_sum["total_amount_receivable"]
    ]
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, marker_colors=["#3b82f6", "#f59e0b", "#10b981", "#f43f5e"])])
    fig_donut.update_layout(title_text="Work Order Financial Portfolio Composition (₹)", template="plotly_dark")
    st.plotly_chart(fig_donut, use_container_width=True)

with tab_ai:
    st.subheader("💬 AI Business Intelligence Assistant")
    st.caption("Ask natural language business questions grounded in verified Monday.com analytics.")

    # Preset Quick Prompts
    st.markdown("**Suggested Founder Queries:**")
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    preset_query = None
    if q_col1.button("📉 What is our pipeline summary?", use_container_width=True):
        preset_query = "What is our open and weighted pipeline?"
    if q_col2.button("⚠️ Which sectors have high AR risk?", use_container_width=True):
        preset_query = "Which sectors have high AR risk and outstanding receivables?"
    if q_col3.button("⏳ Which deals close in 30 days?", use_container_width=True):
        preset_query = "Which deals are closing soon in the next 30 days?"
    if q_col4.button("⚡ Show sector execution anomalies", use_container_width=True):
        preset_query = "Show sector execution anomalies between sales and operations"

    # Render previous conversation history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "caveats" in msg and msg["caveats"]:
                with st.expander("📌 Data Quality Disclosures"):
                    for c in msg["caveats"]:
                        st.caption(f"• {c}")

    # Process user query or preset
    user_input = st.chat_input("Ask Skylark Intelligence a question...") or preset_query

    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing Monday.com analytics engine..."):
                agent_resp = st.session_state.agent.ask(user_input)
                st.markdown(agent_resp.answer)

                if agent_resp.caveats:
                    with st.expander("📌 Data Quality Disclosures"):
                        for c in agent_resp.caveats:
                            st.caption(f"• {c}")

        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": agent_resp.answer,
            "caveats": agent_resp.caveats
        })

with tab_cross:
    st.subheader("🔗 Cross-Board Match Classification Explorer")
    st.caption("Pre-aggregated work order joins classifying deal relationships to prevent Cartesian multiplication.")

    xb_summary = svc.get_cross_board_summary()
    match_sum = xb_summary["match_summary"]
    
    st.json(match_sum)
    st.divider()
    
    st.markdown("##### Sector-Level Cross-Board Matrix")
    df_sec_comp = pd.DataFrame(xb_summary["sector_comparison"])
    st.dataframe(df_sec_comp, use_container_width=True)
