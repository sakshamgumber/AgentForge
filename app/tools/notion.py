"""Notion MCP Tool integration for AgentForge.

Exposes Notion tools strictly through external MCP servers via AgentForge's BaseMCPToolProvider:
- Standardized BaseTool interface compatible with LangGraph and OpenAI function calling
- Role-based ToolPermission enforcement (READ, WRITE, DESTRUCTIVE)
- PostgreSQL tool execution audit logging (tools table)
- attempt_id and operation_id tracing across agent steps
- Server-side execution timeouts and output compression
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from app.mcp.tool_wrapper import MCPToolWrapper

from app.tools.base_provider import BaseMCPToolProvider
from app.tools.enums import ToolPermission

logger = logging.getLogger(__name__)


def infer_notion_permission(tool_name: str) -> ToolPermission:
    """Infer ToolPermission based on Notion action prefix.

    - READ: search, query, get, fetch, retrieve, list, read, view
    - WRITE: create, update, append, insert, add, edit, duplicate, restore, write
    - DESTRUCTIVE: delete, archive, trash, remove, destroy
    """
    cleaned_name = tool_name.lower()
    if cleaned_name.startswith("notion_"):
        cleaned_name = cleaned_name[len("notion_"):]

    if any(cleaned_name.startswith(p) for p in ("delete", "archive", "trash", "remove", "destroy")):
        return ToolPermission.DESTRUCTIVE

    if any(cleaned_name.startswith(p) for p in ("create", "update", "append", "insert", "add", "edit", "duplicate", "restore", "write")):
        return ToolPermission.WRITE

    return ToolPermission.READ


class NotionToolProvider(BaseMCPToolProvider):
    """MCP tool provider for Notion workspace integration."""

    @property
    def server_name(self) -> str:
        return "notion"

    def infer_permission(self, tool_name: str) -> ToolPermission:
        return infer_notion_permission(tool_name)

    async def get_tools(
        self,
        access_token: Optional[str] = None,
        url: Optional[str] = None,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
        client_manager: Optional[Any] = None,
    ) -> List[MCPToolWrapper]:
        """Retrieve Notion tools from MCP server with custom credentials and error handling."""
        from app.mcp.configuration.notion import get_notion_config

        custom_configs = {}
        if access_token or url:
            custom_configs["notion"] = get_notion_config(
                url=url,
                access_token=access_token,
            )

        return await super().get_tools(
            attempt_id=attempt_id,
            operation_id=operation_id,
            enable_db_logging=enable_db_logging,
            timeout_seconds=timeout_seconds,
            client_manager=client_manager,
            custom_configs=custom_configs if custom_configs else None,
        )


# Default singleton provider instance
notion_provider = NotionToolProvider()


def create_notion_mcp_wrapper(
    mcp_tool: Any,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    permissions: Optional[ToolPermission] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    max_output_chars: Optional[int] = 4000,
    compress_output: bool = True,
) -> MCPToolWrapper:
    """Wrap a Notion MCP tool instance into AgentForge's MCPToolWrapper."""
    return notion_provider.wrap_tool(
        mcp_tool=mcp_tool,
        attempt_id=attempt_id,
        operation_id=operation_id,
        permissions=permissions,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        compress_output=compress_output,
    )


async def get_notion_tools(
    access_token: Optional[str] = None,
    url: Optional[str] = None,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    client_manager: Optional[Any] = None,
) -> List[MCPToolWrapper]:
    """Retrieve Notion tools from the MCP server, wrapped in MCPToolWrapper."""
    return await notion_provider.get_tools(
        access_token=access_token,
        url=url,
        attempt_id=attempt_id,
        operation_id=operation_id,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        client_manager=client_manager,
    )
