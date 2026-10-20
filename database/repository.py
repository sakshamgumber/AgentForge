"""Repository functions for logging tool executions to PostgreSQL."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from database.connection import (
    HAS_SQLALCHEMY,
    AsyncSessionLocal,
    SyncSessionLocal,
)
from database.models import ToolExecutionModel

logger = logging.getLogger(__name__)


def record_tool_execution_sync(
    tool_name: str,
    status: str,
    attempt_id: str,
    operation_id: str,
    error: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Any] = None,
) -> ToolExecutionModel:
    """Record a tool execution attempt synchronously in the database."""
    entry = ToolExecutionModel(
        tool_name=tool_name,
        status=status,
        attempt_id=attempt_id,
        operation_id=operation_id,
        error=error,
        parameters=parameters or {},
        result=result,
    )

    if HAS_SQLALCHEMY and SyncSessionLocal is not None:
        try:
            with SyncSessionLocal() as session:
                session.add(entry)
                session.commit()
                session.refresh(entry)
        except Exception as e:
            logger.warning("Could not persist tool execution to database (sync): %s", e)

    return entry


async def record_tool_execution_async(
    tool_name: str,
    status: str,
    attempt_id: str,
    operation_id: str,
    error: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Any] = None,
) -> ToolExecutionModel:
    """Record a tool execution attempt asynchronously in the database."""
    entry = ToolExecutionModel(
        tool_name=tool_name,
        status=status,
        attempt_id=attempt_id,
        operation_id=operation_id,
        error=error,
        parameters=parameters or {},
        result=result,
    )

    if HAS_SQLALCHEMY and AsyncSessionLocal is not None:
        try:
            async with AsyncSessionLocal() as session:
                session.add(entry)
                await session.commit()
                await session.refresh(entry)
        except Exception as e:
            logger.warning("Could not persist tool execution to database (async): %s", e)

    return entry
