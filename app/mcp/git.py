"""Git repository MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def get_git_config(
    repo_path: Optional[str] = None,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for Git repository inspection.

    Transport: Local subprocess over stdio.
    Default uses uvx mcp-server-git or python -m mcp_server_git.
    Reference: https://github.com/modelcontextprotocol/servers
    """
    resolved_cmd = command or os.getenv("GIT_MCP_COMMAND", "uvx")
    resolved_repo = repo_path or os.getenv("GIT_REPOSITORY_PATH", os.getcwd())

    cmd_args = args if args is not None else [
        "mcp-server-git",
        "--repository",
        resolved_repo,
    ]

    return {
        "transport": "stdio",
        "command": resolved_cmd,
        "args": cmd_args,
    }
