# HarmonyOS Dev MCP

`harmonyos_dev_mcp` provides HarmonyOS MCP tools for device discovery, app build and deployment, UI automation, E2E inspection, and log validation.

[![Version](https://img.shields.io/badge/version-0.9.1-blue)](pyproject.toml)
[![PyPI](https://img.shields.io/pypi/v/harmonyos-dev-mcp.svg)](https://pypi.org/project/harmonyos-dev-mcp/)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)

## Links

- PyPI: [harmonyos-dev-mcp](https://pypi.org/project/harmonyos-dev-mcp/)
- Tool reference: [docs/tool_reference.md](docs/tool_reference.md)
- Logs query guide: [docs/logs_query.md](docs/logs_query.md)

## What It Provides

The package exposes 18 MCP tools:

### 0.9.1 highlights

- `input_text` now selects an IME-safe strategy for digits, Unicode, and ASCII
  text without changing the active input method.
- Handle and unambiguous search targets are observed until their exact final
  value is visible or the verification deadline expires.
- Reliable text input verifies both foreground-window state and element focus
  before any text or shortcut is dispatched.
- UI mutations are serialized per HDC endpoint and device, while separate
  devices remain concurrent.
- `press_key` distinguishes event dispatch from application-level effect
  verification.

Parameter notation:

- `name`: required
- `name?`: optional
- `name*`: conditionally required, depending on the selected mode or target

Device-targeted tools also accept `hdc_server?` for wireless debugging by IP. Pass the wireless HDC endpoint, for example `192.168.43.34:35215`, to route commands as `hdc -t 192.168.43.34:35215 ...`. If both a device SN and an IP endpoint are needed, pass `device_id` as the SN and `hdc_server` as the IP endpoint; commands are routed as `hdc -t <SN> -s <IP:port> ...`. You can also set `HARMONYOS_HDC_SERVER` as a default endpoint.

General tools:

| Tool | Parameters |
|---|---|
| `list_devices` | `hdc_server?` |
| `query_package` | `device_id?`, `hdc_server?`, `bundle_name*`, `keyword?`, `info_type?="list"` |
| `logs_query` | `device_id?`, `hdc_server?`, `logs?`, `input_file?`, `input_files?`, `lines?=100`, `level?`, `tag?`, `tag_search?`, `keyword?`, `domain?`, `pid?`, `package_name?`, `start_time?`, `end_time?`, `seconds?`, `save_path?`, `time_expr?`, `include_crash?=false`, `mode?="errors"`, `marker_keywords?`, `fallback_to_historical?=false`, `realtime_wait_ms?=1000`, `context_lines?=0` |

Build tools:

| Tool | Parameters |
|---|---|
| `build_app` | `project_path`, `build_mode?="debug"`, `target?="hap"`, `product?="default"`, `module_name*`, `is_clean?=false`, `include_hsp?=false`, `hsp_module_names?` |
| `install_app` | `hap_path`, `device_id?`, `hdc_server?` |
| `run_app` | `bundle_name`, `device_id?`, `hdc_server?`, `ability_name?`, `module_name?`, `auto_detect?=true` |
| `uninstall_app` | `bundle_name`, `device_id?`, `hdc_server?` |

UI tools:

| Tool | Parameters |
|---|---|
| `screenshot` | `device_id?`, `hdc_server?`, `local_path?`, `display_id?=0`, `left*`, `top*`, `right*`, `bottom*` |
| `click` | `device_id?`, `hdc_server?`, `x*`, `y*`, `element_handle*`, `text*`, `element_type*`, `element_id*`, `count?=1`, `bundle_name?` |
| `long_press` | `device_id?`, `hdc_server?`, `x*`, `y*`, `element_handle*`, `text*`, `element_type*`, `element_id*`, `bundle_name?` |
| `input_text` | `text`, `device_id?`, `hdc_server?`, `x*`, `y*`, `element_handle*`, `element_text*`, `element_type*`, `element_id*`, `bundle_name?`, `mode?="replace"` |
| `swipe` | `device_id?`, `hdc_server?`, `from_x*`, `from_y*`, `to_x*`, `to_y*`, `direction*`, `speed?=600` |
| `drag` | `device_id?`, `hdc_server?`, `from_x`, `from_y`, `to_x`, `to_y`, `speed?=600` |
| `press_key` | `key`, `modifiers?`, `device_id?`, `hdc_server?` |
| `find_elements` | `device_id?`, `hdc_server?`, `text*`, `element_type*`, `element_id*`, `bundle_name?`, `window_id?` |

`press_key` accepts all 354 OpenHarmony InputKit `KEYCODE_*` definitions. Key
names are case- and separator-insensitive, so `KEYCODE_PAGE_UP`, `PageUp`, and
`page-up` are equivalent. Use `input_text` for strings and Chinese text.

`click` and `long_press` report `dispatched=true, effect_verified=false` when
the device accepts the command. This confirms delivery, not an application
state change.

For reliable text entry, call `find_elements` or `wait_for_element` first and
pass the returned `element_handle` to `input_text`. A search target is also
verified when it resolves to exactly one element. Coordinate mode cannot read
the target value, so it sends the original text without cleanup tricks and
returns `dispatched=true, verified=false`.

`input_text` never toggles the active IME. Internally it uses direct entry for
short ASCII digits, native paste for Unicode or long text, and a verified
sentinel-assisted paste for other ASCII text. The sentinel is removed only
after the exact sentinel-bearing value is observed. Paste strategies may
replace the device clipboard; check `clipboard_modified` in the result.

Handle and search modes first click the target, then observe both
`focused=true` and a foreground target window before dispatching text. Set
`INPUT_FOCUS_TIMEOUT_MS` to change the default `5000ms` focus budget. A
background or occluded target that does not acquire focus returns
`INPUT_FOCUS_TIMEOUT` without dispatching text.

Input verification also uses a deadline rather than a fixed delay. Set
`INPUT_VERIFY_TIMEOUT_MS` to change the default `15000ms` value budget.
Successful observations return immediately. Password fields and some Web/Chromium
accessibility fields may not expose or accept deterministic text operations;
these return a verification error with the last observed `actual_text` instead
of claiming success. A failed write may still leave partial text in the target.

E2E tools:

| Tool | Parameters |
|---|---|
| `get_ui_tree` | `device_id?`, `hdc_server?`, `bundle_name?`, `window_id?` |
| `list_windows` | `device_id?`, `hdc_server?`, `bundle_name?` |
| `wait_for_element` | `device_id?`, `hdc_server?`, `bundle_name?`, `window_id?`, `text*`, `element_type*`, `element_id*`, `state?="found"`, `timeout_ms?=5000`, `interval_ms?=300` |

`wait_for_element.timeout_ms` is a strict wall-clock budget covering device
queries, polling sleeps, and the stability confirmation. When the budget
expires, the tool returns `WAIT_TIMEOUT` without starting another observation;
`timeout_ms=0` returns immediately without querying the device.

`build_app` supports HarmonyOS HAP, HAR, HSP, APP, and HNP build flows. HSP outputs can also be integrated into a HAP with `include_hsp=true`.

Detailed validation rules, result fields, errors, and examples are in the [tool reference](docs/tool_reference.md).

## Layout

```text
mcp_ho_dev/
|- src/harmonyos_dev_mcp/
|  |- build/                   # Hvigor build helpers, signing, packaging, and target handlers
|  |- device/hdc/              # HDC device, package, app, file, and UI adapters
|  |- logs/                    # Log query parsing and history support
|  |- runtime/                 # Server factory and explicit MCP tool registration
|  |- tools/                   # Public MCP tool entrypoints
|  |- ui/                      # UI tree parsing, selectors, actions, and normalization
|  |- utils/                   # Compatibility wrappers
|  |- harmonyos/               # HarmonyOS on-device adapter (TCP hdc client + standalone MCP server + stubs)
|  `- _common/                 # Shared runtime infrastructure bundled in this package
|- tests/unit/                 # Unit tests grouped by domain
|- docs/                       # Public tool and log query documentation
|- scripts/                    # Release helpers
|- pyproject.toml              # Project metadata and build config
|- uv.lock
|- README.md
```

## Requirements

- Python 3.12+
- DevEco Studio 5.0+
- HarmonyOS SDK toolchains, including `hdc`
- `uv`

### HarmonyOS on-device (additional)

- No DevEco Studio or `pip`/`uv` needed — stubs are bundled in-repo
- hdc server must be started in TCP mode from HiShell (see [Run](#harmonyos-on-device))

## Install

Install from PyPI:

```bash
pip install harmonyos-dev-mcp
```

Install from source for local development:

```bash
uv sync
```

Use `uv run` for development commands so Python resolves this checkout instead
of another globally installed `harmonyos-dev-mcp` version:

```bash
uv run python -c "import harmonyos_dev_mcp; print(harmonyos_dev_mcp.__file__)"
```

## Run

### Windows / macOS

```bash
uv run harmonyos-dev-mcp
```

### HarmonyOS (On-Device)

On HarmonyOS devices, the sandbox blocks subprocess `hdc` calls (UDS isolation)
and Python native extensions (`pydantic_core` .so blocked by SELinux). The
`harmonyos/` adapter solves both:

1. **TCP hdc client** — connects to hdc server over TCP directly, no subprocess
2. **Standalone MCP server** — pure Python JSON-RPC over stdio, no `fastmcp`
3. **Bundled stubs** — `fastmcp`/`mcp`/`loguru` stubs shipped in-repo

All 18 tools work without modification — `hdc_base.py` checks `HDC_USE_TCP=1`
and routes commands through TCP instead of subprocess.

**Prerequisites** (one-time, in HiShell):

```bash
hdc -s 0.0.0.0:8710 start -r
hdc tconn 127.0.0.1:$(param get persist.hdc.port)
```

**Run:**

```bash
HDC_USE_TCP=1 \
HARMONYOS_HDC_SERVER=127.0.0.1:8710 \
PYTHONPATH=<repo>/src/harmonyos_dev_mcp/harmonyos/stubs:<repo>/src \
python3 -c "from harmonyos_dev_mcp.harmonyos.mcp_server import main; main()"
```

> `python3 -m` and script-file invocation fail on HarmonyOS due to
> `libpython3.12.so` not loading in subprocess context. Use `-c` instead.

**One-command setup** (auto-detects Python, SDK, hdc; outputs importable JSON):

```bash
bash src/harmonyos_dev_mcp/harmonyos/setup.sh
```

Check connected devices:

```bash
hdc list targets
```

Use wireless debugging by IP:

```python
await list_devices(hdc_server="192.168.43.34:35215")
await install_app(r"C:\path\to\app.hap", hdc_server="192.168.43.34:35215")
```

Or set a default endpoint:

```bash
set HARMONYOS_HDC_SERVER=192.168.43.34:35215
```

## Documentation

- [Tool Reference](docs/tool_reference.md)
- [Logs Query Guide](docs/logs_query.md)

## Build Examples

Build a debug HAP:

```python
await build_app(r"C:\path\to\project", target="hap", build_mode="debug", product="default")
```

Build HSP modules and integrate them into a HAP:

```python
await build_app(
    r"C:\path\to\project",
    target="hap",
    build_mode="debug",
    product="default",
    include_hsp=True,
    hsp_module_names=["library_one", "library_two"],
)
```

Build an HNP-injected HAP:

```python
await build_app(r"C:\path\to\project", target="hnp", build_mode="debug", product="default")
```

## Development

Run unit tests:

```bash
uv run pytest tests/unit -v
```

Run with coverage:

```bash
uv run pytest tests/unit -v --cov=harmonyos_dev_mcp
```

Build package artifacts:

```bash
uv build --out-dir dist --clear
```

## Notes

- `build_app` is a long-running tool. Set MCP `tools/call timeout` to at least `60s`, and prefer `120s` for cold builds.
- `build_app target="hnp"` builds a base HAP, injects module HNP packages from `entry/hnp`, and signs the HAP through SDK packaging tools.
- `build_app target="hsp"` builds shared modules; `build_app target="hap" include_hsp=true` can integrate one or more HSP outputs into the HAP.
- `logs_query` supports `errors` and `markers` modes.
- The shared infrastructure that used to live in a separate common package is bundled in `harmonyos_dev_mcp._common`.
- On HarmonyOS devices, set `HDC_USE_TCP=1` to switch from subprocess `hdc` calls to direct TCP connections. This bypasses the sandbox UDS isolation. See [HarmonyOS (On-Device)](#harmonyos-on-device) for details.

## License

Apache License 2.0
