"""Tool Exceptions integrated with LangGraph error handling."""

from __future__ import annotations

from typing import Any, Dict, Optional


class ToolError(Exception):
    """Base tool error."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error_type": self.__class__.__name__,
            "tool_name": self.tool_name,
            "message": self.message,
            "details": self.details,
        }


class ToolValidationError(ToolError):
    """Raised when parameters fail validation (missing required fields or additional properties)."""
    pass


class ToolPermissionError(ToolError):
    """Raised when caller lacks required ToolPermission."""
    pass


class ToolTimeoutError(ToolError):
    """Raised when execution exceeds timeout_seconds."""
    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails internally."""
    pass
