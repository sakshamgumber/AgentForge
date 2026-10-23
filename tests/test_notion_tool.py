"""Unit tests for Notion MCP tool integration with MCPToolWrapper and permission guards."""

import pytest
from app.mcp.client_manager import MCPClientManager
from app.mcp.configuration.notion import get_notion_config
from app.tools.base import ExecutionContext, ToolStatus, ToolPermissionError, ToolValidationError
from app.tools.enums import ToolPermission
from app.tools.notion import (
    create_notion_mcp_wrapper,
    get_notion_tools,
    infer_notion_permission,
)
from app.tools.langgraph_adapter import LangGraphToolNode


class MockNotionMCPTool:
    """Mock MCP tool mimicking a tool returned from Notion MCP server."""

    def __init__(self, name="notion_create_page", result=None):
        self.name = name
        self.description = f"Notion MCP tool: {name}"
        if "search" in name or "fetch" in name or "get" in name:
            self.args = {
                "query": {"type": "string", "description": "Search query or identifier"},
            }
            self.required = ["query"]
        else:
            self.args = {
                "parent_id": {"type": "string", "description": "Parent database or page ID"},
                "title": {"type": "string", "description": "Page title"},
            }
            self.required = ["parent_id", "title"]
        self._result = result or {"page_id": "notion_page_123", "url": "https://notion.so/page123"}

    def invoke(self, args):
        return self._result

    async def ainvoke(self, args):
        return self._result


def test_get_notion_config(monkeypatch):
    """Verify Notion MCP configuration generator with defaults and custom parameters."""
    # Custom url and token
    config = get_notion_config(
        url="https://custom.notion.mcp/endpoint",
        access_token="secret_notion_token_abc",
        headers={"X-Custom-Header": "TestValue"},
    )
    assert config["transport"] == "http"
    assert config["url"] == "https://custom.notion.mcp/endpoint"
    assert config["headers"]["Authorization"] == "Bearer secret_notion_token_abc"
    assert config["headers"]["X-Custom-Header"] == "TestValue"

    # Fallback to NOTION_API_KEY if NOTION_ACCESS_TOKEN is not set
    monkeypatch.delenv("NOTION_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("NOTION_API_KEY", "secret_from_api_key")
    config_api_key = get_notion_config()
    assert config_api_key["headers"]["Authorization"] == "Bearer secret_from_api_key"


def test_infer_notion_permission():
    """Verify role-based permission inference for Notion operations."""
    # READ
    assert infer_notion_permission("search") == ToolPermission.READ
    assert infer_notion_permission("notion_search") == ToolPermission.READ
    assert infer_notion_permission("get_page") == ToolPermission.READ
    assert infer_notion_permission("get_block_children") == ToolPermission.READ
    assert infer_notion_permission("query_database") == ToolPermission.READ
    assert infer_notion_permission("fetch") == ToolPermission.READ
    assert infer_notion_permission("list_databases") == ToolPermission.READ

    # WRITE
    assert infer_notion_permission("create_page") == ToolPermission.WRITE
    assert infer_notion_permission("notion_create_page") == ToolPermission.WRITE
    assert infer_notion_permission("append_block_children") == ToolPermission.WRITE
    assert infer_notion_permission("update_page") == ToolPermission.WRITE
    assert infer_notion_permission("update_block") == ToolPermission.WRITE
    assert infer_notion_permission("insert_block") == ToolPermission.WRITE
    assert infer_notion_permission("duplicate_page") == ToolPermission.WRITE

    # DESTRUCTIVE
    assert infer_notion_permission("archive_page") == ToolPermission.DESTRUCTIVE
    assert infer_notion_permission("notion_archive_page") == ToolPermission.DESTRUCTIVE
    assert infer_notion_permission("delete_block") == ToolPermission.DESTRUCTIVE
    assert infer_notion_permission("trash_page") == ToolPermission.DESTRUCTIVE
    assert infer_notion_permission("remove_content") == ToolPermission.DESTRUCTIVE


def test_notion_wrapper_requires_mcp_tool():
    """Verify ValueError is raised if mcp_tool is None."""
    with pytest.raises(ValueError, match="mcp_tool must be provided"):
        create_notion_mcp_wrapper(mcp_tool=None)


def test_notion_wrapper_schema_and_permissions():
    """Verify parameter schema and automatic permission mapping."""
    mock_tool = MockNotionMCPTool(name="notion_create_page")
    tool = create_notion_mcp_wrapper(
        mcp_tool=mock_tool,
        attempt_id="att-notion-1",
        operation_id="op-notion-1",
    )
    schema = tool.to_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "notion_create_page"
    assert "parent_id" in schema["function"]["parameters"]["properties"]
    assert "title" in schema["function"]["parameters"]["required"]
    assert tool.server_name == "notion"
    assert tool.permissions == ToolPermission.WRITE


def test_notion_write_permission_enforcement_blocks_read_only():
    """Verify caller with only READ permission is blocked before mutating Notion pages."""
    mock_write_tool = MockNotionMCPTool(name="notion_create_page")
    tool = create_notion_mcp_wrapper(mcp_tool=mock_write_tool, enable_db_logging=False)

    assert tool.permissions == ToolPermission.WRITE

    read_only_ctx = ExecutionContext(permissions={ToolPermission.READ})
    with pytest.raises(ToolPermissionError, match="Permission denied"):
        tool.execute({"parent_id": "db_123", "title": "New Meeting Notes"}, context=read_only_ctx)


def test_notion_write_permission_enforcement_allows_authorized_caller():
    """Verify caller with WRITE permission successfully creates Notion pages."""
    mock_write_tool = MockNotionMCPTool(name="notion_create_page")
    tool = create_notion_mcp_wrapper(mcp_tool=mock_write_tool, enable_db_logging=False)

    write_ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.WRITE})
    result = tool.execute({"parent_id": "db_123", "title": "New Meeting Notes"}, context=write_ctx)

    assert tool.status == ToolStatus.SUCCESS
    assert result["page_id"] == "notion_page_123"


def test_notion_destructive_permission_enforcement():
    """Verify archive/delete operations require DESTRUCTIVE permission."""
    mock_archive_tool = MockNotionMCPTool(name="notion_archive_page")
    tool = create_notion_mcp_wrapper(mcp_tool=mock_archive_tool, enable_db_logging=False)

    assert tool.permissions == ToolPermission.DESTRUCTIVE

    # Caller with only WRITE permission should still be blocked from archiving
    write_only_ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.WRITE})
    with pytest.raises(ToolPermissionError):
        tool.execute({"parent_id": "db_123", "title": "Old Page"}, context=write_only_ctx)

    # Caller with DESTRUCTIVE permission can proceed
    destructive_ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.DESTRUCTIVE})
    result = tool.execute({"parent_id": "db_123", "title": "Old Page"}, context=destructive_ctx)
    assert tool.status == ToolStatus.SUCCESS


def test_notion_langgraph_node_integration():
    """Verify Notion tool executes inside LangGraphToolNode."""
    mock_tool = MockNotionMCPTool(name="notion_search", result=[{"id": "page_99", "title": "Roadmap"}])
    tool = create_notion_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    node = LangGraphToolNode(tools=[tool])
    state = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_notion_1", "name": "notion_search", "args": {"query": "Roadmap"}}
                ],
            }
        ]
    }
    output = node(state)
    assert len(output["messages"]) == 1
    assert output["messages"][0]["status"] == "success"
    assert "Roadmap" in output["messages"][0]["content"]


def test_notion_langgraph_node_recovery():
    """Verify LangGraphToolNode captures permission errors gracefully for agent recovery."""
    mock_tool = MockNotionMCPTool(name="notion_create_page")
    tool = create_notion_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    read_only_ctx = ExecutionContext(permissions={ToolPermission.READ})
    node = LangGraphToolNode(tools=[tool], context=read_only_ctx)

    state = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_notion_2", "name": "notion_create_page", "args": {"parent_id": "1", "title": "Doc"}}
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
async def test_get_notion_tools_with_client_manager():
    """Verify get_notion_tools with custom client manager."""
    mock_tool = MockNotionMCPTool(name="notion_search")

    class MockMCPClientManager:
        async def get_notion_tools(self, **kwargs):
            return [create_notion_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)]

    tools = await get_notion_tools(
        client_manager=MockMCPClientManager(),
        enable_db_logging=False,
    )
    assert len(tools) == 1
    assert tools[0].name == "notion_search"
    assert tools[0].server_name == "notion"


@pytest.mark.asyncio
async def test_get_notion_tools_raises_when_no_server_or_empty():
    """Verify RuntimeError is raised when Notion MCP server returns no tools."""
    class EmptyMCPClientManager:
        async def get_notion_tools(self, **kwargs):
            return []

    with pytest.raises(RuntimeError, match="returned no tools"):
        await get_notion_tools(
            client_manager=EmptyMCPClientManager(),
            enable_db_logging=False,
        )


@pytest.mark.asyncio
async def test_client_manager_get_notion_tools():
    """Verify MCPClientManager.get_notion_tools retrieves and filters notion tools."""
    mock_tool = MockNotionMCPTool(name="notion_search")
    manager = MCPClientManager(enabled_servers=["notion"])

    class MockClient:
        async def get_tools(self):
            return [mock_tool]

    manager._client = MockClient()
    tools = await manager.get_notion_tools(enable_db_logging=False)
    assert len(tools) == 1
    assert tools[0].name == "notion_search"
    assert tools[0].server_name == "notion"
