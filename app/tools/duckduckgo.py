"""DuckDuckGo MCP Tool integration for AgentForge.

Exposes DuckDuckGo search strictly through external MCP servers via AgentForge's BaseMCPToolProvider:
- Standardized BaseTool interface compatible with LangGraph and OpenAI function calling
- PostgreSQL tool execution audit logging (tools table)
- attempt_id and operation_id tracing across agent steps
- Configurable execution timeouts and permissions
- Server-side output compression and token truncation
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.mcp.tool_wrapper import MCPToolWrapper
from app.tools.base_provider import BaseMCPToolProvider
from app.tools.enums import ToolPermission


class DuckDuckGoToolProvider(BaseMCPToolProvider):
    """MCP tool provider for DuckDuckGo public web search."""

    @property
    def server_name(self) -> str:
        return "duckduckgo"

    def infer_permission(self, tool_name: str) -> ToolPermission:
        return ToolPermission.READ


# Default singleton provider instance
duckduckgo_provider = DuckDuckGoToolProvider()


def create_duckduckgo_mcp_wrapper(
    mcp_tool: Any,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    max_output_chars: Optional[int] = 4000,
    compress_output: bool = True,
) -> MCPToolWrapper:
    """Wrap a DuckDuckGo MCP tool instance into AgentForge's MCPToolWrapper."""
    return duckduckgo_provider.wrap_tool(
        mcp_tool=mcp_tool,
        attempt_id=attempt_id,
        operation_id=operation_id,
        permissions=ToolPermission.READ,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        compress_output=compress_output,
    )


async def get_duckduckgo_tools(
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    client_manager: Optional[Any] = None,
) -> List[MCPToolWrapper]:
    """Retrieve DuckDuckGo tools from the MCP server, wrapped in MCPToolWrapper."""
    return await duckduckgo_provider.get_tools(
        attempt_id=attempt_id,
        operation_id=operation_id,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        client_manager=client_manager,
    )
