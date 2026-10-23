"""Unit tests for DuckDuckGo MCP tool integration with MCPToolWrapper."""

import pytest
from app.tools.base import ExecutionContext, ToolStatus, ToolValidationError
from app.tools.enums import ToolPermission
from app.tools.duckduckgo import (
    create_duckduckgo_mcp_wrapper,
    get_duckduckgo_tools,
)
from app.tools.langgraph_adapter import LangGraphToolNode


class MockMCPTool:
    """Mock MCP tool mimicking a tool returned by MultiServerMCPClient."""

    def __init__(self, name="duckduckgo_search", result=None):
        self.name = name
        self.description = "Search the web using DuckDuckGo MCP server."
        self.args = {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results", "default": 5},
        }
        self.required = ["query"]
        self._result = result or [{"title": "AgentForge", "snippet": "Agent framework", "url": "https://example.com"}]

    def invoke(self, args):
        return self._result

    async def ainvoke(self, args):
        return self._result


def test_duckduckgo_wrapper_requires_mcp_tool():
    """Verify ValueError is raised if mcp_tool is None."""
    with pytest.raises(ValueError, match="mcp_tool must be provided"):
        create_duckduckgo_mcp_wrapper(mcp_tool=None)


def test_duckduckgo_wrapper_schema():
    """Verify JSON schema compliant with OpenAI / LangChain function calling."""
    mock_tool = MockMCPTool()
    tool = create_duckduckgo_mcp_wrapper(
        mcp_tool=mock_tool,
        attempt_id="att-test-1",
        operation_id="op-test-1",
    )
    schema = tool.to_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "duckduckgo_search"
    assert "query" in schema["function"]["parameters"]["properties"]
    assert "query" in schema["function"]["parameters"]["required"]
    assert tool.permissions == ToolPermission.READ
    assert tool.server_name == "duckduckgo"


def test_duckduckgo_wrapper_missing_query_validation():
    """Verify validation fails when required query is missing."""
    mock_tool = MockMCPTool()
    tool = create_duckduckgo_mcp_wrapper(mcp_tool=mock_tool)
    ctx = ExecutionContext()

    with pytest.raises(ToolValidationError):
        tool.execute({}, context=ctx)


def test_duckduckgo_wrapper_execution_mocked():
    """Verify tool execution passes through MCPToolWrapper with tracing and compression."""
    mock_results = [{"title": "AgentForge", "snippet": "Agent framework", "url": "https://example.com"}]
    mock_tool = MockMCPTool(result=mock_results)

    tool = create_duckduckgo_mcp_wrapper(
        mcp_tool=mock_tool,
        attempt_id="att-exec-mock",
        operation_id="op-exec-mock",
        enable_db_logging=False,
    )
    ctx = ExecutionContext(attempt_id="att-exec-mock", operation_id="op-exec-mock")
    result = tool.execute({"query": "agentforge"}, context=ctx)

    assert result == mock_results
    assert tool.status == ToolStatus.SUCCESS
    assert tool.attempt_id == "att-exec-mock"
    assert tool.operation_id == "op-exec-mock"


def test_langgraph_node_integration():
    """Verify tool runs within LangGraphToolNode correctly."""
    mock_results = [{"title": "Python", "snippet": "Language", "url": "https://python.org"}]
    mock_tool = MockMCPTool(result=mock_results)
    tool = create_duckduckgo_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    node = LangGraphToolNode(tools=[tool])
    state = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_mock_1", "name": "duckduckgo_search", "args": {"query": "python"}}
                ],
            }
        ]
    }
    output = node(state)
    assert len(output["messages"]) == 1
    assert output["messages"][0]["status"] == "success"
    assert "Python" in output["messages"][0]["content"]


@pytest.mark.asyncio
async def test_get_duckduckgo_tools_success_with_manager():
    """Verify get_duckduckgo_tools retrieves wrapped tools when client manager provides them."""
    mock_tool = MockMCPTool()
    wrapped_mock = create_duckduckgo_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    class MockMCPClientManager:
        async def get_duckduckgo_tools(self, **kwargs):
            return [wrapped_mock]

    tools = await get_duckduckgo_tools(
        client_manager=MockMCPClientManager(),
        enable_db_logging=False,
    )
    assert len(tools) == 1
    assert tools[0].name == "duckduckgo_search"


@pytest.mark.asyncio
async def test_get_duckduckgo_tools_raises_when_no_server_or_empty():
    """Verify RuntimeError is raised when MCP server returns no tools."""
    class EmptyMCPClientManager:
        async def get_duckduckgo_tools(self, **kwargs):
            return []

    with pytest.raises(RuntimeError, match="returned no tools"):
        await get_duckduckgo_tools(
            client_manager=EmptyMCPClientManager(),
            enable_db_logging=False,
        )
