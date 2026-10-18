"""Sequential Thinking MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def get_sequential_thinking_config(
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for structured sequential reasoning.

    Transport: Local subprocess over stdio.
    Default uses npx -y @modelcontextprotocol/server-sequential-thinking.
    Reference: https://github.com/modelcontextprotocol/servers
    """
    resolved_cmd = command or os.getenv("SEQUENTIAL_THINKING_MCP_COMMAND", "npx")

    cmd_args = args if args is not None else [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking",
    ]

    return {
        "transport": "stdio",
        "command": resolved_cmd,
        "args": cmd_args,
    }
