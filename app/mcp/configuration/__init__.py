"""MCP server configurations package."""

from app.mcp.configuration.context7 import get_context7_config
from app.mcp.configuration.duckduckgo import get_duckduckgo_config
from app.mcp.configuration.filesystem import get_filesystem_config
from app.mcp.configuration.git import get_git_config
from app.mcp.configuration.github import get_github_config
from app.mcp.configuration.google_drive import get_google_drive_config
from app.mcp.configuration.notion import get_notion_config
from app.mcp.configuration.sequential_thinking import get_sequential_thinking_config

__all__ = [
    "get_context7_config",
    "get_duckduckgo_config",
    "get_filesystem_config",
    "get_git_config",
    "get_github_config",
    "get_google_drive_config",
    "get_notion_config",
    "get_sequential_thinking_config",
]
