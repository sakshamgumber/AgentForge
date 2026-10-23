"""Unit tests for GitHub MCP tool integration with MCPToolWrapper."""

import pytest
from app.mcp.configuration.github import get_github_config
from app.tools.base import ExecutionContext, ToolStatus, ToolPermissionError, ToolValidationError
from app.tools.enums import ToolPermission
from app.tools.github import (
    create_github_mcp_wrapper,
    get_github_tools,
    infer_github_permission,
)
from app.tools.langgraph_adapter import LangGraphToolNode


class MockGitHubMCPTool:
    """Mock MCP tool mimicking a tool returned by MultiServerMCPClient from GitHub server."""

    def __init__(self, name="github_search_repositories", result=None):
        self.name = name
        self.description = f"GitHub MCP tool: {name}"
        self.args = {
            "query": {"type": "string", "description": "Search query"},
        }
        self.required = ["query"]
        self._result = result or [{"id": 1, "name": "AgentForge", "owner": "sakshamgumber"}]

    def invoke(self, args):
        return self._result

    async def ainvoke(self, args):
        return self._result


def test_get_github_config():
    """Verify GitHub MCP configuration generator."""
    config = get_github_config(token="ghp_test_secret_123")
    assert config["transport"] == "stdio"
    assert config["command"] == "npx"
    assert "@modelcontextprotocol/server-github" in config["args"]
    assert config["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_test_secret_123"


def test_infer_github_permission():
    """Verify role-based permission inference for GitHub actions."""
    assert infer_github_permission("search_repositories") == ToolPermission.READ
    assert infer_github_permission("get_file_contents") == ToolPermission.READ
    assert infer_github_permission("list_issues") == ToolPermission.READ
    assert infer_github_permission("github_create_issue") == ToolPermission.WRITE
    assert infer_github_permission("update_pull_request") == ToolPermission.WRITE
    assert infer_github_permission("add_comment") == ToolPermission.WRITE
    assert infer_github_permission("delete_file") == ToolPermission.DESTRUCTIVE
    assert infer_github_permission("github_push_files") == ToolPermission.DESTRUCTIVE


def test_github_wrapper_requires_mcp_tool():
    """Verify ValueError is raised if mcp_tool is None."""
    with pytest.raises(ValueError, match="mcp_tool must be provided"):
        create_github_mcp_wrapper(mcp_tool=None)


def test_github_wrapper_schema_and_permissions():
    """Verify JSON schema and automatic permission mapping."""
    mock_tool = MockGitHubMCPTool(name="github_create_issue")
    tool = create_github_mcp_wrapper(
        mcp_tool=mock_tool,
        attempt_id="att-gh-1",
        operation_id="op-gh-1",
    )
    schema = tool.to_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "github_create_issue"
    assert "query" in schema["function"]["parameters"]["properties"]
    assert "query" in schema["function"]["parameters"]["required"]
    assert tool.server_name == "github"
    assert tool.permissions == ToolPermission.WRITE


def test_github_wrapper_permission_enforcement():
    """Verify ExecutionContext permission checks on write tools."""
    mock_tool = MockGitHubMCPTool(name="github_create_issue")
    tool = create_github_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    # Read-only caller execution should fail
    read_only_ctx = ExecutionContext(permissions={ToolPermission.READ})
    with pytest.raises(ToolPermissionError):
        tool.execute({"query": "issue title"}, context=read_only_ctx)

    # Caller with WRITE permission should succeed
    write_ctx = ExecutionContext(permissions={ToolPermission.READ, ToolPermission.WRITE})
    result = tool.execute({"query": "issue title"}, context=write_ctx)
    assert tool.status == ToolStatus.SUCCESS
    assert result is not None


def test_github_langgraph_node_integration():
    """Verify GitHub tool executes inside LangGraphToolNode."""
    mock_tool = MockGitHubMCPTool(name="github_search_repositories")
    tool = create_github_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    node = LangGraphToolNode(tools=[tool])
    state = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_gh_1", "name": "github_search_repositories", "args": {"query": "AgentForge"}}
                ],
            }
        ]
    }
    output = node(state)
    assert len(output["messages"]) == 1
    assert output["messages"][0]["status"] == "success"
    assert "AgentForge" in output["messages"][0]["content"]


@pytest.mark.asyncio
async def test_get_github_tools_with_client_manager():
    """Verify get_github_tools with custom client manager."""
    mock_tool = MockGitHubMCPTool()

    class MockMCPClientManager:
        async def get_tools(self):
            return [mock_tool]

    tools = await get_github_tools(
        client_manager=MockMCPClientManager(),
        enable_db_logging=False,
    )
    assert len(tools) == 1
    assert tools[0].name == "github_search_repositories"
    assert tools[0].server_name == "github"


@pytest.mark.asyncio
async def test_get_github_tools_raises_when_no_server_or_empty():
    """Verify RuntimeError is raised when GitHub MCP server returns no tools."""
    class EmptyMCPClientManager:
        async def get_tools(self):
            return []

    with pytest.raises(RuntimeError, match="returned no tools"):
        await get_github_tools(
            client_manager=EmptyMCPClientManager(),
            enable_db_logging=False,
        )
