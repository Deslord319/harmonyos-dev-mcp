from unittest.mock import Mock

import pytest
from fastmcp import Client

from common.server.base import run_server


def test_run_server_disables_banner_by_default():
    server = Mock()

    run_server(server)

    server.run.assert_called_once_with(show_banner=False)


def test_run_server_allows_overriding_banner():
    server = Mock()

    run_server(server, show_banner=True)

    server.run.assert_called_once_with(show_banner=True)


@pytest.mark.asyncio
async def test_list_devices_round_trips_through_fastmcp_client(mock_hdc):
    from harmonyos_mcp.server import mcp

    async with Client(mcp) as client:
        result = await client.call_tool_mcp("list_devices", {})

    assert result.isError is False
    assert isinstance(result.structuredContent, dict)
    structured = result.structuredContent
    if "structuredContent" in structured:
        structured = structured["structuredContent"]
    assert structured["ok"] is True
    assert structured["result"]["count"] == len(structured["result"]["devices"])
    assert structured["result"]["devices"]
    assert structured["result"]["devices"][0]["device_id"]


@pytest.mark.asyncio
async def test_e2e_tool_schemas_are_exposed_via_fastmcp(mock_hdc):
    from harmonyos_mcp.server import mcp

    async with Client(mcp) as client:
        tools = await client.list_tools()

    tool_map = {tool.name: tool for tool in tools}

    assert "bundle_name" in tool_map["list_windows"].inputSchema["properties"]
    assert "bundle_name" in tool_map["get_ui_tree"].inputSchema["properties"]
    assert "bundle_name" in tool_map["wait_element"].inputSchema["properties"]
    assert tool_map["wait_element"].inputSchema["properties"]["state"]["enum"] == ["found", "gone"]
