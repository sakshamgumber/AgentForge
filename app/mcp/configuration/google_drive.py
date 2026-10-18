"""Google Drive MCP server configuration."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def get_google_drive_config(
    url: Optional[str] = None,
    access_token: Optional[str] = None,
    credentials_path: Optional[str] = None,
    token_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Return MCP server configuration dictionary for Google Drive document search and access.

    Transport: Remote HTTP endpoint or local subprocess.
    Reference: https://developers.google.com/drive/api/guides/about-sdk
    """
    resolved_url = url or os.getenv("GOOGLE_DRIVE_MCP_URL", "https://drivemcp.googleapis.com/mcp/v1")
    resolved_token = access_token or os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN", "")

    headers: Dict[str, str] = {}
    if resolved_token:
        headers["Authorization"] = f"Bearer {resolved_token}"

    config: Dict[str, Any] = {
        "transport": "http",
        "url": resolved_url,
        "headers": headers,
    }

    # If local file-based credentials/token paths are configured
    cred_file = credentials_path or os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH")
    tok_file = token_path or os.getenv("GOOGLE_DRIVE_TOKEN_PATH")
    if cred_file or tok_file:
        config["metadata"] = {
            "credentials_path": cred_file,
            "token_path": tok_file,
        }

    return config
