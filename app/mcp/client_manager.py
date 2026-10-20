"""MCP Client Manager for connecting and managing multiple MCP servers using langchain-mcp-adapters."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from app.mcp.configuration import (
    get_context7_config,
    get_duckduckgo_config,
    get_filesystem_config,
    get_git_config,
    get_google_drive_config,
    get_notion_config,
    get_sequential_thinking_config,
)


logger = logging.getLogger(__name__)

# Try importing official MultiServerMCPClient from langchain-mcp-adapters
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    HAS_LANGCHAIN_MCP = True
except ImportError:
    MultiServerMCPClient = None  # type: ignore
    HAS_LANGCHAIN_MCP = False


class FallbackMultiServerMCPClient:
    """Fallback client when langchain-mcp-adapters is not yet installed."""

    def __init__(self, servers: Dict[str, Dict[str, Any]], tool_name_prefix: bool = True):
        self.servers = servers
        self.tool_name_prefix = tool_name_prefix

    async def get_tools(self) -> List[Any]:
        logger.warning(
            "langchain-mcp-adapters is not installed. Run `pip install langchain-mcp-adapters` to connect to live MCP servers."
        )
        return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MCPClientManager:
    """Manager for connecting to multiple MCP servers and providing tools to LangGraph agents.

    Supported servers:
    - context7: Documentation retrieval
    - duckduckgo: Public web search
    - google_drive: Google Drive document access
    - notion: Notion workspace access
    - filesystem: Local project filesystem
    - git: Git repository inspection
    - sequential_thinking: Complex multi-step reasoning
    """

    SUPPORTED_SERVERS = {
        "context7",
        "duckduckgo",
        "google_drive",
        "notion",
        "filesystem",
        "git",
        "sequential_thinking",
    }

    def __init__(
        self,
        enabled_servers: Optional[Sequence[str]] = None,
        custom_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        tool_name_prefix: bool = True,
    ):
        """Initialize MCPClientManager.

        Args:
            enabled_servers: List of server identifiers to enable. Defaults to all supported servers.
            custom_configs: Optional dictionary to override default server configurations.
            tool_name_prefix: Whether to prefix tool names with server name to avoid collisions.
        """
        self.enabled_servers = set(enabled_servers) if enabled_servers else set(self.SUPPORTED_SERVERS)
        self.custom_configs = custom_configs or {}
        self.tool_name_prefix = tool_name_prefix
        self._client: Optional[Any] = None

    def get_server_configs(self) -> Dict[str, Dict[str, Any]]:
        """Build dictionary of server configurations for all enabled servers."""
        configs: Dict[str, Dict[str, Any]] = {}

        config_builders = {
            "context7": get_context7_config,
            "duckduckgo": get_duckduckgo_config,
            "google_drive": get_google_drive_config,
            "notion": get_notion_config,
            "filesystem": get_filesystem_config,
            "git": get_git_config,
            "sequential_thinking": get_sequential_thinking_config,
        }

        for server_name in self.enabled_servers:
            if server_name in self.custom_configs:
                configs[server_name] = self.custom_configs[server_name]
            elif server_name in config_builders:
                configs[server_name] = config_builders[server_name]()
            else:
                logger.warning("Unknown server '%s' requested in enabled_servers", server_name)

        return configs

    def build_client(self) -> Any:
        """Construct the underlying MultiServerMCPClient instance."""
        configs = self.get_server_configs()

        if HAS_LANGCHAIN_MCP and MultiServerMCPClient is not None:
            return MultiServerMCPClient(
                configs,
                tool_name_prefix=self.tool_name_prefix,
            )
        else:
            return FallbackMultiServerMCPClient(
                configs,
                tool_name_prefix=self.tool_name_prefix,
            )

    def get_client(self) -> Any:
        """Return or lazily create the active MCP client instance."""
        if self._client is None:
            self._client = self.build_client()
        return self._client

    async def get_tools(self) -> List[Any]:
        """Discover and return all tools available from connected MCP servers."""
        client = self.get_client()
        return await client.get_tools()

    async def get_wrapped_tools(
        self,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
    ) -> List[Any]:
        """Discover and return all MCP tools wrapped into AgentForge BaseTool with attempt_id and DB tracing."""
        from app.mcp.tool_wrapper import MCPToolWrapper

        raw_tools = await self.get_tools()
        wrapped_tools = []
        for tool in raw_tools:
            wrapped = MCPToolWrapper(
                mcp_tool=tool,
                attempt_id=attempt_id,
                operation_id=operation_id,
                enable_db_logging=enable_db_logging,
                timeout_seconds=timeout_seconds,
            )
            wrapped_tools.append(wrapped)
        return wrapped_tools


    async def close(self) -> None:
        """Close client connections gracefully."""
        if self._client is not None:
            if hasattr(self._client, "close"):
                await self._client.close()
            elif hasattr(self._client, "__aexit__"):
                await self._client.__aexit__(None, None, None)
            self._client = None

    async def __aenter__(self) -> MCPClientManager:
        self.get_client()
        if hasattr(self._client, "__aenter__"):
            await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
