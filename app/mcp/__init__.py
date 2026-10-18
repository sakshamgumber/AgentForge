"""MCP integration package for AgentForge."""

import sys
from app.mcp import configuration
from app.mcp.client_manager import MCPClientManager
from app.mcp.configuration import (
    get_context7_config,
    get_duckduckgo_config,
    get_filesystem_config,
    get_git_config,
    get_google_drive_config,
    get_notion_config,
    get_sequential_thinking_config,
)

# Alias plural form for compatibility
configurations = configuration
sys.modules.setdefault("app.mcp.configurations", configuration)

__all__ = [
    "MCPClientManager",
    "configuration",
    "configurations",
    "get_context7_config",
    "get_duckduckgo_config",
    "get_filesystem_config",
    "get_git_config",
    "get_google_drive_config",
    "get_notion_config",
    "get_sequential_thinking_config",
]
