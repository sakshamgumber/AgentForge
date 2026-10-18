"""Notion hosted MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def get_notion_config(
    url: Optional[str] = None,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for Notion workspace access.

    Transport: Remote HTTP endpoint.
    Reference: https://developers.notion.com/guides/mcp
    """
    resolved_url = url or os.getenv("NOTION_MCP_URL", "https://mcp.notion.com/mcp")
    resolved_token = access_token or os.getenv("NOTION_ACCESS_TOKEN", "")

    headers: Dict[str, str] = {}
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    return {
        "transport": "http",
        "url": resolved_url,
        "headers": headers,
    }
