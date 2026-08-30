from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import json

class AIProvider(ABC):
    """
    Abstract AI Provider Interface.
    Decouples the BI Agent from specific LLM vendors (OpenAI, Anthropic, Gemini, etc.).
    """

    @abstractmethod
    def generate_response(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate response with optional tool choices."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verify API connectivity and key validity."""
        pass


class OpenAIProvider(AIProvider):
    """
    OpenAI API Provider implementation using official OpenAI SDK.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("AI_MODEL", model)
        self._client = None
        if self.api_key:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                self._client = None

    def health_check(self) -> bool:
        return self._client is not None and bool(self.api_key)

    def generate_response(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("OpenAI client is not initialized. Please set OPENAI_API_KEY.")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {}
                })

        return {
            "content": msg.content or "",
            "tool_calls": tool_calls,
            "role": "assistant"
        }

from dotenv import load_dotenv
load_dotenv(override=True)

class GeminiProvider(AIProvider):
    """Gemini API Provider using official google-genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = (
            model_name
            or os.getenv("GEMINI_MODEL")
            or "gemini-2.5-flash-lite"
        )

        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None

    def health_check(self) -> bool:
        return self._client is not None and bool(self.api_key)

    def generate_response(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("Gemini client is not initialized. Please set GEMINI_API_KEY.")

        try:
            from google.genai import types
        except ImportError:
            types = None

        system_parts = []
        gemini_contents = []

        for m in messages:
            role = m.get("role", "user")
            content_str = m.get("content", "")
            if role == "system":
                system_parts.append(content_str)
            elif role in ["user", "human"]:
                if types:
                    gemini_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content_str)]))
                else:
                    gemini_contents.append({"role": "user", "parts": [content_str]})
            elif role in ["assistant", "model"]:
                if types:
                    gemini_contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content_str or "")]))
                else:
                    gemini_contents.append({"role": "model", "parts": [content_str or ""]})
            elif role == "tool":
                tool_name = m.get("name", "tool")
                tool_text = f"Tool '{tool_name}' result: {content_str}"
                if types:
                    gemini_contents.append(types.Content(role="user", parts=[types.Part.from_text(text=tool_text)]))
                else:
                    gemini_contents.append({"role": "user", "parts": [tool_text]})

        system_instruction = "\n\n".join(system_parts) if system_parts else None

        genai_tools = None
        if tools and types:
            func_declarations = []
            for tool_item in tools:
                if isinstance(tool_item, dict):
                    if "function" in tool_item and isinstance(tool_item["function"], dict):
                        func = tool_item["function"]
                    else:
                        func = tool_item
                    fd = types.FunctionDeclaration(
                        name=func["name"],
                        description=func.get("description", ""),
                        parameters_json_schema=func.get("parameters", {})
                    )
                    func_declarations.append(fd)
                elif hasattr(tool_item, "name"):
                    func_declarations.append(tool_item)

            if func_declarations:
                genai_tools = [types.Tool(function_declarations=func_declarations)]

        if types:
            config_kwargs = {
                "temperature": 0.2,
                "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True)
            }
            if system_instruction:
                config_kwargs["system_instruction"] = system_instruction
            if genai_tools:
                config_kwargs["tools"] = genai_tools

            config = types.GenerateContentConfig(**config_kwargs)
        else:
            config = None

        try:
            if hasattr(self._client, "models") and hasattr(self._client.models, "generate_content"):
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=gemini_contents,
                    config=config
                )
            elif hasattr(self._client, "generate_content"):
                response = self._client.generate_content(gemini_contents, tools=tools)
            else:
                raise RuntimeError("Gemini client generate_content method unavailable.")
        except RuntimeError:
            raise
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str or "limit" in err_str:
                raise RuntimeError(f"Gemini API error: Quota limits exceeded: {str(e)}")
            elif "api key" in err_str or "unauthorized" in err_str or "forbidden" in err_str or "invalid" in err_str:
                raise RuntimeError(f"Gemini API error: Authentication failed: {str(e)}")
            else:
                raise RuntimeError(f"Gemini API error: {str(e)}")

        content = ""
        try:
            if getattr(response, "text", None):
                content = response.text
        except Exception:
            content = ""

        if not content and getattr(response, "candidates", None):
            text_parts = []
            for candidate in response.candidates:
                if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
                    for part in candidate.content.parts:
                        if getattr(part, "text", None):
                            text_parts.append(part.text)
            content = "".join(text_parts)

        tool_calls = []
        if getattr(response, "function_calls", None):
            for fc in response.function_calls:
                name = getattr(fc, "name", "")
                args = dict(fc.args) if getattr(fc, "args", None) else {}
                tool_calls.append({
                    "id": getattr(fc, "id", None) or name,
                    "name": name,
                    "arguments": args
                })
        elif getattr(response, "candidates", None):
            for candidate in response.candidates:
                if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
                    for part in candidate.content.parts:
                        fc = getattr(part, "function_call", None)
                        if fc:
                            name = getattr(fc, "name", "")
                            args = dict(fc.args) if getattr(fc, "args", None) else {}
                            tool_calls.append({
                                "id": getattr(fc, "id", None) or name,
                                "name": name,
                                "arguments": args
                            })

        return {
            "content": content,
            "tool_calls": tool_calls,
            "role": "assistant"
        }

class MockAIProvider(AIProvider):
    """
    Mock AI Provider for deterministic unit testing.
    Uses pattern matching to decide which analytics tool to call and generates structured responses.
    """

    def health_check(self) -> bool:
        return True

    def generate_response(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        last_msg = messages[-1]["content"].lower() if messages else ""
        
        has_tool_result = any(m.get("role") == "tool" for m in messages)
        if has_tool_result:
            tool_msg = next((m for m in reversed(messages) if m.get("role") == "tool"), {})
            content = tool_msg.get("content", "")
            return {
                "content": f"Based on our structured analytics:\n\n{content}",
                "tool_calls": [],
                "role": "assistant"
            }

        tool_calls = []

        if "vague_query_test" in last_msg or last_msg.strip() in ["show me pipeline", "show me the pipeline"]:
            return {
                "content": "Sure! Would you like the overall pipeline summary, or would you prefer a breakdown by sector or stage?",
                "tool_calls": [],
                "role": "assistant"
            }

        if "cross" in last_msg or "cross board" in last_msg or "cross-board" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_cross_board_summary", "arguments": {}})
        elif "work order" in last_msg or "work orders" in last_msg or "project" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_work_order_summary", "arguments": {}})
        elif "weighted" in last_msg or "probability" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_pipeline_summary", "arguments": {}})
        elif "sector" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_pipeline_by_sector", "arguments": {}})
        elif "stage" in last_msg or "stuck" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_pipeline_by_stage", "arguments": {}})
        elif "closing soon" in last_msg or "next 30 days" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_closing_soon_deals", "arguments": {"days_ahead": 60}})
        elif "billed" in last_msg or "unbilled" in last_msg or "billing" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_billing_health", "arguments": {}})
        elif "collected" in last_msg or "collection" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_collection_health", "arguments": {}})
        elif "receivable" in last_msg or "receivables" in last_msg or " ar " in f" {last_msg} ":
            tool_calls.append({"id": "call_1", "name": "get_receivables", "arguments": {}})
        elif "risk" in last_msg or "worried" in last_msg or "focus" in last_msg or "insight" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_founder_insights", "arguments": {}})
        elif "pipeline" in last_msg:
            tool_calls.append({"id": "call_1", "name": "get_pipeline_summary", "arguments": {}})
        else:
            tool_calls.append({"id": "call_1", "name": "get_executive_summary", "arguments": {}})

        return {
            "content": "",
            "tool_calls": tool_calls,
            "role": "assistant"
        }
