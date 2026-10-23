"""GitHub MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def get_github_config(
    token: Optional[str] = None,
    command: Optional[str] = None,
    args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for GitHub integration.

    Transport: Local subprocess over stdio.
    Default uses npx -y @modelcontextprotocol/server-github.
    Reference: https://github.com/modelcontextprotocol/servers/tree/main/src/github
    """
    resolved_cmd = command or os.getenv("GITHUB_MCP_COMMAND", "npx")
    resolved_pkg = os.getenv("GITHUB_MCP_PACKAGE", "@modelcontextprotocol/server-github")
    resolved_token = token or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN", "")

    cmd_args = args if args is not None else ["-y", resolved_pkg]

    cmd_env: Dict[str, str] = dict(os.environ)
    if resolved_token:
        cmd_env["GITHUB_PERSONAL_ACCESS_TOKEN"] = resolved_token
    if env:
        cmd_env.update(env)

    return {
        "transport": "stdio",
        "command": resolved_cmd,
        "args": cmd_args,
        "env": cmd_env,
    }
