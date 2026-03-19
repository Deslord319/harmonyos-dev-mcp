# HarmonyOS Dev MCP

**HarmonyOS 设备自动化与 E2E 测试 MCP 服务**

[![Version](https://img.shields.io/badge/version-0.7.0-blue)](services/harmonyos_dev_mcp/pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![HarmonyOS](https://img.shields.io/badge/HarmonyOS-5.0+-green)](https://developer.huawei.com/consumer/cn/harmonyos/)

当前社区主线只包含 `harmonyos_dev_mcp` 服务。`services/harmonyos_compile_mcp/` 目录暂为预留，不属于当前 workspace，也不作为对外发布内容。

## 目录结构

```text
mcp_ho_dev/
├── packages/
│   └── common/
│       └── src/common/
├── services/
│   └── harmonyos_dev_mcp/
│       ├── docs/
│       ├── src/harmonyos_dev_mcp/
│       └── tests/
├── pyproject.toml
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
uv sync --all-packages
```

### 2. 启动服务

```bash
uv run harmonyos-dev-mcp
```

### 3. 确认设备连接

```bash
hdc list targets
```

## 工具列表

当前提供 18 个工具，分为 4 类：

| 分类 | 工具 |
|------|------|
| General | `list_devices` `query_package` `logs_query` |
| Build | `build_app` `install_app` `run_app` `uninstall_app` |
| UI | `screenshot` `click_element` `long_press_element` `input_text` `swipe` `drag` `press_key` `find_element` |
| E2E | `get_ui_tree` `list_windows` `wait_element` |

## 环境要求

| 工具 | 版本 |
|------|------|
| Python | 3.12+ |
| DevEco Studio | 5.0+ |
| hdc | 最新版 |
| uv | 最新版 |

## MCP 客户端配置

OpenCode 配置文件路径：

```text
~/.config/opencode/opencode.jsonc
```

示例：

```json
{
  "mcp": {
    "harmonyos-dev-mcp": {
      "type": "local",
      "command": ["uv", "run", "harmonyos-dev-mcp"],
      "enabled": true,
      "timeout": 60000,
      "env": {}
    }
  }
}
```

## 开发

运行主线单测：

```bash
uv run pytest services/harmonyos_dev_mcp/tests/unit -v
```

构建包：

```bash
cd packages/common
uv build

cd ../../services/harmonyos_dev_mcp
uv build
```

## 故障排查

无法启动服务时，优先检查：

- `uv run harmonyos-dev-mcp` 是否能本地直接启动
- `hdc list targets` 是否能看到设备
- `logs/` 目录下是否生成当前服务日志文件

工具调用超时时，优先检查：

- 设备是否已连接且屏幕已解锁
- DevEco Studio / SDK / `hdc` 路径是否可用
- MCP 客户端超时时间是否至少为 60 秒

## 相关文档

- `services/harmonyos_dev_mcp/docs/logs_query.md`
- `services/harmonyos_dev_mcp/docs/query_package.md`

## MCP 调用注意事项

- `query_package.info_type` 仅支持 `list`、`abilities`、`main_ability`、`permissions`。
- `query_package.info_type="basic"` 不受支持。
- `input_text.element_handle` 必须直接传对象，推荐复用 `find_element` 或 `wait_element` 返回的 `element_handle`。
- 不要把 `input_text.element_handle` 作为 JSON 字符串传入。

## License

Apache License 2.0
