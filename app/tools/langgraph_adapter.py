"""LangGraph integration for BaseTool error handling and execution nodes."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Sequence
from app.tools.base import BaseTool, ExecutionContext, ToolError


def format_error_for_langgraph(
    tool_name: str,
    tool_call_id: str,
    error: Exception,
    attempt_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Format an exception into a structured LangGraph tool message error response."""
    error_type = error.__class__.__name__
    error_msg = str(error)
    details = getattr(error, "details", {})

    payload: Dict[str, Any] = {
        "status": "error",
        "tool_name": tool_name,
        "error_type": error_type,
        "message": error_msg,
        "details": details,
        "guidance": "Please review the required parameters and constraints and retry.",
    }
    if attempt_id:
        payload["attempt_id"] = attempt_id

    content = json.dumps(payload)

    response: Dict[str, Any] = {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": content,
        "status": "error",
    }
    if attempt_id:
        response["attempt_id"] = attempt_id
    return response



class LangGraphToolNode:
    """A tool execution node designed for LangGraph state graphs with comprehensive error handling."""

    def __init__(self, tools: Sequence[BaseTool], context: Optional[ExecutionContext] = None):
        self.tools_by_name: Dict[str, BaseTool] = {tool.name: tool for tool in tools}
        self.context = context

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool calls from the latest message/state, catching all errors for agent self-correction."""
        messages = state.get("messages", [])
        if not messages:
            return {"messages": []}

        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", None)
        if tool_calls is None and isinstance(last_message, dict):
            tool_calls = last_message.get("tool_calls", [])

        if not tool_calls:
            return {"messages": []}

        tool_messages: List[Dict[str, Any]] = []

        for call in tool_calls:
            call_id = call.get("id", "call_default") if isinstance(call, dict) else getattr(call, "id", "call_default")
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            args = call.get("args", {}) if isinstance(call, dict) else getattr(call, "args", {})

            tool = self.tools_by_name.get(name)
            if not tool:
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": f"Error: Tool '{name}' not found.",
                    "status": "error",
                })
                continue

            try:
                result = tool.execute(args, context=self.context)
                content = json.dumps(result) if not isinstance(result, str) else result
                msg: Dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": content,
                    "status": "success",
                }
                if getattr(tool, "attempt_id", None):
                    msg["attempt_id"] = tool.attempt_id
                tool_messages.append(msg)
            except Exception as e:
                # Capture tool errors (validation, timeout, permission, execution) for LangGraph recovery
                attempt_id = getattr(tool, "attempt_id", None)
                error_msg = format_error_for_langgraph(
                    tool_name=name,
                    tool_call_id=call_id,
                    error=e,
                    attempt_id=attempt_id,
                )
                tool_messages.append(error_msg)

        return {"messages": tool_messages}
