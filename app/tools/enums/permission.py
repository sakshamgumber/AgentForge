"""ToolPermission enum definition."""

from enum import Enum


class ToolPermission(str, Enum):
    """Permissions for tool execution, enforced outside the LLM.
    
    Hierarchy / Categories:
    - READ: Non-mutating read, query, search, or inspect operations.
    - WRITE: Mutating operations such as creating or updating data.
    - DESTRUCTIVE: Permanent deletions, truncations, or drops.
    - ADMIN: Administrative configuration, role assignment, system-level modifications.
    """
    READ = "READ"
    WRITE = "WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    ADMIN = "ADMIN"
