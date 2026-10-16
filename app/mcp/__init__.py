"""MCP integration package for AgentForge."""

from app.mcp.client_manager import MCPClientManager
from app.mcp.context7 import get_context7_config
from app.mcp.duckduckgo import get_duckduckgo_config
from app.mcp.filesystem import get_filesystem_config
from app.mcp.git import get_git_config
from app.mcp.google_drive import get_google_drive_config
from app.mcp.notion import get_notion_config
from app.mcp.sequential_thinking import get_sequential_thinking_config

__all__ = [
    "MCPClientManager",
    "get_context7_config",
    "get_duckduckgo_config",
    "get_filesystem_config",
    "get_git_config",
    "get_google_drive_config",
    "get_notion_config",
    "get_sequential_thinking_config",
]
