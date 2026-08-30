from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import logging
from analytics.service import AnalyticsService
from ai.provider import AIProvider, MockAIProvider
from ai.prompts import get_system_prompt
from ai.tools import TOOL_SCHEMAS, AnalyticsToolExecutor

logger = logging.getLogger(__name__)

@dataclass
class AgentResponse:
    answer: str
    insights: List[str] = field(default_factory=list)
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    clarification_needed: bool = False

def _extract_caveats_recursive(obj: Any) -> List[str]:
    """Recursively find 'data_quality_caveat' or 'caveat' strings in tool outputs."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ["data_quality_caveat", "caveat"] and isinstance(v, str):
                found.append(v)
            else:
                found.extend(_extract_caveats_recursive(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_extract_caveats_recursive(item))
    return found

class SkylarkBIAgent:
    """
    Production-quality AI Business Intelligence Agent.
    Connects LLM natural language intent to deterministic Phase 4 AnalyticsService.
    Manages conversational memory, tool selection, data quality caveats, and founder responses.
    """

    def __init__(self, analytics_service: AnalyticsService, provider: Optional[AIProvider] = None):
        self.service = analytics_service
        self.provider = provider or MockAIProvider()
        self.tool_executor = AnalyticsToolExecutor(analytics_service)
        self.conversation_history: List[Dict[str, Any]] = [
            {"role": "system", "content": get_system_prompt()}
        ]

    def reset_conversation(self):
        """Reset conversation memory while preserving system prompt."""
        self.conversation_history = [
            {"role": "system", "content": get_system_prompt()}
        ]

    def ask(self, user_query: str) -> AgentResponse:
        """Process natural language query and return structured AgentResponse."""
        if not user_query or not user_query.strip():
            return AgentResponse(
                answer="Please enter a business query (e.g., 'What is our open pipeline?' or 'Which work orders are overdue?').",
                clarification_needed=True
            )

        self.conversation_history.append({"role": "user", "content": user_query})

        tools_used = []
        caveats = []
        sources = ["Monday.com Deals Board", "Monday.com Work Orders Board"]
        insights = []
        metrics = []

        try:
            response_payload = self.provider.generate_response(
                messages=self.conversation_history,
                tools=TOOL_SCHEMAS
            )

            tool_calls = response_payload.get("tool_calls", [])

            if not tool_calls:
                answer_content = response_payload.get("content", "")
                self.conversation_history.append({"role": "assistant", "content": answer_content})
                
                is_clarification = "?" in answer_content and any(
                    word in answer_content.lower() for word in ["would you", "clarify", "do you want", "prefer"]
                )

                return AgentResponse(
                    answer=answer_content,
                    insights=insights,
                    metrics=metrics,
                    caveats=caveats,
                    sources=sources,
                    tools_used=tools_used,
                    clarification_needed=is_clarification
                )

            for tc in tool_calls:
                tool_name = tc["name"]
                args = tc.get("arguments", {})
                tools_used.append(tool_name)

                tool_result = self.tool_executor.execute_tool(tool_name, args)

                # Recursively extract all caveats from tool output
                extracted = _extract_caveats_recursive(tool_result)
                caveats.extend(extracted)

                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tool_name,
                    "content": json.dumps(tool_result, default=str)
                })

            final_payload = self.provider.generate_response(
                messages=self.conversation_history,
                tools=None
            )
            final_text = final_payload.get("content", "")
            self.conversation_history.append({"role": "assistant", "content": final_text})

            for line in final_text.split("\n"):
                line_str = line.strip()
                if line_str.startswith("- ") or line_str.startswith("* "):
                    insights.append(line_str[2:])

            return AgentResponse(
                answer=final_text,
                insights=insights,
                metrics=metrics,
                caveats=list(set(caveats)),
                sources=sources,
                tools_used=tools_used,
                clarification_needed=False
            )

        except Exception as e:
            logger.error(f"Error processing agent query: {str(e)}", exc_info=True)
            err_msg = "I couldn't retrieve or compute the requested Monday.com analytics data right now. Please try again."
            return AgentResponse(
                answer=f"{err_msg} (Error: {str(e)})",
                caveats=[f"Execution exception: {str(e)}"],
                tools_used=tools_used,
                clarification_needed=False
            )
