"""Unit tests for Context7 MCP tool integration and direct Context7APIClient."""

import io
import json
import urllib.error
import pytest

from app.mcp.client_manager import MCPClientManager
from app.mcp.configuration.context7 import get_context7_config
from app.tools.base import ExecutionContext, ToolStatus
from app.tools.enums import ToolPermission
from app.tools.context7 import (
    Context7APIClient,
    create_context7_mcp_wrapper,
    get_context7_tools,
    infer_context7_permission,
)
from app.tools.langgraph_adapter import LangGraphToolNode


class MockContext7MCPTool:
    """Mock MCP tool mimicking a tool returned from Context7 MCP server."""

    def __init__(self, name="resolve-library-id", result=None):
        self.name = name
        self.description = f"Context7 documentation tool: {name}"
        if "resolve" in name:
            self.args = {
                "query": {"type": "string", "description": "Library or package name to resolve"},
            }
            self.required = ["query"]
            self._result = result or ["/tiangolo/fastapi", "/tiangolo/fastapi/0.115.0"]
        else:
            self.args = {
                "libraryId": {"type": "string", "description": "Context7 library ID"},
                "query": {"type": "string", "description": "Topic or concept to look up"},
            }
            self.required = ["libraryId", "query"]
            self._result = result or "## FastAPI Dependency Injection\nUse `Depends()` to inject dependencies."

    def invoke(self, args):
        return self._result

    async def ainvoke(self, args):
        return self._result


def test_get_context7_config(monkeypatch):
    """Verify Context7 configuration generator with defaults and custom parameters."""
    config = get_context7_config(
        url="https://custom.context7.com/mcp",
        api_key="ctx7_secret_123",
        headers={"X-Custom": "Val"},
    )
    assert config["transport"] == "http"
    assert config["url"] == "https://custom.context7.com/mcp"
    assert config["headers"]["Authorization"] == "Bearer ctx7_secret_123"
    assert config["headers"]["X-Custom"] == "Val"

    # Fallback to CONTEXT7_TOKEN
    monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
    monkeypatch.setenv("CONTEXT7_TOKEN", "token_fallback_abc")
    config_fallback = get_context7_config()
    assert config_fallback["headers"]["Authorization"] == "Bearer token_fallback_abc"


def test_infer_context7_permission():
    """Verify Context7 tools resolve to READ permission."""
    assert infer_context7_permission("resolve-library-id") == ToolPermission.READ
    assert infer_context7_permission("context7_resolve_library_id") == ToolPermission.READ
    assert infer_context7_permission("query-docs") == ToolPermission.READ
    assert infer_context7_permission("query_docs") == ToolPermission.READ
    assert infer_context7_permission("get_library_docs") == ToolPermission.READ
    assert infer_context7_permission("search_documentation") == ToolPermission.READ


def test_context7_wrapper_requires_mcp_tool():
    """Verify ValueError is raised if mcp_tool is None."""
    with pytest.raises(ValueError, match="mcp_tool must be provided"):
        create_context7_mcp_wrapper(mcp_tool=None)


def test_context7_wrapper_schema_and_permissions():
    """Verify JSON schema and automatic READ permission mapping."""
    mock_tool = MockContext7MCPTool(name="query-docs")
    tool = create_context7_mcp_wrapper(
        mcp_tool=mock_tool,
        attempt_id="att-ctx7-1",
        operation_id="op-ctx7-1",
    )
    schema = tool.to_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "query-docs"
    assert "libraryId" in schema["function"]["parameters"]["properties"]
    assert "query" in schema["function"]["parameters"]["properties"]
    assert tool.server_name == "context7"
    assert tool.permissions == ToolPermission.READ


def test_context7_wrapper_execution_mocked():
    """Verify execution of wrapped Context7 tool."""
    mock_tool = MockContext7MCPTool(name="query-docs")
    tool = create_context7_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    ctx = ExecutionContext(permissions={ToolPermission.READ})
    result = tool.execute(
        {"libraryId": "/tiangolo/fastapi", "query": "dependency injection"},
        context=ctx,
    )
    assert tool.status == ToolStatus.SUCCESS
    assert "FastAPI Dependency Injection" in result


def test_context7_langgraph_node_integration():
    """Verify Context7 tool executes seamlessly inside LangGraphToolNode."""
    mock_tool = MockContext7MCPTool(name="resolve-library-id")
    tool = create_context7_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)

    node = LangGraphToolNode(tools=[tool])
    state = {
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_ctx7_1", "name": "resolve-library-id", "args": {"query": "fastapi"}}
                ],
            }
        ]
    }
    output = node(state)
    assert len(output["messages"]) == 1
    assert output["messages"][0]["status"] == "success"
    assert "/tiangolo/fastapi" in output["messages"][0]["content"]


@pytest.mark.asyncio
async def test_get_context7_tools_with_client_manager():
    """Verify get_context7_tools with client manager."""
    mock_tool = MockContext7MCPTool(name="resolve-library-id")

    class MockMCPClientManager:
        async def get_context7_tools(self, **kwargs):
            return [create_context7_mcp_wrapper(mcp_tool=mock_tool, enable_db_logging=False)]

    tools = await get_context7_tools(
        client_manager=MockMCPClientManager(),
        enable_db_logging=False,
    )
    assert len(tools) == 1
    assert tools[0].name == "resolve-library-id"
    assert tools[0].server_name == "context7"


@pytest.mark.asyncio
async def test_get_context7_tools_raises_when_no_server_or_empty():
    """Verify RuntimeError is raised when Context7 MCP server returns no tools."""
    class EmptyMCPClientManager:
        async def get_context7_tools(self, **kwargs):
            return []

    with pytest.raises(RuntimeError, match="returned no tools"):
        await get_context7_tools(
            client_manager=EmptyMCPClientManager(),
            enable_db_logging=False,
        )


@pytest.mark.asyncio
async def test_client_manager_get_context7_tools():
    """Verify MCPClientManager.get_context7_tools retrieves and filters context7 tools."""
    mock_tool = MockContext7MCPTool(name="context7_query_docs")
    manager = MCPClientManager(enabled_servers=["context7"])

    class MockClient:
        async def get_tools(self):
            return [mock_tool]

    manager._client = MockClient()
    tools = await manager.get_context7_tools(enable_db_logging=False)
    assert len(tools) == 1
    assert tools[0].name == "context7_query_docs"
    assert tools[0].server_name == "context7"


def test_context7_api_client_direct_resolve(monkeypatch):
    """Verify direct Context7APIClient resolve_library_id method."""
    client = Context7APIClient(api_key="test_key", base_url="https://mcp.context7.com/mcp")

    class MockHTTPResponse:
        def __init__(self, data):
            self._data = data

        def read(self):
            return self._data.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req, timeout=30.0):
        assert req.headers["Authorization"] == "Bearer test_key"
        body = json.loads(req.data.decode("utf-8"))
        assert body["method"] == "tools/call"
        assert body["params"]["name"] == "resolve-library-id"
        return MockHTTPResponse(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": ["/tiangolo/fastapi"],
        }))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    res = client.resolve_library_id("fastapi")
    assert res == ["/tiangolo/fastapi"]


@pytest.mark.asyncio
async def test_context7_api_client_direct_query_docs(monkeypatch):
    """Verify direct Context7APIClient query_docs async method."""
    client = Context7APIClient(api_key="test_key")

    class MockHTTPResponse:
        def __init__(self, data):
            self._data = data

        def read(self):
            return self._data.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req, timeout=30.0):
        body = json.loads(req.data.decode("utf-8"))
        assert body["params"]["name"] == "query-docs"
        assert body["params"]["arguments"]["libraryId"] == "/tiangolo/fastapi"
        return MockHTTPResponse(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": "Docs content",
        }))

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    res = await client.a_query_docs(library_id="/tiangolo/fastapi", query="routing")
    assert res == "Docs content"


def test_context7_api_client_error_handling(monkeypatch):
    """Verify Context7APIClient raises RuntimeError on HTTP failure."""
    client = Context7APIClient(api_key="test_key")

    def mock_urlopen_fail(req, timeout=30.0):
        fp = io.BytesIO(b'{"message": "Unauthorized"}')
        raise urllib.error.HTTPError(
            url="https://mcp.context7.com/mcp",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=fp,
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_fail)

    with pytest.raises(RuntimeError, match="Context7 API request failed with HTTP 401"):
        client.resolve_library_id("fastapi")
