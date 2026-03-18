# query_package

统一包查询工具，支持：
- 列包：`info_type=list`
- 查能力：`info_type=abilities`
- 查主入口：`info_type=main_ability`
- 查权限：`info_type=permissions`

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `device_id` | string | `null` | 设备 ID，空时自动选第一台在线设备 |
| `bundle_name` | string | `null` | 应用包名 |
| `keyword` | string | `null` | 仅在 `list` 模式下生效，用于过滤包名 |
| `info_type` | string | `list` | `list/abilities/main_ability/permissions` |

规则：
- 当 `info_type` 为 `abilities/main_ability/permissions` 时，必须传 `bundle_name`。
- 当传入 `bundle_name` 且 `info_type=list` 时，会自动切到 `abilities`。

## 返回结构

工具外层为 MCP 标准结构，业务数据在 `structuredContent`：

```json
{
  "tool": "query_package",
  "ok": true,
  "result": {},
  "error": null,
  "meta": {}
}
```

失败时：

```json
{
  "tool": "query_package",
  "ok": false,
  "result": {},
  "error": {
    "code": "MISSING_BUNDLE_NAME",
    "detail": "info_type=\"main_ability\" requires bundle_name"
  },
  "meta": {}
}
```

`error` 仅包含 `code/detail`，不再包含历史字段。

## 结果示例

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

