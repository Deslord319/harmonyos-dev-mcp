# query_package

Unified package query tool. Supported modes:

- List packages: `info_type=list`
- Query abilities: `info_type=abilities`
- Query main ability: `info_type=main_ability`
- Query permissions: `info_type=permissions`

## Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `device_id` | string | `null` | Device ID. Uses the first online device when omitted. |
| `bundle_name` | string | `null` | Target bundle name. |
| `keyword` | string | `null` | Only used when `info_type=list`. |
| `info_type` | string | `list` | Only supports `list`, `abilities`, `main_ability`, `permissions`. |

Rules:

- When `info_type` is `abilities`, `main_ability`, or `permissions`, `bundle_name` is required.
- When `bundle_name` is provided together with `info_type=list`, the tool automatically switches to `abilities`.
- `info_type="basic"` is not supported.

## MCP Response

The tool returns a standard MCP envelope and places business data under `structuredContent.result`.

Success:

```json
{
  "tool": "query_package",
  "ok": true,
  "result": {},
  "error": null,
  "meta": {}
}
```

Failure:

```json
{
  "tool": "query_package",
  "ok": false,
  "result": {},
  "error": {
    "code": "INVALID_INFO_TYPE",
    "detail": "invalid info_type. supported values: list, abilities, main_ability, permissions; \"basic\" is not supported"
  },
  "meta": {}
}
```

## Examples

### 1. `info_type=list`

```json
{
  "tool": "query_package",
  "ok": true,
  "result": {
    "device_id": "3QC0124C11000711",
    "info_type": "list",
    "packages": ["com.example.myapplication"],
    "count": 1,
    "keyword": ""
  },
  "error": null
}
```

### 2. `info_type=abilities`

```json
{
  "tool": "query_package",
  "ok": true,
  "result": {
    "device_id": "3QC0124C11000711",
    "info_type": "abilities",
    "bundle_name": "com.example.myapplication",
    "abilities": [
      {"name": "EntryAbility", "module": "entry", "type": "page"}
    ],
    "modules": ["entry"],
    "main_ability": {"name": "EntryAbility", "module": "entry", "type": "page"},
    "ability_count": 1
  },
  "error": null
}
```

### 3. `info_type=main_ability`

```json
{
  "tool": "query_package",
  "ok": true,
  "result": {
    "device_id": "3QC0124C11000711",
    "info_type": "main_ability",
    "bundle_name": "com.example.myapplication",
    "ability_name": "EntryAbility",
    "module_name": "entry",
    "candidates": [
      {
        "ability_name": "EntryAbility",
        "module_name": "entry",
        "is_entry_module": true,
        "is_entry_main_ability": true,
        "is_launcher": true,
        "source": "entryModule.mainAbility, action.system.home",
        "visible": true,
        "type": "page"
      }
    ],
    "recommended": 0
  },
  "error": null
}
```

### 4. `info_type=permissions`

```json
{
  "tool": "query_package",
  "ok": true,
  "result": {
    "device_id": "3QC0124C11000711",
    "info_type": "permissions",
    "bundle_name": "com.example.myapplication",
    "requested_permissions": ["ohos.permission.INTERNET"],
    "permission_count": 1
  },
  "error": null
}
```
