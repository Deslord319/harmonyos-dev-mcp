# HarmonyOS MCP Server

**HarmonyOS 设备自动化与 E2E 测试基础设施**

[![Version](https://img.shields.io/badge/version-0.7.0-blue)](RELEASE_NOTES.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![HarmonyOS](https://img.shields.io/badge/HarmonyOS-5.0+-green)](https://developer.huawei.com/consumer/cn/harmonyos/)

HarmonyOS MCP 服务端工程，提供：
- **设备自动化** - 真机/模拟器设备管理、应用安装/卸载、UI 交互
- **E2E 测试支持** - UI 树查询、窗口管理、元素等待
- **编译工具链** - 自动化构建、签名、部署
- **日志审计** - 安全事件查询、日志导出

> **最新版本**: v0.7.0 - 新增 E2E 测试工具，改进窗口解析和构建体验

## 目录结构

```text
mcp_ho_dev/
├── packages/
│   └── common/
│       └── src/common/
├── services/
│   ├── harmonyos_dev_mcp/
│   │   ├── src/harmonyos_dev_mcp/
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
uv run harmonyos-dev-mcp
```

## 工具列表

共 18 个工具，分为 4 类：

| 分类 | 工具 | 功能 |
|------|------|------|
| **General**<br>设备管理 | `list_devices` | 列出已连接设备 |
| | `query_package` | 查询应用安装状态 |
| | `logs_query` | 查询安全审计日志 |
| **Build**<br>构建部署 | `build_app` | 构建 HAP 包 |
| | `install_app` | 安装应用到设备 |
| | `run_app` | 启动应用 |
| | `uninstall_app` | 卸载应用 |
| **UI**<br>交互操作 | `screenshot` | 屏幕截图 |
| | `click_element` | 点击元素 |
| | `long_press_element` | 长按元素 |
| | `input_text` | 输入文本 |
| | `swipe` | 滑动操作 |
| | `drag` | 拖拽操作 |
| | `press_key` | 按键操作 |
| | `find_element` | 查找元素 |
| **E2E Test**<br>端到端测试 ⭐ | `get_ui_tree` | 获取 UI 树结构 |
| | `list_windows` | 列出所有窗口 |
| | `wait_element` | 等待元素出现 |

## 响应结构

所有工具返回统一的 MCP 标准格式：

```json
{
  "content": [{"type": "text", "text": "..."}],
  "structuredContent": {
    "tool": "tool_name",
    "ok": true,
    "result": {},
    "error": null,
    "meta": {
      "request_id": "uuid",
      "timestamp": "2026-03-13T00:00:00.000000+00:00",
      "duration_ms": 123
    }
  },
  "isError": false
}
```

错误响应：

```json
{
  "tool": "tool_name",
  "ok": false,
  "result": {...},
  "error": {
    "code": "ERROR_CODE",
    "detail": "人类可读的详细描述"
  }
}
```

## 快速开始

### 1. 安装依赖

```bash
uv sync --all-packages
```

### 2. 启动 MCP Server

```bash
uv run harmonyos-dev-mcp
```

### 3. 连接设备

确保设备已通过 HDC 连接：

```bash
hdc list targets
# 输出示例：3QC0124C11000711
```

## 使用示例

### 查询已安装应用

```python
result = await client.call_tool("query_package", {
    "device_id": "3QC0124C11000711",
    "info_type": "list"
})
# 返回：{"packages": ["com.example.app"], "count": 1}
```

### 点击 UI 元素

```python
await client.call_tool("click_element", {
    "device_id": "3QC0124C11000711",
    "text": "确定"
})
```

### 获取 UI 树

```python
ui_tree = await client.call_tool("get_ui_tree", {
    "device_id": "3QC0124C11000711"
})
```

### 等待元素出现

```python
await client.call_tool("wait_element", {
    "device_id": "3QC0124C11000711",
    "text": "欢迎",
    "timeout": 10000
})
```

## 环境要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 运行环境 |
| DevEco Studio | 5.0+ | HarmonyOS SDK |
| hdc | 最新版 | 设备连接工具 |
| uv | 最新版 | Python 包管理 |

## MCP 客户端配置

### OpenCode 配置

在一下目录创建 `~/.conifg/opencode/opencode.jsonc`：

```json
{
  "mcp": {
    "harmonyos-dev-mcp": {
      "type": "local",
      "command": ["uv", "run", "harmonyos-dev-mcp"],
      "enabled": true,
      "timeout": 60000,
      "env": {
      }
    }
  }
}
```

### 故障排查

**问题**: MCP Server 无法启动

```bash
# 手动测试启动
uv run harmonyos-dev-mcp

# 检查设备连接
hdc list targets

# 查看日志
tail -f logs/harmonyos-dev-mcp.stderr.log
```

**问题**: 工具调用超时

- 确保设备已连接且屏幕已解锁
- 检查 HDC 路径配置（DevEco Studio 设置）
- 增加客户端超时设置（建议 30s+）

## 相关文档

## 开发

### 运行测试

```bash
# 单元测试
uv run pytest services/harmonyos_dev_mcp/tests/unit -v

# 配置测试
uv run pytest services/harmonyos_dev_mcp/tests/unit/test_config.py -v

# E2E 工具测试
uv run pytest services/harmonyos_dev_mcp/tests/unit/test_e2e_tools.py -v
```

### 构建包

```bash
# 构建 common 包
cd packages/common && uv build

# 构建 harmonyos_dev_mcp 包
cd services/harmonyos_dev_mcp && uv build
```

## License

Apache License 2.0

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
PYTHONPATH=packages/common/src;services/harmonyos_dev_mcp/src pytest services/harmonyos_dev_mcp/tests/unit -q
PYTHONPATH=packages/common/src;services/harmonyos_dev_mcp/src pytest packages/common/tests -q
```