# HarmonyOS Dev MCP

`harmonyos_dev_mcp` is the current community mainline service for HarmonyOS device automation, app deployment, UI interaction, and E2E assistance.

## Run

```bash
uv sync --all-packages
uv run harmonyos-dev-mcp
```

## Requirements

- Python 3.12+
- DevEco Studio 5.0+
- `hdc`
- `uv`

## Tool Groups

- General: `list_devices` `query_package` `logs_query`
- Build: `build_app` `install_app` `run_app` `uninstall_app`
- UI: `screenshot` `click_element` `long_press_element` `input_text` `swipe` `drag` `press_key` `find_element`
- E2E: `get_ui_tree` `list_windows` `wait_element`

## Call Notes

- `build_app` is a long-running tool.
- Set MCP `tools/call timeout` to at least `60s`.
- For cold builds, `120s` is the recommended timeout.
- `build_app` defaults to `build_mode="debug"`, `target="hap"`, and `product="default"`.
- If a project already defines hvigor signing in `build-profile.json5`, `build_app` returns the hvigor output artifact directly.
- If a project still uses a project-local MDM signing flow and hvigor only produces an unsigned HAP, `build_app` will try `project_root/hapsigner/2-<build_mode>-sign.bat` automatically. On success, `output_path` switches to the signed artifact, usually `project_root/hapsigner/signApp.hap`.
- `logs_query` supports `mode="errors"` and `mode="markers"`.
- `logs_query` defaults to realtime sampling and does not fallback to historical logs unless `fallback_to_historical=true`.
- `logs_query.package_name` is no longer reduced to a single pid by default.
- `query_package.info_type` only supports `list`, `abilities`, `main_ability`, and `permissions`.
- `query_package.info_type="basic"` is not supported.
- `input_text.element_handle` must be an object returned by `find_element` or `wait_element`.
- Do not pass `input_text.element_handle` as a JSON string.
- For MDM-style projects, keep signing materials and scripts under `project_root/hapsigner/`. The MCP fallback only runs project-local scripts; it does not synthesize signing config.

Correct `input_text` example:

```json
{
  "element_handle": {
    "window_id": 80,
    "id": "420",
    "compid": "80:420",
    "type": "TextInput"
  },
  "text": "security"
}
```

Incorrect `input_text` example:

```json
{
  "element_handle": "{\"window_id\":80,\"id\":\"420\"}",
  "text": "security"
}
```

## Test

```bash
uv run pytest services/harmonyos_dev_mcp/tests/unit -v
```

## Docs

- `docs/logs_query.md`
