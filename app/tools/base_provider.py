"""Abstract base class for server-specific MCP tool providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

from app.mcp.tool_wrapper import MCPToolWrapper
from app.tools.enums import ToolPermission
from app.mcp.client_manager import MCPClientManager

logger = logging.getLogger(__name__)


class BaseMCPToolProvider(ABC):
    """Abstract interface for server-specific MCP tool discovery and wrapping.

    Subclasses define `server_name` and optionally override `infer_permission`
    or credential/configuration resolution.
    """

    @property
    @abstractmethod
    def server_name(self) -> str:
        """The identifier of the MCP server (e.g. 'duckduckgo', 'github')."""
        ...

    def infer_permission(self, tool_name: str) -> ToolPermission:
        """Infer default permission for a given tool name.

        Defaults to ToolPermission.READ unless overridden by subclass.
        """
        return ToolPermission.READ

    def wrap_tool(
        self,
        mcp_tool: Any,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        permissions: Optional[ToolPermission] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
        max_output_chars: Optional[int] = 4000,
        compress_output: bool = True,
    ) -> MCPToolWrapper:
        """Wrap an underlying MCP tool instance into AgentForge's MCPToolWrapper.

        Args:
            mcp_tool: Underlying MCP or LangChain tool.
            attempt_id: Execution attempt ID for PostgreSQL tracking.
            operation_id: Operation workflow ID for PostgreSQL tracking.
            permissions: Explicit ToolPermission. If None, auto-inferred via infer_permission().
            enable_db_logging: Whether to record execution into PostgreSQL tools table.
            timeout_seconds: Server execution timeout.
            max_output_chars: Maximum output characters before compression/truncation.
            compress_output: Whether to prune and compress output.

        Returns:
            Configured MCPToolWrapper ready for agent binding or LangGraph execution.
        """
        if mcp_tool is None:
            raise ValueError(f"mcp_tool must be provided to {self.__class__.__name__}.wrap_tool")

        tool_name = getattr(mcp_tool, "name", f"{self.server_name}_tool")
        resolved_permission = permissions or self.infer_permission(tool_name)

        return MCPToolWrapper(
            mcp_tool=mcp_tool,
            server_name=self.server_name,
            attempt_id=attempt_id,
            operation_id=operation_id,
            enable_db_logging=enable_db_logging,
            timeout_seconds=timeout_seconds,
            permissions=resolved_permission,
            max_output_chars=max_output_chars,
            compress_output=compress_output,
        )

    async def get_tools(
        self,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
        client_manager: Optional[Any] = None,
        custom_configs: Optional[Dict[str, Any]] = None,
    ) -> List[MCPToolWrapper]:
        """Connect to the MCP server, discover available tools, and wrap them.

        Args:
            attempt_id: Execution attempt ID.
            operation_id: Operation ID.
            enable_db_logging: Enable PostgreSQL audit logging.
            timeout_seconds: Timeout in seconds.
            client_manager: Optional existing MCPClientManager instance.
            custom_configs: Optional custom server configs dictionary.

        Returns:
            List of wrapped MCP tools.

        Raises:
            RuntimeError: If connecting to the MCP server fails or no tools are returned.
        """

        manager = client_manager or MCPClientManager(
            enabled_servers=[self.server_name],
            custom_configs=custom_configs,
            tool_name_prefix=True,
        )

        try:
            # Check if client manager has already wrapped server tools
            if hasattr(manager, "get_server_tools"):
                tools = await manager.get_server_tools(
                    server_name=self.server_name,
                    attempt_id=attempt_id,
                    operation_id=operation_id,
                    enable_db_logging=enable_db_logging,
                    timeout_seconds=timeout_seconds,
                )
                if tools:
                    return tools

            raw_tools = await manager.get_tools()
        except Exception as e:
            logger.error("Failed to connect to %s MCP server: %s", self.server_name, e)
            raise RuntimeError(f"Could not connect to {self.server_name} MCP server: {e}") from e

        if not raw_tools:
            raise RuntimeError(
                f"{self.server_name.capitalize()} MCP server returned no tools. "
                f"Ensure the server package is installed and accessible."
            )

        wrapped_tools: List[MCPToolWrapper] = []
        for tool in raw_tools:
            wrapped = self.wrap_tool(
                mcp_tool=tool,
                attempt_id=attempt_id,
                operation_id=operation_id,
                enable_db_logging=enable_db_logging,
                timeout_seconds=timeout_seconds,
            )
            wrapped_tools.append(wrapped)

        return wrapped_tools
