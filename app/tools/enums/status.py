"""ToolStatus enum definition."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ToolStatus(str, Enum):
    """Status enum for tool execution lifecycle and outcomes.

    Four primary types:
    - SUCCESS: Tool executed successfully.
    - FAILURE: Tool execution failed due to error or parameter validation.
    - TIMEOUT: Tool execution exceeded server-enforced timeout.
    - PERMISSION_DENIED: Caller context lacked required permissions.
    """
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    @classmethod
    def _missing_(cls, value: object) -> Optional[ToolStatus]:
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper() or member.name.upper() == value.upper():
                    return member
        return None


# Convenient alias
Status = ToolStatus
