"""DuckDuckGo MCP Tool integration for AgentForge.

Exposes DuckDuckGo search strictly through external MCP servers via AgentForge's MCPToolWrapper:
- Standardized BaseTool interface compatible with LangGraph and OpenAI function calling
- PostgreSQL tool execution audit logging (tools table)
- attempt_id and operation_id tracing across agent steps
- Configurable execution timeouts and permissions
- Server-side output compression and token truncation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.mcp.tool_wrapper import MCPToolWrapper
from app.tools.base import BaseTool, ExecutionContext, ToolStatus
from app.tools.enums import ToolPermission

logger = logging.getLogger(__name__)


def create_duckduckgo_mcp_wrapper(
    mcp_tool: Any,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    max_output_chars: Optional[int] = 4000,
    compress_output: bool = True,
) -> MCPToolWrapper:
    """Wrap a DuckDuckGo MCP tool instance into AgentForge's MCPToolWrapper.

    Args:
        mcp_tool: Underlying MCP or LangChain tool received from the MCP server.
        attempt_id: Execution attempt ID for PostgreSQL tracking.
        operation_id: Operation workflow ID for PostgreSQL tracking.
        enable_db_logging: Whether to record execution into PostgreSQL tools table.
        timeout_seconds: Server execution timeout.
        max_output_chars: Maximum output characters before compression/truncation.
        compress_output: Whether to prune and compress output.

    Returns:
        Configured MCPToolWrapper ready for agent binding or LangGraph execution.
    """
    if mcp_tool is None:
        raise ValueError("mcp_tool must be provided to create_duckduckgo_mcp_wrapper")

    return MCPToolWrapper(
        mcp_tool=mcp_tool,
        server_name="duckduckgo",
        attempt_id=attempt_id,
        operation_id=operation_id,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        permissions=ToolPermission.READ,
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
    """Retrieve DuckDuckGo tools from the MCP server, wrapped in MCPToolWrapper.

    Connects to the DuckDuckGo MCP server (uvx duckduckgo-mcp-server) over stdio.
    Raises RuntimeError if the MCP server is unreachable or returns no tools.

    Args:
        attempt_id: Execution attempt ID.
        operation_id: Operation ID.
        enable_db_logging: Enable PostgreSQL audit logging.
        timeout_seconds: Timeout in seconds.
        client_manager: Optional existing MCPClientManager instance.

    Returns:
        List containing the wrapped DuckDuckGo MCP tool(s).

    Raises:
        RuntimeError: If connecting to the DuckDuckGo MCP server fails or no tools are found.
    """
    from app.mcp.client_manager import MCPClientManager

    manager = client_manager or MCPClientManager(
        enabled_servers=["duckduckgo"],
        tool_name_prefix=True,
    )

    try:
        live_tools = await manager.get_duckduckgo_tools(
            attempt_id=attempt_id,
            operation_id=operation_id,
            enable_db_logging=enable_db_logging,
            timeout_seconds=timeout_seconds,
        )
    except Exception as e:
        logger.error("Failed to connect to DuckDuckGo MCP server: %s", e)
        raise RuntimeError(f"Could not connect to DuckDuckGo MCP server: {e}") from e

    if not live_tools:
        raise RuntimeError(
            "DuckDuckGo MCP server returned no tools. "
            "Ensure 'duckduckgo-mcp-server' is installed and 'langchain-mcp-adapters' is available."
        )

    return live_tools
