"""Context7 MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def get_context7_config(
    api_key: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for Context7 documentation lookup.

    Transport: HTTP remote endpoint.
    Reference: https://context7.com/docs/resources/all-clients
    """
    resolved_api_key = api_key or os.getenv("CONTEXT7_API_KEY", "")
    resolved_url = url or os.getenv("CONTEXT7_MCP_URL", "https://mcp.context7.com/mcp")

    headers: Dict[str, str] = {}
    if resolved_api_key:
        headers["Authorization"] = f"Bearer {resolved_api_key}"

    return {
        "transport": "http",
        "url": resolved_url,
        "headers": headers,
    }
