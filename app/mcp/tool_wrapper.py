"""MCP Tool Wrapper connecting external MCP servers to AgentForge BaseTool and PostgreSQL tracing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional
import uuid

from app.tools.base import BaseTool, ExecutionContext, ToolStatus
from app.tools.enums import ToolPermission
from database.repository import (
    record_tool_execution_async,
    record_tool_execution_sync,
)

logger = logging.getLogger(__name__)


def _extract_parameters_from_mcp_tool(mcp_tool: Any) -> Dict[str, Any]:
    """Extract JSON Schema parameter dictionary from an MCP/LangChain tool."""
    if hasattr(mcp_tool, "args_schema") and mcp_tool.args_schema is not None:
        schema_cls = mcp_tool.args_schema
        if hasattr(schema_cls, "model_json_schema"):
            return schema_cls.model_json_schema()
        elif hasattr(schema_cls, "schema"):
            return schema_cls.schema()

    if hasattr(mcp_tool, "args") and isinstance(mcp_tool.args, dict):
        required = getattr(mcp_tool, "required", [])
        return {"type": "object", "properties": mcp_tool.args, "required": list(required)}

    return {"type": "object", "properties": {}}


class MCPToolWrapper(BaseTool):
    """Wraps an MCP server tool into the AgentForge BaseTool interface.
    
    Provides:
    - attempt_id and operation_id tracking for every MCP invocation
    - Automatic PostgreSQL audit logging into the 'tools' table
    - Server-side execution timeouts and output compression
    - ExecutionContext permission enforcement
    - LangGraph structured error recovery
    """

    def __init__(
        self,
        mcp_tool: Any,
        server_name: Optional[str] = None,
        attempt_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        enable_db_logging: bool = True,
        timeout_seconds: Optional[float] = 30.0,
        permissions: ToolPermission = ToolPermission.READ,
        max_output_chars: Optional[int] = 4000,
        compress_output: bool = True,
    ):
        self._mcp_tool = mcp_tool
        self.server_name = server_name or getattr(mcp_tool, "name", "mcp").split("_")[0]
        self.enable_db_logging = enable_db_logging

        tool_name = getattr(mcp_tool, "name", "mcp_tool")
        tool_desc = getattr(mcp_tool, "description", f"MCP Tool from {self.server_name} server")
        raw_schema = _extract_parameters_from_mcp_tool(mcp_tool)
        properties = raw_schema.get("properties", raw_schema) if isinstance(raw_schema, dict) else {}
        required_fields = raw_schema.get("required", []) if isinstance(raw_schema, dict) else []

        super().__init__(
            name=tool_name,
            description=tool_desc,
            parameters=properties,
            required=required_fields,
            additionalProperties=True,
            timeout_seconds=timeout_seconds,
            permissions=permissions,
            attempt_id=attempt_id,
            operation_id=operation_id,
            max_output_chars=max_output_chars,
            compress_output=compress_output,
        )

    def _resolve_trace_ids(self, context: Optional[ExecutionContext]) -> tuple[str, str]:
        """Resolve attempt_id and operation_id from tool state or ExecutionContext."""
        current_attempt = (
            self.attempt_id
            or (getattr(context, "attempt_id", None) if context else None)
            or f"att-{uuid.uuid4().hex[:12]}"
        )
        current_operation = (
            self.operation_id
            or (getattr(context, "operation_id", None) if context else None)
            or f"op-{uuid.uuid4().hex[:12]}"
        )
        self.attempt_id = current_attempt
        self.operation_id = current_operation
        return current_attempt, current_operation

    def _run(self, args: Dict[str, Any], context: Optional[ExecutionContext] = None) -> Any:
        """Synchronously execute the underlying MCP tool with DB audit logging."""
        attempt_id, operation_id = self._resolve_trace_ids(context)

        try:
            if hasattr(self._mcp_tool, "invoke"):
                result = self._mcp_tool.invoke(args)
            elif hasattr(self._mcp_tool, "run"):
                result = self._mcp_tool.run(args)
            elif callable(self._mcp_tool):
                result = self._mcp_tool(**args)
            else:
                raise AttributeError(f"MCP tool '{self.name}' has no callable invoke or run method")

            if self.enable_db_logging:
                record_tool_execution_sync(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS.value,
                    attempt_id=attempt_id,
                    operation_id=operation_id,
                    parameters=args,
                    result=result,
                )

            return result

        except Exception as e:
            if self.enable_db_logging:
                record_tool_execution_sync(
                    tool_name=self.name,
                    status=ToolStatus.FAILURE.value,
                    attempt_id=attempt_id,
                    operation_id=operation_id,
                    error=str(e),
                    parameters=args,
                )
            raise

    async def _arun(self, args: Dict[str, Any], context: Optional[ExecutionContext] = None) -> Any:
        """Asynchronously execute the underlying MCP tool with DB audit logging."""
        attempt_id, operation_id = self._resolve_trace_ids(context)

        try:
            if hasattr(self._mcp_tool, "ainvoke"):
                result = await self._mcp_tool.ainvoke(args)
            elif hasattr(self._mcp_tool, "arun"):
                result = await self._mcp_tool.arun(args)
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, self._run, args, context)

            if self.enable_db_logging:
                await record_tool_execution_async(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS.value,
                    attempt_id=attempt_id,
                    operation_id=operation_id,
                    parameters=args,
                    result=result,
                )

            return result

        except Exception as e:
            if self.enable_db_logging:
                await record_tool_execution_async(
                    tool_name=self.name,
                    status=ToolStatus.FAILURE.value,
                    attempt_id=attempt_id,
                    operation_id=operation_id,
                    error=str(e),
                    parameters=args,
                )
            raise
