# HarmonyOS Dev MCP

HarmonyOS device automation and E2E testing MCP workspace.

[![Version](https://img.shields.io/badge/version-0.7.6-blue)](services/harmonyos_dev_mcp/pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![HarmonyOS](https://img.shields.io/badge/HarmonyOS-5.0+-green)](https://developer.huawei.com/consumer/cn/harmonyos/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

## Overview

This repository is a workspace for HarmonyOS MCP services. The current mainline service is `harmonyos_dev_mcp`, which exposes HarmonyOS build, device, UI, window, and log capabilities as MCP tools.

It is designed to support:

- device automation
- app build and deployment
- UI interaction
- E2E execution
- log-based validation and troubleshooting

## Workspace Layout

```text
mcp_ho_dev/
|- packages/
|  |- common/                      # Shared MCP infrastructure
|- services/
|  |- harmonyos_dev_mcp/          # Main HarmonyOS device automation service
|  |- harmonyos_compile_mcp/      # Reserved / non-mainline service
|- pyproject.toml                 # Workspace config
|- uv.lock
|- README.md
```

## Main Service

The main service lives in [services/harmonyos_dev_mcp](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp).

Tool groups:

- General: `list_devices`, `query_package`, `logs_query`
- Build: `build_app`, `install_app`, `run_app`, `uninstall_app`
- UI: `screenshot`, `click_element`, `long_press_element`, `input_text`, `swipe`, `drag`, `press_key`, `find_element`
- E2E: `get_ui_tree`, `list_windows`, `wait_element`

## Quick Start

```bash
uv sync --all-packages
uv run harmonyos-dev-mcp
```

Check connected devices:

```bash
hdc list targets
```

## Documentation

- [Service README](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp/README.md)
- [Tool Reference](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp/docs/tool_reference.md)
- [Logs Query Guide](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp/docs/logs_query.md)

## Development

Run unit tests:

```bash
uv run pytest services/harmonyos_dev_mcp/tests/unit -v
```

Run with coverage:

```bash
uv run pytest services/harmonyos_dev_mcp/tests/unit -v --cov=harmonyos_dev_mcp
```

## Notes

- `build_app` is a long-running tool. Set MCP `tools/call timeout` to at least `60s`, and prefer `120s` for cold builds.
- `build_app target="hnp"` builds a base HAP, injects module HNP packages from `entry/hnp`, and signs the HAP through the SDK packaging tools.
- `logs_query` supports `errors` and `markers` modes.
- The detailed parameter definitions for all tools are maintained in the tool reference, not in this top-level README.

## License

Apache License 2.0
