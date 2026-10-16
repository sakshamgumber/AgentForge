"""DuckDuckGo Search MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def get_duckduckgo_config(
    command: Optional[str] = None,
    package: Optional[str] = None,
    args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for DuckDuckGo public web search.

    Transport: Local subprocess over stdio.
    Default uses uvx/duckduckgo-mcp-server.
    """
    resolved_cmd = command or os.getenv("DUCKDUCKGO_MCP_COMMAND", "uvx")
    resolved_pkg = package or os.getenv("DUCKDUCKGO_MCP_PACKAGE", "duckduckgo-mcp-server")

    cmd_args = args if args is not None else [resolved_pkg]

    return {
        "transport": "stdio",
        "command": resolved_cmd,
        "args": cmd_args,
    }
