"""HarmonyOS adapter for harmonyos-dev-mcp.

Provides:
- tcp_hdc: Direct TCP hdc client (bypasses subprocess + UDS sandbox)
- mcp_server: Pure Python MCP stdio server (no fastmcp dependency)
- stubs: Bundled stubs for fastmcp, mcp.types, loguru
- setup.sh: One-command setup for OpenDesk
"""
