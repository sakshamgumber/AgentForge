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
]

from app.tools.duckduckgo import (
    create_duckduckgo_mcp_wrapper,
    get_duckduckgo_tools,
)

