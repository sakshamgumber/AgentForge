"""Filesystem MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def get_filesystem_config(
    allowed_dir: Optional[str] = None,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for local filesystem management.

    Transport: Local subprocess over stdio.
    Default uses npx -y @modelcontextprotocol/server-filesystem.
    Reference: https://github.com/modelcontextprotocol/servers
    """
    resolved_cmd = command or os.getenv("FILESYSTEM_MCP_COMMAND", "npx")
    resolved_dir = allowed_dir or os.getenv("FILESYSTEM_ALLOWED_DIR", os.getcwd())

    cmd_args = args if args is not None else [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        resolved_dir,
    ]

    return {
        "transport": "stdio",
        "command": resolved_cmd,
        "args": cmd_args,
    }
