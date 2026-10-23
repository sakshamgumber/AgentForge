"""Tools package for AgentForge."""

from app.tools.base import (
    BaseTool,
    ToolPermission,
    ToolStatus,
    Status,
    ExecutionContext,
    ToolError,
    ToolValidationError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolExecutionError,
)

from app.tools.compression import (
    compress_tool_output,
    compress_json,
    compress_string,
    prune_empty_fields,
)

__all__ = [
    "BaseTool",
    "ToolPermission",
    "ToolStatus",
    "Status",
    "ExecutionContext",
    "ToolError",
    "ToolValidationError",
    "ToolPermissionError",
    "ToolTimeoutError",
    "ToolExecutionError",
    "compress_tool_output",
    "compress_json",
    "compress_string",
    "prune_empty_fields",
    "create_duckduckgo_mcp_wrapper",
    "get_duckduckgo_tools",
    "create_github_mcp_wrapper",
    "get_github_tools",
    "infer_github_permission",
    "create_google_drive_mcp_wrapper",
    "get_google_drive_tools",
    "infer_google_drive_permission",
    "create_notion_mcp_wrapper",
    "get_notion_tools",
    "infer_notion_permission",
    "create_context7_mcp_wrapper",
    "get_context7_tools",
    "infer_context7_permission",
    "Context7APIClient",
    "context7_client",
    "BaseMCPToolProvider",
]

from app.tools.base_provider import BaseMCPToolProvider

from app.tools.context7 import (
    Context7APIClient,
    context7_client,
    create_context7_mcp_wrapper,
    get_context7_tools,
    infer_context7_permission,
)
from app.tools.duckduckgo import (
    create_duckduckgo_mcp_wrapper,
    get_duckduckgo_tools,
)
from app.tools.github import (
    create_github_mcp_wrapper,
    get_github_tools,
    infer_github_permission,
)
from app.tools.google_drive import (
    create_google_drive_mcp_wrapper,
    get_google_drive_tools,
    infer_google_drive_permission,
)
from app.tools.notion import (
    create_notion_mcp_wrapper,
    get_notion_tools,
    infer_notion_permission,
)

