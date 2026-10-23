"""Context7 MCP Tool & Direct API Integration for AgentForge.

Exposes Context7 library documentation and search tools strictly through MCP servers
and provides a direct lightweight Context7APIClient for programmatic documentation querying:
- Standardized BaseTool interface compatible with LangGraph and OpenAI function calling
- Role-based ToolPermission enforcement (READ)
- Direct Context7APIClient for resolving library IDs and querying up-to-date documentation
- PostgreSQL tool execution audit logging (tools table)
- attempt_id and operation_id tracing across agent steps
- Server-side execution timeouts and output compression
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.mcp.tool_wrapper import MCPToolWrapper

from app.tools.base_provider import BaseMCPToolProvider
from app.tools.enums import ToolPermission

logger = logging.getLogger(__name__)


class Context7APIClient:
    """Lightweight client for interacting directly with the Context7 MCP / HTTP API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("CONTEXT7_API_KEY") or os.getenv("CONTEXT7_TOKEN", "")
        self.base_url = (base_url or os.getenv("CONTEXT7_MCP_URL", "https://mcp.context7.com/mcp")).rstrip("/")
        self.timeout = timeout

    def _post_rpc(self, method: str, params: Dict[str, Any]) -> Any:
        """Execute a JSON-RPC request against the Context7 HTTP endpoint."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = resp.read().decode("utf-8")
                # Handle possible JSON-RPC or text response
                try:
                    res_json = json.loads(resp_data)
                    if "error" in res_json:
                        raise RuntimeError(f"Context7 API error: {res_json['error']}")
                    return res_json.get("result", res_json)
                except json.JSONDecodeError:
                    return resp_data
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error("Context7 HTTP request failed (%d): %s", e.code, err_body)
            raise RuntimeError(f"Context7 API request failed with HTTP {e.code}: {err_body}") from e
        except Exception as e:
            logger.error("Context7 request error: %s", e)
            raise RuntimeError(f"Failed to communicate with Context7 API: {e}") from e

    def resolve_library_id(self, query: str) -> Any:
        """Resolve a human-readable library or package name into a Context7 library ID (e.g. /tiangolo/fastapi)."""
        return self._post_rpc(
            method="tools/call",
            params={
                "name": "resolve-library-id",
                "arguments": {"query": query},
            },
        )

    async def a_resolve_library_id(self, query: str) -> Any:
        """Asynchronously resolve a human-readable library or package name."""
        return await asyncio.to_thread(self.resolve_library_id, query)

    def query_docs(self, library_id: str, query: str, language: Optional[str] = None) -> Any:
        """Query documentation context and code examples for a given library ID."""
        args: Dict[str, Any] = {
            "libraryId": library_id,
            "query": query,
        }
        if language:
            args["language"] = language

        return self._post_rpc(
            method="tools/call",
            params={
                "name": "query-docs",
                "arguments": args,
            },
        )

    async def a_query_docs(self, library_id: str, query: str, language: Optional[str] = None) -> Any:
        """Asynchronously query documentation context and code examples."""
        return await asyncio.to_thread(self.query_docs, library_id, query, language)


# Default singleton API client instance
context7_client = Context7APIClient()


def infer_context7_permission(tool_name: str) -> ToolPermission:
    """Infer ToolPermission based on Context7 action prefix.

    Context7 is predominantly a documentation search and retrieval provider (READ).
    """
    cleaned_name = tool_name.lower().replace("-", "_")
    if cleaned_name.startswith("context7_"):
        cleaned_name = cleaned_name[len("context7_"):]

    if any(cleaned_name.startswith(p) for p in ("delete", "remove", "destroy")):
        return ToolPermission.DESTRUCTIVE

    if any(cleaned_name.startswith(p) for p in ("create", "update", "set", "post", "write")):
        return ToolPermission.WRITE

    return ToolPermission.READ


class Context7ToolProvider(BaseMCPToolProvider):
    """MCP tool provider for Context7 library documentation retrieval."""

    @property
    def server_name(self) -> str:
        return "context7"

    def infer_permission(self, tool_name: str) -> ToolPermission:
        return infer_context7_permission(tool_name)

    async def get_tools(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
        client_manager: Optional[Any] = None,
    ) -> List[MCPToolWrapper]:
        """Retrieve Context7 tools from MCP server with custom credentials and error handling."""
        from app.mcp.configuration.context7 import get_context7_config

        custom_configs = {}
        if api_key or url:
            custom_configs["context7"] = get_context7_config(
                url=url,
                api_key=api_key,
            )

        return await super().get_tools(
            attempt_id=attempt_id,
            operation_id=operation_id,
            enable_db_logging=enable_db_logging,
            timeout_seconds=timeout_seconds,
            client_manager=client_manager,
            custom_configs=custom_configs if custom_configs else None,
        )


# Default singleton provider instance
context7_provider = Context7ToolProvider()


def create_context7_mcp_wrapper(
    mcp_tool: Any,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    permissions: Optional[ToolPermission] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    max_output_chars: Optional[int] = 4000,
    compress_output: bool = True,
) -> MCPToolWrapper:
    """Wrap a Context7 MCP tool instance into AgentForge's MCPToolWrapper."""
    return context7_provider.wrap_tool(
        mcp_tool=mcp_tool,
        attempt_id=attempt_id,
        operation_id=operation_id,
        permissions=permissions,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        compress_output=compress_output,
    )


async def get_context7_tools(
    api_key: Optional[str] = None,
    url: Optional[str] = None,
    attempt_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    enable_db_logging: bool = True,
    timeout_seconds: Optional[float] = 30.0,
    client_manager: Optional[Any] = None,
) -> List[MCPToolWrapper]:
    """Retrieve Context7 tools from the MCP server, wrapped in MCPToolWrapper."""
    return await context7_provider.get_tools(
        api_key=api_key,
        url=url,
        attempt_id=attempt_id,
        operation_id=operation_id,
        enable_db_logging=enable_db_logging,
        timeout_seconds=timeout_seconds,
        client_manager=client_manager,
    )
