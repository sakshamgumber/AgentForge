"""Unit tests for Google Drive MCP tool integration with MCPToolWrapper and permission guards."""

import pytest
from app.tools.base import ExecutionContext, ToolStatus, ToolPermissionError, ToolValidationError
from app.tools.enums import ToolPermission
from app.tools.google_drive import (
    create_google_drive_mcp_wrapper,
    get_google_drive_tools,
    infer_google_drive_permission,
)
from app.tools.langgraph_adapter import LangGraphToolNode


class MockGoogleDriveMCPTool:
    """Mock MCP tool mimicking a tool returned from Google Drive MCP server."""

    def __init__(self, name="google_drive_create_file", result=None):
        self.name = name
        self.description = f"Google Drive MCP tool: {name}"
        self.args = {
            "name": {"type": "string", "description": "File or document name"},
            "content": {"type": "string", "description": "File content"},
        }
        self.required = ["name"]
        self._result = result or {"file_id": "gdrive_file_123", "status": "created"}

    def invoke(self, args):
        return self._result

    async def ainvoke(self, args):
        return self._result


def test_infer_google_drive_permission():
    """Verify role-based permission inference for Google Drive actions."""
    assert infer_google_drive_permission("search_files") == ToolPermission.READ
    assert infer_google_drive_permission("get_file_metadata") == ToolPermission.READ
    assert infer_google_drive_permission("download_file") == ToolPermission.READ
    assert infer_google_drive_permission("google_drive_create_file") == ToolPermission.WRITE
    assert infer_google_drive_permission("upload_document") == ToolPermission.WRITE
    assert infer_google_drive_permission("update_file_content") == ToolPermission.WRITE
    assert infer_google_drive_permission("delete_file") == ToolPermission.DESTRUCTIVE
    assert infer_google_drive_permission("trash_document") == ToolPermission.DESTRUCTIVE


def test_google_drive_write_permission_enforcement_blocks_read_only():
    """Verify caller with only READ permission is blocked before creating or writing files."""
    mock_write_tool = MockGoogleDriveMCPTool(name="google_drive_create_file")
    tool = create_google_drive_mcp_wrapper(mcp_tool=mock_write_tool, enable_db_logging=False)

    assert tool.permissions == ToolPermission.WRITE

    # Execution with only READ permission must fail before executing
    read_only_ctx = ExecutionContext(permissions={ToolPermission.READ})
    with pytest.raises(ToolPermissionError, match="Permission denied"):
        tool.execute({"name": "Quarterly Report.docx"}, context=read_only_ctx)


def test_google_drive_write_permission_enforcement_allows_authorized_caller():
    """Verify caller with WRITE permission successfully creates/writes files."""
    mock_write_tool = MockGoogleDriveMCPTool(name="google_drive_create_file")
    tool = create_google_drive_mcp_wrapper(mcp_tool=mock_write_tool, enable_db_logging=False)

    write_ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.WRITE})
    result = tool.execute({"name": "Quarterly Report.docx"}, context=write_ctx)

    assert tool.status == ToolStatus.SUCCESS
    assert result["file_id"] == "gdrive_file_123"


def test_google_drive_destructive_permission_enforcement():
    """Verify destructive trash/delete operations require DESTRUCTIVE permission."""
    mock_delete_tool = MockGoogleDriveMCPTool(name="google_drive_trash_document")
    tool = create_google_drive_mcp_wrapper(mcp_tool=mock_delete_tool, enable_db_logging=False)

    assert tool.permissions == ToolPermission.DESTRUCTIVE

    # Caller with only WRITE permission should still be blocked from trashing
    write_only_ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.WRITE})
    with pytest.raises(ToolPermissionError):
        tool.execute({"name": "doc_id"}, context=write_only_ctx)

    # Caller with DESTRUCTIVE permission can proceed
    destructive_ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.DESTRUCTIVE})
    result = tool.execute({"name": "doc_id"}, context=destructive_ctx)
    assert tool.status == ToolStatus.SUCCESS


def test_google_drive_schema_and_validation():
    """Verify parameter schema and required field validation."""
    mock_tool = MockGoogleDriveMCPTool(name="google_drive_create_file")
    tool = create_google_drive_mcp_wrapper(mcp_tool=mock_tool)
    schema = tool.to_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "google_drive_create_file"
    assert "name" in schema["function"]["parameters"]["required"]

    # Missing required argument fails validation
    ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.WRITE})
    with pytest.raises(ToolValidationError):
        tool.execute({}, context=ctx)


def test_google_drive_langgraph_node_recovery():
    """Verify LangGraphToolNode captures permission errors gracefully for agent recovery."""
    mock_tool = MockGoogleDriveMCPTool(name="google_drive_upload_document")
    tool = create_google_drive_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    # Mount tool with read-only context in LangGraph node
    read_only_ctx = ExecutionContext(permissions={ToolPermission.READ})
    node = LangGraphToolNode(tools=[tool], context=read_only_ctx)

    state = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_gdrive_1", "name": "google_drive_upload_document", "args": {"name": "Test.pdf"}}
                ],
            }
        ]
    }
    output = node(state)

    assert len(output["messages"]) == 1
    message = output["messages"][0]
    assert message["status"] == "error"
    assert "Permission denied" in message["content"]


@pytest.mark.asyncio
async def test_get_google_drive_tools_raises_when_no_server_or_empty():
    """Verify RuntimeError is raised when Google Drive MCP server is unreachable or returns no tools."""
    class EmptyMCPClientManager:
        async def get_google_drive_tools(self, **kwargs):
            return []

    with pytest.raises(RuntimeError, match="returned no tools"):
        await get_google_drive_tools(
            client_manager=EmptyMCPClientManager(),
            enable_db_logging=False,
        )
