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
- `logs_query` supports `mode="errors"` and `mode="markers"`.
- `logs_query` defaults to realtime sampling and does not fallback to historical logs unless `fallback_to_historical=true`.
- `logs_query.package_name` is no longer reduced to a single pid by default.
- `query_package.info_type` only supports `list`, `abilities`, `main_ability`, and `permissions`.
- `query_package.info_type="basic"` is not supported.
- `input_text.element_handle` must be an object returned by `find_element` or `wait_element`.
- Do not pass `input_text.element_handle` as a JSON string.

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
- `docs/query_package.md`
