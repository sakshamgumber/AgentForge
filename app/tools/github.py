"""GitHub MCP Tool integration for AgentForge.

Exposes GitHub tools strictly through external MCP servers via AgentForge's BaseMCPToolProvider:
- Standardized BaseTool interface compatible with LangGraph and OpenAI function calling
- PostgreSQL tool execution audit logging (tools table)
- attempt_id and operation_id tracing across agent steps
- Role-based ToolPermission enforcement (READ, WRITE, DESTRUCTIVE)
- Server-side execution timeouts and output compression
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.mcp.tool_wrapper import MCPToolWrapper
from app.tools.base_provider import BaseMCPToolProvider
from app.tools.enums import ToolPermission

from app.mcp.configuration.github import get_github_config


def infer_github_permission(tool_name: str) -> ToolPermission:
    """Infer ToolPermission based on GitHub action prefix.

    - READ: queries, searches, inspections (get, list, search, read)
    - WRITE: resource creation and modification (create, update, add, fork, set, merge, open, close)
    - DESTRUCTIVE: irreversible changes (delete, remove, destroy, push)
    """
    cleaned_name = tool_name.lower()
    # Strip any server prefix like 'github_'
    if cleaned_name.startswith("github_"):
        cleaned_name = cleaned_name[len("github_"):]

    if any(cleaned_name.startswith(p) for p in ("delete", "remove", "destroy", "push")):
        return ToolPermission.DESTRUCTIVE

    if any(cleaned_name.startswith(p) for p in ("create", "update", "add", "fork", "set", "merge", "open", "close")):
        return ToolPermission.WRITE

    return ToolPermission.READ


class GitHubToolProvider(BaseMCPToolProvider):
    """MCP tool provider for GitHub API integration."""

    @property
    def server_name(self) -> str:
        return "github"

    def infer_permission(self, tool_name: str) -> ToolPermission:
        return infer_github_permission(tool_name)

    async def get_tools(
        self,
        token: Optional[str] = None,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
        client_manager: Optional[Any] = None,
    ) -> List[MCPToolWrapper]:
        """Retrieve GitHub tools from the MCP server, wrapped in MCPToolWrapper."""
        custom_configs = {}
        if token:
            custom_configs["github"] = get_github_config(token=token)

        return await super().get_tools(
            attempt_id=attempt_id,
            operation_id=operation_id,
            enable_db_logging=enable_db_logging,
            timeout_seconds=timeout_seconds,
            client_manager=client_manager,
            custom_configs=custom_configs if custom_configs else None,
        )


# Default singleton provider instance
github_provider = GitHubToolProvider()


def create_github_mcp_wrapper(
    mcp_tool: Any,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    permissions: Optional[ToolPermission] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    max_output_chars: Optional[int] = 4000,
    compress_output: bool = True,
) -> MCPToolWrapper:
    """Wrap a GitHub MCP tool instance into AgentForge's MCPToolWrapper."""
    return github_provider.wrap_tool(
        mcp_tool=mcp_tool,
        attempt_id=attempt_id,
        operation_id=operation_id,
        permissions=permissions,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        compress_output=compress_output,
    )


async def get_github_tools(
    token: Optional[str] = None,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    client_manager: Optional[Any] = None,
) -> List[MCPToolWrapper]:
    """Retrieve GitHub tools from the MCP server, wrapped in MCPToolWrapper."""
    return await github_provider.get_tools(
        token=token,
        attempt_id=attempt_id,
        operation_id=operation_id,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        client_manager=client_manager,
    )
