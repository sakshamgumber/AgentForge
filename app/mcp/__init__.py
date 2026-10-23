"""MCP integration package for AgentForge."""

import sys
from app.mcp import configuration
from app.mcp.client_manager import MCPClientManager
from app.mcp.tool_wrapper import MCPToolWrapper
from app.mcp.configuration import (

    get_context7_config,
    get_duckduckgo_config,
    get_filesystem_config,
    get_git_config,
    get_github_config,
    get_google_drive_config,
    get_notion_config,
    get_sequential_thinking_config,
)

# Alias plural form for compatibility
configurations = configuration
sys.modules.setdefault("app.mcp.configurations", configuration)

__all__ = [
    "MCPClientManager",
    "MCPToolWrapper",
    "configuration",

    "configurations",
    "get_context7_config",
    "get_duckduckgo_config",
    "get_filesystem_config",
    "get_git_config",
    "get_github_config",
    "get_google_drive_config",
    "get_notion_config",
    "get_sequential_thinking_config",
    "create_duckduckgo_mcp_wrapper",
    "get_duckduckgo_tools",
    "create_github_mcp_wrapper",
    "get_github_tools",
    "create_google_drive_mcp_wrapper",
    "get_google_drive_tools",
]


def __getattr__(name: str):
    if name in ("create_duckduckgo_mcp_wrapper", "get_duckduckgo_tools"):
        from app.tools.duckduckgo import create_duckduckgo_mcp_wrapper, get_duckduckgo_tools
        return locals()[name]
    if name in ("create_github_mcp_wrapper", "get_github_tools"):
        from app.tools.github import create_github_mcp_wrapper, get_github_tools
        return locals()[name]
    if name in ("create_google_drive_mcp_wrapper", "get_google_drive_tools"):
        from app.tools.google_drive import create_google_drive_mcp_wrapper, get_google_drive_tools
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
