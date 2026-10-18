"""Database models for AgentForge tool execution tracking."""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional
import uuid

from database.connection import HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, DateTime, String, Text, func
    from sqlalchemy.dialects.postgresql import JSONB, UUID
    from sqlalchemy.orm import declarative_base

    from database.connection import Base

    class ToolExecutionModel(Base):
        """PostgreSQL table schema for tools tracking."""

        __tablename__ = "tools"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        tool_name = Column(String(255), nullable=False, index=True)
        status = Column(String(50), nullable=False, default="PENDING", index=True)
        error = Column(Text, nullable=True)
        attempt_id = Column(String(100), nullable=False, index=True)
        operation_id = Column(String(100), nullable=False, index=True)
        parameters = Column(JSONB, nullable=True, default=dict)
        result = Column(JSONB, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

        # Aliases for camelCase naming
        @property
        def attempId(self) -> str:
            return self.attempt_id

        @attempId.setter
        def attempId(self, value: str) -> None:
            self.attempt_id = value

        @property
        def operationId(self) -> str:
            return self.operation_id

        @operationId.setter
        def operationId(self, value: str) -> None:
            self.operation_id = value

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": str(self.id) if self.id else None,
                "tool_name": self.tool_name,
                "status": self.status,
                "error": self.error,
                "attempt_id": self.attempt_id,
                "attempId": self.attempt_id,
                "operation_id": self.operation_id,
                "operationId": self.operation_id,
                "parameters": self.parameters,
                "result": self.result,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }

else:
    class ToolExecutionModel:  # type: ignore
        """Fallback lightweight model when SQLAlchemy is not installed."""

        def __init__(
            self,
            tool_name: str,
            status: str,
            attempt_id: str,
            operation_id: str,
            error: Optional[str] = None,
            parameters: Optional[Dict[str, Any]] = None,
            result: Optional[Any] = None,
            id: Optional[str] = None,
        ):
            self.id = id or str(uuid.uuid4())
            self.tool_name = tool_name
            self.status = status
            self.error = error
            self.attempt_id = attempt_id
            self.attempId = attempt_id
            self.operation_id = operation_id
            self.operationId = operation_id
            self.parameters = parameters or {}
            self.result = result
            self.created_at = datetime.datetime.now(datetime.timezone.utc)
            self.updated_at = datetime.datetime.now(datetime.timezone.utc)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "tool_name": self.tool_name,
                "status": self.status,
                "error": self.error,
                "attempt_id": self.attempt_id,
                "attempId": self.attempt_id,
                "operation_id": self.operation_id,
                "operationId": self.operation_id,
                "parameters": self.parameters,
                "result": self.result,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
            }


# Convenient alias
Tool = ToolExecutionModel
ToolModel = ToolExecutionModel
