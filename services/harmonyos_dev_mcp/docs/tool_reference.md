# HarmonyOS Dev MCP Tool Reference

This document describes the public MCP tools exposed by `harmonyos_dev_mcp`. It is based on the current implementation in `src/harmonyos_dev_mcp/tools/`.

## Shared Response Shape

All tools return the same top-level MCP shape:

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

All parameter examples below show the `arguments` payload only.

## General Tools

### `list_devices`

Purpose: list connected HarmonyOS devices with basic information.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| none | - | - | - | No arguments |

Key result fields:

- `devices`
- `count`

Example:

```json
{}
```

### `query_package`

Purpose: query installed packages, abilities, main ability, or permissions.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `bundle_name` | string | Conditional | `null` | Required for `abilities`, `main_ability`, `permissions` |
| `keyword` | string | No | `null` | Used only for package listing |
| `info_type` | string | No | `list` | One of `list`, `abilities`, `main_ability`, `permissions` |

Rules:

- `info_type="basic"` is not supported.
- `info_type="list"` cannot be combined with `bundle_name`.
- `bundle_name` is required when `info_type` is `abilities`, `main_ability`, or `permissions`.

Key result fields:

- `packages`, `count` for `list`
- `abilities`, `modules`, `main_ability`, `ability_count` for `abilities`
- `ability_name`, `module_name`, `candidates`, `recommended` for `main_ability`
- `requested_permissions`, `permission_count` for `permissions`

Common errors:

- `INVALID_INFO_TYPE`
- `MISSING_BUNDLE_NAME`
- `PARAM_CONFLICT`

Examples:

```json
{
  "device_id": "3QC0124C11000711",
  "info_type": "list"
}
```

```json
{
  "device_id": "3QC0124C11000711",
  "bundle_name": "com.example.app",
  "info_type": "main_ability"
}
```

### `logs_query`

Purpose: query HarmonyOS logs for actionable errors or business markers.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `logs` | string[] | No | `null` | Inline raw log lines, highest priority source |
| `input_file` | string | No | `null` | Single local log file |
| `input_files` | string[] | No | `null` | Multiple local log files |
| `lines` | int | No | `100` | Max returned items |
| `level` | string | No | `null` | Minimum level filter |
| `tag` | string | No | `null` | Structured tag filter |
| `tag_search` | string | No | `null` | Raw tag text filter |
| `keyword` | string | No | `null` | Raw keyword filter |
| `domain` | string | No | `null` | Hilog domain filter |
| `pid` | int | No | `null` | Strict PID filter |
| `package_name` | string | No | `null` | Business package relevance filter |
| `start_time` | string | No | `null` | `HH:MM:SS` or `YYYY-MM-DD HH:MM:SS` |
| `end_time` | string | No | `null` | Same format as `start_time` |
| `seconds` | int | No | `null` | Last N seconds |
| `save_path` | string | No | `null` | Optional output snapshot path |
| `time_expr` | string | No | `null` | Natural language time expression |
| `include_crash` | bool | No | `false` | Try to fetch matching crash artifacts |
| `mode` | string | No | `errors` | `errors` or `markers` |
| `marker_keywords` | string[] | No | built-in defaults | Used mainly in `markers` mode |
| `fallback_to_historical` | bool | No | `false` | Realtime first, historical on fallback |
| `realtime_wait_ms` | int | No | `1000` | Realtime sampling window |
| `context_lines` | int | No | `0` | Context before/after each item |

Source priority:

- `logs`
- `input_file` / `input_files`
- device capture

Key result fields:

- `query_mode`
- `source_attempted`
- `source_used`
- `matched`
- `match_count`
- `group_count`
- `items`
- `filters_applied`
- `saved_path`
- `crash_info`

Common errors:

- `INVALID_QUERY_MODE`
- `INVALID_PARAM`
- `FILE_NOT_FOUND`
- `FILE_TOO_LARGE`
- `PATH_NOT_ALLOWED`

Examples:

```json
{
  "mode": "errors",
  "level": "E",
  "lines": 200
}
```

```json
{
  "mode": "markers",
  "package_name": "com.huawei.securitytool",
  "marker_keywords": ["saveResult", "errorcode is = 0"],
  "seconds": 30,
  "realtime_wait_ms": 1500
}
```

Detailed guide:

- [logs_query.md](C:/Users/mu/Desktop/code/mcp_ho_dev/services/harmonyos_dev_mcp/docs/logs_query.md)

## Build Tools

### `build_app`

Purpose: build HarmonyOS artifacts through hvigor.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `project_path` | string | Yes | - | Must be an existing directory |
| `build_mode` | string | No | `debug` | `debug` or `release` |
| `target` | string | No | `hap` | `hap`, `har`, `app`, or `hnp` |
| `product` | string | No | `default` | Hvigor product |
| `module_name` | string | Conditional | `null` | Required when `target="har"` |
| `is_clean` | bool | No | `false` | Clean before build |

Rules:

- `project_path` must exist.
- `module_name` is required when `target="har"`.
- `target="hnp"` builds a base HAP, repacks module HNP packages from directories like `entry/hnp/arm64-v8a/*.hnp`, and signs the HAP with SDK tools.
- `target="hnp"` does not run project-local `.bat`, `.ps1`, or `.sh` build scripts.
- `build_app` is long-running. Set MCP timeout to at least `60s`; prefer `120s` for cold builds.

Key result fields:

- `output_path`
- `artifact_source`
- `sign_status`
- `target`
- `build_mode`
- `product`
- `module_name`
- `is_clean`
- `duration`
- `errors`
- `error_count`

Common errors:

- `INVALID_PROJECT_PATH`
- `INVALID_BUILD_MODE`
- `INVALID_BUILD_TARGET`
- `MISSING_MODULE_NAME`
- `BUILD_TIMEOUT`
- `HNP_PACKAGE_NOT_FOUND`
- `HNP_TOOLCHAIN_NOT_FOUND`
- `HNP_PACKAGING_INPUT_MISSING`
- `HNP_SIGN_FAILED`

Example:

```json
{
  "project_path": "C:/work/security_tool",
  "build_mode": "debug",
  "target": "hap"
}
```

### `install_app`

Purpose: install a `.hap` or `.app` package onto the device.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `hap_path` | string | Yes | - | Must end with `.hap` or `.app` |
| `device_id` | string | No | auto-resolve | Target device |

Key result fields:

- `device_id`
- `hap_path`

Common errors:

- `MISSING_HAP_PATH`
- `INVALID_APP_PACKAGE`
- `INSTALL_FAILED`

### `run_app`

Purpose: launch an app and verify its window.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `bundle_name` | string | Yes | - | Target app bundle |
| `device_id` | string | No | auto-resolve | Target device |
| `ability_name` | string | No | `null` | Explicit launch ability |
| `module_name` | string | No | `null` | Explicit module |
| `auto_detect` | bool | No | `true` | Resolve main ability automatically |

Behavior:

- When `ability_name` is omitted and `auto_detect=true`, the tool tries `get_main_ability` first.
- If that fails, it falls back to visible `page` abilities, then any `page` ability.

Key result fields:

- `bundle_name`
- `ability_name`
- `module_name`
- `auto_detected`
- `command_success`
- `window_found`
- `window`

Common errors:

- `ABILITY_RESOLUTION_FAILED`
- `RUN_APP_FAILED`

### `uninstall_app`

Purpose: uninstall an app from the device.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `bundle_name` | string | Yes | - | Target app bundle |
| `device_id` | string | No | auto-resolve | Target device |

Common errors:

- `MISSING_BUNDLE_NAME`
- `UNINSTALL_FAILED`

## UI Tools

### `click_element`

Purpose: click or double-click a target.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `x` | int | Conditional | `null` | Coordinate mode |
| `y` | int | Conditional | `null` | Coordinate mode |
| `element_handle` | object | Conditional | `null` | Handle from `find_element` or `wait_element` |
| `text` | string | Conditional | `null` | Search mode |
| `element_type` | string | Conditional | `null` | Search mode |
| `element_id` | string | Conditional | `null` | Search mode |
| `double_click` | bool | No | `false` | Use double click |
| `bundle_name` | string | No | `null` | Search scope only |

Rules:

- Provide one mode only: coordinates, `element_handle`, or search criteria.
- Coordinates cannot be combined with `element_handle` or search criteria.
- `element_handle` may be refreshed internally through `lookup_hint` if stale.

Key result fields:

- `x`
- `y`
- `resolved_via`
- `handle_refreshed`
- `element_handle`

Common errors:

- `PARAM_CONFLICT`
- `MISSING_PARAMS`
- `INVALID_ELEMENT_HANDLE`
- `ELEMENT_NOT_FOUND`
- `AMBIGUOUS_ELEMENT_MATCH`

### `long_press_element`

Purpose: long press a target.

Parameters:

Same resolution modes as `click_element`, except no `double_click`.

Common errors:

- `PARAM_CONFLICT`
- `MISSING_PARAMS`
- `INVALID_ELEMENT_HANDLE`
- `ELEMENT_NOT_FOUND`

### `swipe`

Purpose: perform swipe by direction or explicit coordinates.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `from_x` | int | Conditional | `null` | Coordinate mode |
| `from_y` | int | Conditional | `null` | Coordinate mode |
| `to_x` | int | Conditional | `null` | Coordinate mode |
| `to_y` | int | Conditional | `null` | Coordinate mode |
| `direction` | string | Conditional | `null` | Direction mode |
| `speed` | int | No | `600` | Swipe speed |

Rules:

- `direction` cannot be combined with explicit coordinates.
- Coordinate mode requires all four coordinate values.

Key result fields:

- `from_x`
- `from_y`
- `to_x`
- `to_y`
- `direction`

Common errors:

- `PARAM_CONFLICT`
- `MISSING_PARAMS`

### `input_text`

Purpose: input text into a field by coordinates, handle, or search criteria.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `x` | int | Conditional | `null` | Coordinate mode |
| `y` | int | Conditional | `null` | Coordinate mode |
| `text` | string | Yes | - | Text to input |
| `element_handle` | object | Conditional | `null` | Handle mode |
| `element_text` | string | Conditional | `null` | Search mode text |
| `element_type` | string | Conditional | `null` | Search mode type |
| `element_id` | string | Conditional | `null` | Search mode id |
| `bundle_name` | string | No | `null` | Search scope only |

Rules:

- `text` is always required.
- Use one resolution mode only.
- Do not pass `element_handle` as a JSON string.

Key result fields:

- `text`
- `x`
- `y`
- `resolved_via`
- `handle_refreshed`
- `element_handle`

Common errors:

- `MISSING_TEXT`
- `PARAM_CONFLICT`
- `MISSING_PARAMS`
- `INVALID_ELEMENT_HANDLE`
- `ELEMENT_NOT_FOUND`

Correct example:

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

Incorrect example:

```json
{
  "element_handle": "{\"window_id\":80,\"id\":\"420\"}",
  "text": "security"
}
```

### `press_key`

Purpose: simulate supported system keys.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `key` | string | Yes | - | Key name or supported alias |

Supported aliases include:

- `home`
- `back`
- `power`
- `volume_up`
- `volume_down`

Supported normalized keys:

- `Back`
- `Camera`
- `DPadCenter`
- `DPadDown`
- `DPadLeft`
- `DPadRight`
- `DPadUp`
- `Enter`
- `Escape`
- `Home`
- `Menu`
- `Notification`
- `Power`
- `RecentApps`
- `Search`
- `VolumeDown`
- `VolumeUp`

Common errors:

- `MISSING_KEY`
- `INVALID_KEY`

### `find_element`

Purpose: search for UI elements and return reusable handles.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `text` | string | Conditional | `null` | Search criteria |
| `element_type` | string | Conditional | `null` | Search criteria |
| `element_id` | string | Conditional | `null` | Search criteria |
| `bundle_name` | string | No | `null` | Narrow search scope |
| `window_id` | int | No | `null` | Narrow search scope |

Rules:

- At least one of `text`, `element_type`, `element_id` is required.

Key result fields:

- `elements`
- `count`
- `elements[].element_handle`
- `elements[].lookup_is_broad`
- `elements[].bounds`

Common errors:

- `MISSING_SEARCH_CRITERIA`
- `ELEMENT_NOT_FOUND`

### `screenshot`

Purpose: take a full-screen or region screenshot.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `local_path` | string | No | auto-generated path | Output path |
| `display_id` | int | No | `0` | Full screenshot only |
| `left` | int | Conditional | `null` | Region bounds |
| `top` | int | Conditional | `null` | Region bounds |
| `right` | int | Conditional | `null` | Region bounds |
| `bottom` | int | Conditional | `null` | Region bounds |

Rules:

- Region screenshot requires `left`, `top`, `right`, and `bottom` together.
- If `local_path` is omitted, the tool generates a file under the user screenshots directory.

Key result fields:

- `local_path`
- `file_size`
- `bounds` for region screenshots

Common errors:

- `PARAM_CONFLICT`
- `SCREENSHOT_ERROR`

### `drag`

Purpose: drag from one coordinate to another.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `from_x` | int | Yes | - | Start coordinate |
| `from_y` | int | Yes | - | Start coordinate |
| `to_x` | int | Yes | - | End coordinate |
| `to_y` | int | Yes | - | End coordinate |
| `speed` | int | No | `600` | Drag speed |

Common errors:

- `MISSING_PARAMS`

## E2E Tools

### `get_ui_tree`

Purpose: fetch the UI tree for the global dump or a validated target window.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `bundle_name` | string | No | `null` | Resolve a target window first |
| `window_id` | int | No | `null` | Resolve and validate a target window |

Behavior:

- If `bundle_name` or `window_id` is provided, the tool validates the target window before fetching the tree.

Key result fields:

- `window_id`
- `validated_window_id`
- `validation_applied`
- `capture_scope`
- `ui_tree`
- `node_count`

Common errors:

- `WINDOW_RESOLUTION_ERROR`
- `UI_TREE_FETCH_ERROR`
- `INVALID_UI_TREE_PAYLOAD`

### `list_windows`

Purpose: list current windows on the device.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `bundle_name` | string | No | `null` | Filter by normalized bundle name |

Key result fields:

- `windows`
- `count`
- `total_count`

### `wait_element`

Purpose: wait for an element to become present or disappear.

Parameters:

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `device_id` | string | No | auto-resolve | Target device |
| `bundle_name` | string | No | `null` | Search scope |
| `window_id` | int | No | `null` | Search scope |
| `text` | string | Conditional | `null` | Search target |
| `element_type` | string | Conditional | `null` | Search target |
| `element_id` | string | Conditional | `null` | Search target |
| `state` | string | No | `found` | `found` or `gone` |
| `timeout_ms` | int | No | `5000` | Wait timeout |
| `interval_ms` | int | No | `300` | Poll interval and confirm interval |

Rules:

- At least one of `text`, `element_type`, `element_id` is required.
- `state` must be `found` or `gone`.
- `timeout_ms` and `interval_ms` must be `>= 0`.
- The tool performs a second confirmation when `interval_ms > 0` to reduce transient flakiness.

Key result fields:

- `state`
- `satisfied`
- `elapsed_ms`
- `element`

Common errors:

- `INVALID_WAIT_TARGET`
- `INVALID_WAIT_STATE`
- `INVALID_TIMEOUT`
- `INVALID_INTERVAL`
- `WAIT_TIMEOUT`

Example:

```json
{
  "text": "Login",
  "state": "found",
  "timeout_ms": 5000,
  "interval_ms": 300
}
```
