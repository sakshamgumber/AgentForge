"""BaseTool interface following the AgentForge tool specification."""

from __future__ import annotations

import asyncio
import concurrent.futures
from abc import ABC, abstractmethod
from enum import Enum
import inspect
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Permissions & Execution Context
# ---------------------------------------------------------------------------

from app.tools.enums import ToolPermission, ToolStatus, Status


class ExecutionContext(BaseModel):
    """Context of the caller to verify permissions before tool execution."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    permissions: Set[ToolPermission] = Field(default_factory=lambda: {ToolPermission.READ})
    is_admin: bool = False

    def has_permission(self, permission: ToolPermission) -> bool:
        if self.is_admin:
            return True
        return permission in self.permissions


from app.tools.compression import compress_tool_output
from app.tools.error import (
    ToolError,
    ToolValidationError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolExecutionError,
)


# ---------------------------------------------------------------------------
# BaseTool Interface
# ---------------------------------------------------------------------------

class BaseTool(ABC):
    """Base interface for all tools.
    
    Fields:
    - name: String attribute.
    - description: Purpose, intended use, and limitations for LLMs.
    - parameters: Compliant JSON Schema dictionary containing typed property definitions.
    - required: List of required parameter names; enforced during validation.
    - additionalProperties: Defaults to False; rejects unknown arguments during execution.
    - timeout_seconds: Server-side execution timeout enforced via ThreadPoolExecutor / asyncio.
                       Exposed to LLM only if expose_timeout_to_model=True.
    - permissions: ToolPermission (READ, WRITE, DESTRUCTIVE, ADMIN) verified against ExecutionContext.
    - idempotent: Boolean flag indicating whether repeating the call is safe without side effects.
    - status: ToolStatus enum indicating execution outcome (SUCCESS, FAILURE, TIMEOUT, PERMISSION_DENIED).
    - max_output_chars: Maximum characters allowed in tool output before compression/truncation is applied.
    - compress_output: Boolean flag enabling automatic JSON/text output compression.
    """

    name: str
    description: str
    parameters: Dict[str, Any] = {}
    required: List[str] = []
    additionalProperties: bool = False
    timeout_seconds: Optional[float] = 30.0
    expose_timeout_to_model: bool = False
    permissions: ToolPermission = ToolPermission.READ
    idempotent: bool = False
    status: ToolStatus = ToolStatus.SUCCESS
    max_output_chars: Optional[int] = 4000
    compress_output: bool = True

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        required: Optional[List[str]] = None,
        additionalProperties: Optional[bool] = None,
        timeout_seconds: Optional[float] = None,
        expose_timeout_to_model: Optional[bool] = None,
        permissions: Optional[ToolPermission] = None,
        idempotent: Optional[bool] = None,
        status: Optional[ToolStatus] = None,
        max_output_chars: Optional[int] = None,
        compress_output: Optional[bool] = None,
    ):
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if parameters is not None:
            self.parameters = parameters
        if required is not None:
            self.required = required
        if additionalProperties is not None:
            self.additionalProperties = additionalProperties
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds
        if expose_timeout_to_model is not None:
            self.expose_timeout_to_model = expose_timeout_to_model
        if permissions is not None:
            self.permissions = permissions
        if idempotent is not None:
            self.idempotent = idempotent
        if status is not None:
            self.status = status if isinstance(status, ToolStatus) else ToolStatus(status)
        if max_output_chars is not None:
            self.max_output_chars = max_output_chars
        if compress_output is not None:
            self.compress_output = compress_output

        self._validate_interface()

    def _validate_interface(self) -> None:
        """Validate tool schema definition on initialization."""
        # 1. Validate name: non-empty string
        if not hasattr(self, "name") or not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(f"Tool 'name' must be a non-empty string in {self.__class__.__name__}")

        # 2. Validate description: non-empty string (or fallback to docstring)
        if not hasattr(self, "description") or not isinstance(self.description, str) or not self.description.strip():
            doc = inspect.getdoc(self.__class__)
            if doc:
                self.description = doc
            else:
                raise ValueError(f"Tool 'description' must be non-empty in {self.__class__.__name__}")

        # 3. Validate parameters: compliant JSON Schema dictionary
        if not hasattr(self, "parameters") or not isinstance(self.parameters, dict):
            self.parameters = {}

        # 4. Validate required: list of required fields present in parameters
        if not hasattr(self, "required") or not isinstance(self.required, list):
            self.required = []
        for req in self.required:
            if req not in self.parameters:
                raise ValueError(f"Required parameter '{req}' not found in parameters schema for tool '{self.name}'")

        # 5. Validate additionalProperties: boolean default False
        if not isinstance(self.additionalProperties, bool):
            raise ValueError(f"'additionalProperties' must be a boolean in tool '{self.name}'")

        # 6. Validate timeout_seconds
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError(f"'timeout_seconds' must be positive in tool '{self.name}'")

        # 7. Validate permissions
        if not isinstance(self.permissions, ToolPermission):
            raise ValueError(f"'permissions' must be a ToolPermission enum in tool '{self.name}'")

        # 8. Validate idempotent
        if not isinstance(self.idempotent, bool):
            raise ValueError(f"'idempotent' must be a boolean in tool '{self.name}'")

        # 9. Validate status
        if not isinstance(self.status, ToolStatus):
            raise ValueError(f"'status' must be an instance of ToolStatus in tool '{self.name}'")

    def check_permissions(self, context: Optional[ExecutionContext] = None) -> None:
        """Verify caller's ExecutionContext has the required ToolPermission outside the LLM."""
        if context is None:
            if self.permissions != ToolPermission.READ:
                raise ToolPermissionError(
                    f"ExecutionContext required for tool '{self.name}' with permission '{self.permissions.value}'",
                    tool_name=self.name,
                    details={"required_permission": self.permissions.value},
                )
            return

        if not context.has_permission(self.permissions):
            raise ToolPermissionError(
                f"Permission denied: tool '{self.name}' requires '{self.permissions.value}'",
                tool_name=self.name,
                details={
                    "required_permission": self.permissions.value,
                    "granted_permissions": [p.value for p in context.permissions],
                },
            )

    def validate_parameters(self, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate input arguments against required fields and additionalProperties."""
        args_dict = dict(args) if args is not None else {}

        # Reject unknown arguments if additionalProperties is False
        if not self.additionalProperties:
            allowed_keys = set(self.parameters.keys())
            if self.expose_timeout_to_model:
                allowed_keys.add("timeout_seconds")
            extra = set(args_dict.keys()) - allowed_keys
            if extra:
                raise ToolValidationError(
                    f"Tool '{self.name}' does not allow additional properties: {sorted(list(extra))}",
                    tool_name=self.name,
                    details={"unexpected_keys": sorted(list(extra)), "allowed_keys": sorted(list(allowed_keys))},
                )

        # Enforce explicitly required parameters
        missing = [req for req in self.required if req not in args_dict or args_dict[req] is None]
        if missing:
            raise ToolValidationError(
                f"Tool '{self.name}' missing required parameter(s): {missing}",
                tool_name=self.name,
                details={"missing": missing, "required": self.required},
            )

        return args_dict

    def to_schema(self, expose_timeout: Optional[bool] = None) -> Dict[str, Any]:
        """Generate compliant JSON Schema for LLM tool/function calling."""
        expose = self.expose_timeout_to_model if expose_timeout is None else expose_timeout
        props = dict(self.parameters)

        if expose and "timeout_seconds" not in props:
            props["timeout_seconds"] = {
                "type": "number",
                "description": "Server execution timeout in seconds.",
                "default": self.timeout_seconds,
            }

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": list(self.required),
                    "additionalProperties": self.additionalProperties,
                },
            },
        }

    def compress_result(self, result: Any) -> Any:
        """Compress tool output if compress_output is enabled and max_output_chars is set."""
        if self.compress_output and self.max_output_chars is not None and self.max_output_chars > 0:
            return compress_tool_output(result, max_chars=self.max_output_chars)
        return result

    def execute(self, args: Optional[Dict[str, Any]] = None, context: Optional[ExecutionContext] = None) -> Any:
        """Execute tool synchronously with permission checks, parameter validation, timeout, and output compression."""
        try:
            self.check_permissions(context)
        except ToolPermissionError:
            self.status = ToolStatus.PERMISSION_DENIED
            raise

        try:
            valid_args = self.validate_parameters(args)
        except ToolValidationError:
            self.status = ToolStatus.FAILURE
            raise

        timeout = self.timeout_seconds
        if self.expose_timeout_to_model and args and "timeout_seconds" in args:
            timeout = float(args["timeout_seconds"])

        if timeout is not None and timeout > 0:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._run, valid_args, context)
                try:
                    raw_result = future.result(timeout=timeout)
                    result = self.compress_result(raw_result)
                    self.status = ToolStatus.SUCCESS
                    return result
                except concurrent.futures.TimeoutError as te:
                    self.status = ToolStatus.TIMEOUT
                    raise ToolTimeoutError(
                        f"Tool '{self.name}' timed out after {timeout} seconds",
                        tool_name=self.name,
                        details={"timeout_seconds": timeout},
                    ) from te
                except Exception as e:
                    self.status = ToolStatus.FAILURE
                    if isinstance(e, ToolError):
                        raise
                    raise ToolExecutionError(
                        f"Execution failed for tool '{self.name}': {str(e)}",
                        tool_name=self.name,
                    ) from e
        else:
            try:
                raw_result = self._run(valid_args, context)
                result = self.compress_result(raw_result)
                self.status = ToolStatus.SUCCESS
                return result
            except Exception as e:
                self.status = ToolStatus.FAILURE
                if isinstance(e, ToolError):
                    raise
                raise ToolExecutionError(
                    f"Execution failed for tool '{self.name}': {str(e)}",
                    tool_name=self.name,
                ) from e

    async def aexecute(self, args: Optional[Dict[str, Any]] = None, context: Optional[ExecutionContext] = None) -> Any:
        """Execute tool asynchronously with permission checks, parameter validation, timeout, and output compression."""
        try:
            self.check_permissions(context)
        except ToolPermissionError:
            self.status = ToolStatus.PERMISSION_DENIED
            raise

        try:
            valid_args = self.validate_parameters(args)
        except ToolValidationError:
            self.status = ToolStatus.FAILURE
            raise

        timeout = self.timeout_seconds
        if self.expose_timeout_to_model and args and "timeout_seconds" in args:
            timeout = float(args["timeout_seconds"])

        coro = self._arun(valid_args, context)
        if timeout is not None and timeout > 0:
            try:
                raw_result = await asyncio.wait_for(coro, timeout=timeout)
                result = self.compress_result(raw_result)
                self.status = ToolStatus.SUCCESS
                return result
            except asyncio.TimeoutError as te:
                self.status = ToolStatus.TIMEOUT
                raise ToolTimeoutError(
                    f"Tool '{self.name}' timed out after {timeout} seconds",
                    tool_name=self.name,
                    details={"timeout_seconds": timeout},
                ) from te
            except Exception as e:
                self.status = ToolStatus.FAILURE
                if isinstance(e, ToolError):
                    raise
                raise ToolExecutionError(
                    f"Execution failed for tool '{self.name}': {str(e)}",
                    tool_name=self.name,
                ) from e
        else:
            try:
                raw_result = await coro
                result = self.compress_result(raw_result)
                self.status = ToolStatus.SUCCESS
                return result
            except Exception as e:
                self.status = ToolStatus.FAILURE
                if isinstance(e, ToolError):
                    raise
                raise ToolExecutionError(
                    f"Execution failed for tool '{self.name}': {str(e)}",
                    tool_name=self.name,
                ) from e

    # Aliases for LangChain/LangGraph conventions
    def run(self, args: Optional[Dict[str, Any]] = None, context: Optional[ExecutionContext] = None) -> Any:
        return self.execute(args, context=context)

    async def arun(self, args: Optional[Dict[str, Any]] = None, context: Optional[ExecutionContext] = None) -> Any:
        return await self.aexecute(args, context=context)

    # LangGraph Error Handler integration
    def handle_tool_error(self, error: Exception) -> Dict[str, Any]:
        """Convert errors into structured LangGraph error responses for agent recovery."""
        if isinstance(error, ToolPermissionError):
            status = ToolStatus.PERMISSION_DENIED
        elif isinstance(error, ToolTimeoutError):
            status = ToolStatus.TIMEOUT
        else:
            status = ToolStatus.FAILURE

        self.status = status
        error_type = error.__class__.__name__
        message = str(error)
        details = getattr(error, "details", {})
        return {
            "status": status.value,
            "tool_name": self.name,
            "error_type": error_type,
            "message": message,
            "details": details,
            "recoverable": isinstance(error, (ToolValidationError, ToolTimeoutError)),
        }

    @abstractmethod
    def _run(self, args: Dict[str, Any], context: Optional[ExecutionContext] = None) -> Any:
        """Internal synchronous execution."""
        raise NotImplementedError

    async def _arun(self, args: Dict[str, Any], context: Optional[ExecutionContext] = None) -> Any:
        """Internal asynchronous execution."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run, args, context)
