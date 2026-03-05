# HarmonyOS MCP Server

HarmonyOS MCP 服务端工程，包含：
- `harmonyos_mcp`：真机/模拟器设备、应用、UI、日志工具
- `harmonyos_compile_mcp`：编译链路相关工具
- `packages/common`：通用配置、容器、工具注册、服务基类

## 目录结构

```text
mcp_ho_dev/
├── packages/
│   └── common/
│       └── src/common/
├── services/
│   ├── harmonyos_mcp/
│   │   ├── src/harmonyos_mcp/
│   │   │   ├── tools/
│   │   │   └── utils/
│   │   └── docs/
│   └── harmonyos_compile_mcp/
├── pyproject.toml
└── README.md
```

## 运行

```bash
uv sync --all-packages
uv run harmonyos-mcp
```

## 工具列表（harmonyos_mcp）

- `general`: `list_devices`, `query_package`, `logs_query`
- `build`: `build_app`, `install_app`, `run_app`, `uninstall_app`
- `ui`: `screenshot`, `click_element`, `long_press_element`, `input_text`, `swipe`, `drag`, `press_key`, `find_element`
- `ui_tree`: `get_ui_tree`, `list_windows`

## 统一响应结构（本次重构）

所有工具返回 MCP 标准顶层结构：

```json
{
  "content": [
    {"type": "text", "text": "run_app: ok"}
  ],
  "structuredContent": {
    "tool": "run_app",
    "ok": true,
    "result": {},
    "error": null,
    "meta": {
      "request_id": "uuid",
      "timestamp": "2026-03-05T07:40:51.000000+00:00",
      "duration_ms": 321
    }
  },
  "isError": false
}
```

`structuredContent.error` 统一为：

```json
{
  "code": "ERROR_CODE",
  "detail": "human readable detail"
}
```

不再输出历史冗余字段：`hint`、`retryable`、`result_status` 等。

## 关键变更说明

### 1. 工具输出标准化

- 统一由 `services/harmonyos_mcp/tools/response.py` 生成 envelope。
- 工具内部统一使用：
  - `ok_result(...)`
  - `error_result(code, detail, result=...)`
  - `from_action_result(...)`

### 2. 错误结构精简

- 错误只保留 `code/detail`。
- `common` 与 `harmonyos_mcp` 两侧定义一致。

### 3. `run_app` 自动入口能力检测字段统一

- 候选入口字段统一为 `ability_name/module_name`。
- `run_app` 自动检测逻辑已按该结构读取，避免回退到错误默认能力名。

## 调用样例

### 成功

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

### 失败

```json
{
  "tool": "run_app",
  "ok": false,
  "result": {
    "device_id": "3QC0124C11000711",
    "bundle_name": "com.example.myapplication"
  },
  "error": {
    "code": "RUN_APP_FAILED",
    "detail": "应用窗口未出现（可能ability_name或module_name错误）"
  }
}
```

## 测试建议

```bash
PYTHONPATH=packages/common/src;services/harmonyos_mcp/src pytest services/harmonyos_mcp/tests/unit -q
PYTHONPATH=packages/common/src;services/harmonyos_mcp/src pytest packages/common/tests -q
```

