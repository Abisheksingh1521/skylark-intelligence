from typing import List, Dict, Any, Callable
from analytics.service import AnalyticsService

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_executive_summary",
            "description": "Get high-level executive KPI summary, top opportunities, and sector anomalies.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_summary",
            "description": "Get sales pipeline summary including Open Pipeline, Weighted Pipeline, deal counts, and coverage %.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_by_sector",
            "description": "Get open pipeline breakdown grouped by sector (Mining, Renewables, Powerline, etc.).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_by_stage",
            "description": "Get open pipeline breakdown grouped by deal stage (Lead Generated, Feasibility, Proposals, etc.).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_closing_soon_deals",
            "description": "Get list of open deals scheduled to close within a target timeframe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Number of days ahead to look (default: 60)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_work_order_summary",
            "description": "Get operational summary for Work Orders: total contract value, billed, unbilled, collected, AR, and overdue count.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_billing_health",
            "description": "Get billing progress, contract vs billed value, unbilled amount, and invoice status distribution.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_collection_health",
            "description": "Get cash collection health, recorded collections, unrecorded counts, and coverage statistics.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_receivables",
            "description": "Get outstanding accounts receivable (AR) exposure and high-priority collection accounts.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cross_board_summary",
            "description": "Get cross-board match classification summary (Strong matches, Ambiguous matches, Unmatched) and sector comparison.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_quality_summary",
            "description": "Get complete data quality diagnostics and caveats for Deals and Work Orders.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_founder_insights",
            "description": "Get founder-level insights: top opportunities, high AR exposure, and sector execution anomalies.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]


class AnalyticsToolExecutor:
    """
    Safely executes tool calls against an AnalyticsService instance.
    Enforces a strict tool allowlist (No arbitrary execution, no database writes, no Monday mutations).
    """

    ALLOWED_TOOLS = {
        "get_executive_summary",
        "get_pipeline_summary",
        "get_pipeline_by_sector",
        "get_pipeline_by_stage",
        "get_closing_soon_deals",
        "get_work_order_summary",
        "get_billing_health",
        "get_collection_health",
        "get_receivables",
        "get_cross_board_summary",
        "get_data_quality_summary",
        "get_founder_insights"
    }

    def __init__(self, analytics_service: AnalyticsService):
        self.service = analytics_service

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self.ALLOWED_TOOLS:
            raise PermissionError(f"Security Alert: Tool '{tool_name}' is not in the read-only tool allowlist.")

        if tool_name == "get_executive_summary":
            return self.service.get_executive_summary()
        elif tool_name == "get_pipeline_summary":
            return self.service.get_pipeline_summary()
        elif tool_name == "get_pipeline_by_sector":
            return {"sectors": self.service.get_pipeline_by_sector()}
        elif tool_name == "get_pipeline_by_stage":
            return {"stages": self.service.get_pipeline_by_stage()}
        elif tool_name == "get_closing_soon_deals":
            days = arguments.get("days_ahead", 60)
            return {"deals_closing_soon": self.service.get_closing_soon_deals(days_ahead=days)}
        elif tool_name == "get_work_order_summary":
            return self.service.get_work_order_summary()
        elif tool_name == "get_billing_health":
            return self.service.get_billing_health()
        elif tool_name == "get_collection_health":
            return self.service.get_collection_health()
        elif tool_name == "get_receivables":
            return self.service.get_receivables()
        elif tool_name == "get_cross_board_summary":
            return self.service.get_cross_board_summary()
        elif tool_name == "get_data_quality_summary":
            return self.service.get_data_quality_summary()
        elif tool_name == "get_founder_insights":
            return {
                "top_opportunities": self.service.get_executive_summary()["top_opportunities"],
                "sector_anomalies": self.service.get_executive_summary()["sector_anomalies"],
                "receivables": self.service.get_receivables()
            }
        else:
            raise ValueError(f"Unknown tool '{tool_name}'")
