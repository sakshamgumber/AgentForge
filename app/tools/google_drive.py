"""Google Drive MCP Tool integration for AgentForge.

Exposes Google Drive tools strictly through external MCP servers via AgentForge's BaseMCPToolProvider:
- Pre-execution permission verification before creating, writing, or deleting files
- Role-based ToolPermission enforcement (READ, WRITE, DESTRUCTIVE)
- Standardized BaseTool interface compatible with LangGraph and OpenAI function calling
- PostgreSQL tool execution audit logging (tools table)
- attempt_id and operation_id tracing across agent steps
- Server-side execution timeouts and output compression
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.mcp.tool_wrapper import MCPToolWrapper

from app.tools.base_provider import BaseMCPToolProvider
from app.tools.enums import ToolPermission

logger = logging.getLogger(__name__)


def infer_google_drive_permission(tool_name: str) -> ToolPermission:
    """Infer ToolPermission based on Google Drive action prefix.

    - READ: search, list, get, read, download, inspect
    - WRITE: create, upload, write, update, copy, move, rename, share
    - DESTRUCTIVE: delete, trash, remove, purge, destroy, unshare
    """
    cleaned_name = tool_name.lower()
    if cleaned_name.startswith("google_drive_"):
        cleaned_name = cleaned_name[len("google_drive_"):]
    elif cleaned_name.startswith("gdrive_"):
        cleaned_name = cleaned_name[len("gdrive_"):]

    if any(cleaned_name.startswith(p) for p in ("delete", "trash", "remove", "purge", "destroy", "unshare")):
        return ToolPermission.DESTRUCTIVE

    if any(cleaned_name.startswith(p) for p in ("create", "upload", "write", "update", "copy", "move", "rename", "share")):
        return ToolPermission.WRITE

    return ToolPermission.READ


class GoogleDriveToolProvider(BaseMCPToolProvider):
    """MCP tool provider for Google Drive integration with pre-execution permission guards."""

    @property
    def server_name(self) -> str:
        return "google_drive"

    def infer_permission(self, tool_name: str) -> ToolPermission:
        return infer_google_drive_permission(tool_name)

    async def get_tools(
        self,
        access_token: Optional[str] = None,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
        client_manager: Optional[Any] = None,
    ) -> List[MCPToolWrapper]:
        """Retrieve Google Drive tools from MCP server with custom credentials and error handling."""
        from app.mcp.configuration.google_drive import get_google_drive_config

        custom_configs = {}
        if any((access_token, credentials_path, token_path)):
            custom_configs["google_drive"] = get_google_drive_config(
                access_token=access_token,
                credentials_path=credentials_path,
                token_path=token_path,
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
google_drive_provider = GoogleDriveToolProvider()


def create_google_drive_mcp_wrapper(
    mcp_tool: Any,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    permissions: Optional[ToolPermission] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    max_output_chars: Optional[int] = 4000,
    compress_output: bool = True,
) -> MCPToolWrapper:
    """Wrap a Google Drive MCP tool instance into AgentForge's MCPToolWrapper."""
    return google_drive_provider.wrap_tool(
        mcp_tool=mcp_tool,
        attempt_id=attempt_id,
        operation_id=operation_id,
        permissions=permissions,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        compress_output=compress_output,
    )


async def get_google_drive_tools(
    access_token: Optional[str] = None,
    credentials_path: Optional[str] = None,
    token_path: Optional[str] = None,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    client_manager: Optional[Any] = None,
) -> List[MCPToolWrapper]:
    """Retrieve Google Drive tools from the MCP server, wrapped in MCPToolWrapper."""
    return await google_drive_provider.get_tools(
        access_token=access_token,
        credentials_path=credentials_path,
        token_path=token_path,
        attempt_id=attempt_id,
        operation_id=operation_id,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        client_manager=client_manager,
    )
