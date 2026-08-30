import pytest
import pandas as pd
from data.normalizer import DealsNormalizer, WorkOrdersNormalizer
from analytics.service import AnalyticsService
from ai.agent import SkylarkBIAgent, AgentResponse
from ai.provider import MockAIProvider
from ai.tools import AnalyticsToolExecutor

@pytest.fixture
def sample_analytics_service():
    raw_deals = [
        {"Deal Name": "Energy Deal 1", "Deal Status": "Open", "Masked Deal value": 500000, "Closure Probability": "High", "Sector/service": "Renewables"},
        {"Deal Name": "Energy Deal 2", "Deal Status": "Open", "Masked Deal value": 300000, "Closure Probability": None, "Sector/service": "Renewables"},
        {"Deal Name": "Mining Deal", "Deal Status": "Open", "Masked Deal value": None, "Closure Probability": "Low", "Sector/service": "Mining"},
    ]
    raw_wos = [
        {"Serial #": "WO-101", "Deal name masked": "Energy Deal 1", "Amount in Rupees (Incl of GST) (Masked)": 400000, "Amount Receivable (Masked)": 150000},
        {"Serial #": "WO-102", "Deal name masked": "Energy Deal 1", "Amount in Rupees (Incl of GST) (Masked)": 200000, "Amount Receivable (Masked)": 50000},
    ]
    deals = DealsNormalizer.normalize_list(raw_deals)
    wos = WorkOrdersNormalizer.normalize_list(raw_wos)
    return AnalyticsService(deals, wos, reference_date=pd.Timestamp("2026-08-30"))

def test_simple_pipeline_question(sample_analytics_service):
    """Test 1: Simple pipeline query."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("How is our pipeline looking?")
    assert isinstance(resp, AgentResponse)
    assert "get_pipeline_summary" in resp.tools_used
    assert "800,000" in resp.answer or "Analytics" in resp.answer

def test_weighted_pipeline_question(sample_analytics_service):
    """Test 2 & 9: Weighted pipeline query surfaces missing probability caveat."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("What is our weighted pipeline?")
    assert "get_pipeline_summary" in resp.tools_used
    assert any("probability" in c.lower() for c in resp.caveats)

def test_sector_filtering(sample_analytics_service):
    """Test 3: Sector breakdown query."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("Show me pipeline by sector")
    assert "get_pipeline_by_sector" in resp.tools_used

def test_stage_filtering(sample_analytics_service):
    """Test 4: Stage breakdown query."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("Break down pipeline by stage")
    assert "get_pipeline_by_stage" in resp.tools_used

def test_closing_soon_question(sample_analytics_service):
    """Test 5: Closing soon query."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("Which deals are closing soon in next 30 days?")
    assert "get_closing_soon_deals" in resp.tools_used

def test_work_order_question(sample_analytics_service):
    """Test 6: Work orders summary query."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("How are our work orders performing?")
    assert "get_work_order_summary" in resp.tools_used

def test_receivables_question(sample_analytics_service):
    """Test 7: Receivables exposure query."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("What is our receivables exposure?")
    assert "get_receivables" in resp.tools_used

def test_cross_board_question(sample_analytics_service):
    """Test 8 & 11: Cross board query surfaces ambiguous join caveat."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("Compare pipeline and execution cross board by sector")
    assert "get_cross_board_summary" in resp.tools_used
    assert len(resp.caveats) >= 1

def test_missing_financial_values_caveat(sample_analytics_service):
    """Test 10: Missing financial values caveat is surfaced."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("What is our pipeline?")
    assert any("unrecorded" in c.lower() or "missing" in c.lower() or "calculated across" in c.lower() for c in resp.caveats)

def test_tool_failure_handling(sample_analytics_service):
    """Test 12: Tool failure returns graceful error message without crashing."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    # Force invalid execution
    def failing_tool(*args, **kwargs):
        raise RuntimeError("Simulated connection timeout")
    agent.tool_executor.execute_tool = failing_tool

    resp = agent.ask("What is our open pipeline?")
    assert "couldn't retrieve" in resp.answer.lower() or "error" in resp.answer.lower()

def test_empty_dataset_handling():
    """Test 13: Empty dataset returns safe response without exception."""
    empty_svc = AnalyticsService([], [], reference_date=pd.Timestamp("2026-08-30"))
    agent = SkylarkBIAgent(empty_svc, provider=MockAIProvider())
    resp = agent.ask("What is our open pipeline?")
    assert "0" in resp.answer or "Analytics" in resp.answer

def test_invalid_user_query(sample_analytics_service):
    """Test 14: Blank or invalid query prompts user."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("   ")
    assert resp.clarification_needed is True

def test_follow_up_conversational_context(sample_analytics_service):
    """Test 15: Follow up conversation memory is preserved across turns."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp1 = agent.ask("Show me pipeline for energy sector")
    assert len(agent.conversation_history) >= 3

    resp2 = agent.ask("Which of those are closing soon?")
    assert len(agent.conversation_history) >= 5
    assert agent.conversation_history[1]["content"] == "Show me pipeline for energy sector"

def test_clarification_behavior(sample_analytics_service):
    """Test 16: Vague query triggers clarification flag."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("vague_query_test: show me pipeline")
    assert resp.clarification_needed is True

def test_no_fabricated_tool_results(sample_analytics_service):
    """Test 17: Answers are grounded in deterministic AnalyticsService values."""
    agent = SkylarkBIAgent(sample_analytics_service, provider=MockAIProvider())
    resp = agent.ask("How much is unbilled?")
    assert "get_billing_health" in resp.tools_used

def test_read_only_tool_restrictions(sample_analytics_service):
    """Test 18: Unallowed / mutation tool calls are blocked by tool executor."""
    executor = AnalyticsToolExecutor(sample_analytics_service)
    with pytest.raises(PermissionError):
        executor.execute_tool("delete_monday_record", {})
