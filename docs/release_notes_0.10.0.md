# HarmonyOS Dev MCP 0.10.0

Release date: 2026-09-20

Version 0.10.0 adds a HarmonyOS on-device runtime and improves TCP-based HDC
transport. The existing Windows and macOS workflow remains supported.

## Highlights

- Added a pure-Python MCP stdio server that can run directly on HarmonyOS.
- Added a direct TCP HDC client for environments where sandboxing prevents
  subprocess access to the system HDC socket.
- Bundled lightweight `fastmcp`, `mcp`, and `loguru` stubs for the on-device
  runtime, avoiding native-extension dependencies there.
- Added `setup.sh` to discover the on-device Python, SDK, and HDC environment.
- Parallelized TCP file transfers to reduce deployment time for larger files.
- Added HarmonyOS-aware SDK and Node.js toolchain discovery, using
  `HARMONYOS_NODE_PATH` for the HarmonyOS Node.js executable.
- Improved `input_text` verification for composite UI components.

## Upgrade

For the standard desktop-hosted server:

```bash
pip install --upgrade harmonyos-dev-mcp==0.10.0
```

For on-device use, start HDC in TCP mode, set `HDC_USE_TCP=1`, and follow the
[HarmonyOS on-device instructions](../README.md#harmonyos-on-device).

## Compatibility

- Desktop runtime: Python 3.12 or newer.
- Existing MCP tool names and contracts from 0.9.1 are unchanged.
- `HARMONYOS_NODE_PATH` replaces use of `NODE_PATH` for HarmonyOS-specific
  Node.js discovery.
