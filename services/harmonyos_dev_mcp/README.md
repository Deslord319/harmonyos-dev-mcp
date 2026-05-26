# HarmonyOS Dev MCP

`harmonyos_dev_mcp` is the current mainline HarmonyOS MCP service for device automation, app deployment, UI interaction, E2E support, and log-based validation.

## What It Provides

This service exposes HarmonyOS automation capabilities as MCP tools so they can be called from:

- MCP clients
- AI agents
- test platforms
- custom automation scripts

Typical use cases:

- build and install a HarmonyOS app
- launch an app and verify the target window
- find, click, input, swipe, and capture screenshots
- wait for UI state changes
- inspect the UI tree
- query logs for errors or business markers

## Requirements

- Python 3.12+
- DevEco Studio 5.0+
- `hdc`
- `uv`

## Run

```bash
uv sync --all-packages
uv run harmonyos-dev-mcp
```

## Tool Groups

- General: `list_devices`, `query_package`, `logs_query`
- Build: `build_app`, `install_app`, `run_app`, `uninstall_app`
- UI: `screenshot`, `click_element`, `long_press_element`, `input_text`, `swipe`, `drag`, `press_key`, `find_element`
- E2E: `get_ui_tree`, `list_windows`, `wait_element`

## Parameter Docs

The detailed parameter reference is maintained here:

- [Tool Reference](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp/docs/tool_reference.md)

That document covers:

- parameter names and types
- defaults
- required and optional inputs
- mutual exclusion and dependency rules
- key result fields
- common error codes
- minimal call examples

## Important Call Notes

- `build_app` is long-running. Set MCP `tools/call timeout` to at least `60s`, and prefer `120s` for cold builds.
- `build_app` defaults to `build_mode="debug"`, `target="hap"`, and `product="default"`.
- `build_app target="hsp"` builds a shared module through hvigor. Pass `module_name` for the shared module.
- `build_app target="hap" include_hsp=true` builds the base HAP, builds one or more `type="shared"` HSP modules, injects them into `shared_libs/`, and re-signs the HAP with SDK tools.
- HAP builds with `include_hsp=true` return `hsp_output_paths` so callers can install the generated HSP files alongside the HAP when the device installer requires shared modules as separate install units.
- `hsp_module_name` can name one HSP module or a comma/semicolon separated list; `hsp_module_names` accepts an explicit list. When both are omitted, the tool discovers all modules whose `src/main/module.json5` declares `type="shared"`.
- `build_app target="hnp"` builds a normal HAP first, injects built HNP packages from the module `hnp` directory, and re-signs the output with SDK tools. It does not call project-local `.bat`, `.ps1`, or `.sh` scripts.
- HNP signing reads `build-profile.json5`. If DevEco stores encrypted passwords there, set `HAP_SIGN_PASSWORD`, or set `HAP_KEY_PASSWORD` and `HAP_STORE_PASSWORD`, so `hap-sign-tool.jar` can sign with plaintext credentials.
- If a project already defines hvigor signing in `build-profile.json5`, `build_app` returns the hvigor artifact directly.
- If hvigor only produces an unsigned HAP and the project uses a project-local MDM signing flow, `build_app` tries `project_root/hapsigner/2-<build_mode>-sign.bat`.
- `query_package.info_type` supports only `list`, `abilities`, `main_ability`, and `permissions`.
- `input_text.element_handle` must be an object returned by `find_element` or `wait_element`, not a JSON string.
- `logs_query` supports `mode="errors"` and `mode="markers"`.
- `logs_query` defaults to realtime sampling and does not fall back to historical logs unless `fallback_to_historical=true`.

## Examples

Query installed packages:

```python
result = await client.call_tool("query_package", {
    "device_id": "3QC0124C11000711",
    "info_type": "list"
})
```

Click an element using a handle from `find_element`:

```python
element = await client.call_tool("find_element", {
    "device_id": "3QC0124C11000711",
    "text": "Login"
})

await client.call_tool("click_element", {
    "device_id": "3QC0124C11000711",
    "element_handle": element["structuredContent"]["result"]["elements"][0]["element_handle"]
})
```

Fetch the UI tree:

```python
ui_tree = await client.call_tool("get_ui_tree", {
    "device_id": "3QC0124C11000711"
})
```

## Result Shape

All tools return a unified MCP envelope:

```json
{
  "content": [{"type": "text", "text": "tool_name: ok"}],
  "structuredContent": {
    "tool": "tool_name",
    "ok": true,
    "result": {},
    "error": null,
    "meta": {
      "request_id": "uuid",
      "timestamp": "2026-03-19T00:00:00+00:00",
      "duration_ms": 123
    }
  },
  "isError": false
}
```

## Development

Run tests:

```bash
uv run pytest services/harmonyos_dev_mcp/tests/unit -v
```

## Release 0.7.6

- Added `build_app target="hnp"` for direct HNP HAP packaging and signing.
- Uses the SDK `app_packing_tool.jar` and `hap-sign-tool.jar` instead of project-local build scripts.
- Detects HNP packages under module `hnp` directories such as `entry/hnp/arm64-v8a/*.hnp`.
- Returns `artifact_source="hnp_direct"` and a signed `*-signed-hnp.hap` output.
- Added edge-case coverage for missing HNP packages, missing SDK packaging jars, missing hvigor packaging inputs, and ordinary `target="hap"` builds that should not trigger HNP repackaging.

## Next Release

- Added `build_app target="hsp"` for hvigor shared module builds.
- Added `build_app target="hap" include_hsp=true` to build HSP modules, inject them under `shared_libs/`, and sign the integrated HAP with SDK tools.
- Added auto-discovery for `type="shared"` modules, plus `hsp_module_name` / `hsp_module_names` to select one or more shared modules.
- Merged HSP `pack.info` metadata into the repacked HAP and returned `hsp_output_paths` for multi-file installation flows.
- Added unit coverage for HSP module validation, HSP build command dispatch, and HAP repack/sign with `--shared-libs-path`.

## Docs

- [Tool Reference](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp/docs/tool_reference.md)
- [Logs Query Guide](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp/docs/logs_query.md)
