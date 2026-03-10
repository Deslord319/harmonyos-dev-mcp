import pytest


@pytest.mark.asyncio
async def test_check_wsl_returns_mcp_envelope(monkeypatch):
    from harmonyos_compile_mcp.tools import compile_tools

    class DummyManager:
        def check_wsl_available(self):
            return {"status": "available", "can_compile": True}

    monkeypatch.setattr(compile_tools, "get_compile_manager", lambda: DummyManager())

    result = await compile_tools.check_wsl()

    assert result["isError"] is False
    sc = result["structuredContent"]
    assert sc["tool"] == "check_wsl"
    assert sc["ok"] is True
    assert sc["result"]["status"] == "available"


@pytest.mark.asyncio
async def test_verify_so_output_wraps_failure(monkeypatch):
    from harmonyos_compile_mcp.tools import compile_tools

    class DummyManager:
        def verify_so_output(self, project_dir, output_dir=None):
            return {
                "success": False,
                "message": "missing output dir",
                "verified": False,
                "so_files": [],
            }

    monkeypatch.setattr(compile_tools, "get_compile_manager", lambda: DummyManager())

    result = await compile_tools.verify_so_output("C:\\dummy")

    assert result["isError"] is True
    sc = result["structuredContent"]
    assert sc["tool"] == "verify_so_output"
    assert sc["ok"] is False
    assert sc["error"]["code"] == "VERIFY_SO_ERROR"
    assert sc["result"]["verified"] is False
