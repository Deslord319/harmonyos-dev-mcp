# HarmonyOS Dev MCP

**HarmonyOS 设备自动化与 E2E 测试 MCP 服务**

[![Version](https://img.shields.io/badge/version-0.7.3-blue)](services/harmonyos_dev_mcp/pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![HarmonyOS](https://img.shields.io/badge/HarmonyOS-5.0+-green)](https://developer.huawei.com/consumer/cn/harmonyos/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

> **HarmonyOS MCP 服务端工程**，提供设备自动化、应用部署、UI 交互和 E2E 测试辅助能力。
> 
> 当前社区主线只包含 `harmonyos_dev_mcp` 服务。`services/harmonyos_compile_mcp/` 目录暂为预留，不属于当前 workspace 发布内容。

---

## 目录结构

```text
mcp_ho_dev/
├── packages/
│   └── common/                      # 通用组件库 (harmonyos-mcp-common)
│       ├── src/common/
│       │   ├── config/              # 配置管理
│       │   ├── server/              # MCP 服务器基类
│       │   ├── tools/               # 工具注册与响应
│       │   ├── types/               # 类型定义
│       │   └── utils/               # 工具函数
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
├── services/
│   └── harmonyos_dev_mcp/           # HarmonyOS 开发 MCP 服务
│       ├── src/harmonyos_dev_mcp/
│       │   ├── tools/
│       │   │   ├── build.py         # 构建/部署工具
│       │   │   ├── device_support.py
│       │   │   ├── e2e.py           # E2E 测试工具
│       │   │   ├── general.py       # 通用工具
│       │   │   ├── log/
│       │   │   │   ├── query.py     # 日志查询
│       │   │   │   ├── parser.py
│       │   │   │   └── historian.py
│       │   │   └── ui.py            # UI 交互工具
│       │   ├── utils/
│       │   │   ├── hdc/             # HDC 封装层
│       │   │   ├── normalizers/     # 数据标准化
│       │   │   ├── parsers/         # 解析器
│       │   │   └── wrappers/        # 外部工具封装
│       │   ├── config.py
│       │   ├── container.py
│       │   ├── server.py
│       │   └── types.py
│       ├── docs/                    # 使用文档
│       ├── tests/
│       │   └── unit/
│       ├── pyproject.toml
│       └── README.md
├── pyproject.toml                   # Workspace 配置
├── uv.lock
└── README.md
```

---

## 功能特性

### 1. 设备自动化
- **设备管理** - 真机/模拟器设备发现、连接状态查询
- **应用部署** - HAP 包安装、卸载、启动
- **UI 交互** - 元素查找、点击、长按、输入、滑动、拖拽
- **屏幕截图** - 全局/元素级截图

### 2. E2E 测试支持 ⭐
- **UI 树查询** - 获取完整 UI 层级结构
- **窗口管理** - 列出所有窗口、窗口切换
- **元素等待** - 智能等待元素出现/消失
- **自动重试** - 内置重试机制，提升测试稳定性

### 3. 构建工具链
- **自动化构建** - 调用 Hvigor 构建 HAP 包
- **错误解析** - 自动提取编译错误并分类
- **超时控制** - 支持长时构建任务

### 4. 日志审计
- **安全事件查询** - 查询设备安全日志
- **实时日志** - 支持实时日志采样
- **历史日志** - 支持回退到历史日志
- **崩溃解析** - 自动解析崩溃日志

---

## 工具列表

共 **18 个工具**，分为 4 类：

| 分类 | 工具 | 功能描述 |
|------|------|----------|
| **General** | `list_devices` | 列出已连接的 HarmonyOS 设备 |
| (3 个) | `query_package` | 查询应用安装状态、权限、Ability 信息 |
| | `logs_query` | 查询安全审计日志、崩溃日志 |
| **Build** | `build_app` | 构建 HAP 包（支持 debug 模式） |
| (4 个) | `install_app` | 安装应用到设备 |
| | `run_app` | 启动应用（支持自动检测主 Ability） |
| | `uninstall_app` | 从设备卸载应用 |
| **UI** | `screenshot` | 屏幕截图（支持区域截图） |
| (8 个) | `click_element` | 点击元素（支持坐标/句柄/文本查找） |
| | `long_press_element` | 长按元素 |
| | `input_text` | 输入文本到文本框 |
| | `swipe` | 滑动操作（支持方向/坐标） |
| | `drag` | 拖拽操作 |
| | `press_key` | 按键操作（音量、电源等） |
| | `find_element` | 查找元素（文本/类型/ID） |
| **E2E** ⭐ | `get_ui_tree` | 获取 UI 树结构（支持窗口过滤） |
| (3 个) | `list_windows` | 列出所有窗口（支持应用过滤） |
| | `wait_element` | 等待元素出现/消失（支持超时） |

---

## 响应结构

所有工具返回统一的 MCP 标准格式：

### 成功响应
```json
{
  "content": [{"type": "text", "text": "..."}],
  "structuredContent": {
    "tool": "tool_name",
    "ok": true,
    "result": {
      "device_id": "3QC0124C11000711",
      "packages": ["com.example.app"],
      "count": 1
    },
    "error": null,
    "meta": {
      "request_id": "uuid-xxx",
      "timestamp": "2026-03-19T00:00:00.000000+00:00",
      "duration_ms": 123
    }
  },
  "isError": false
}
```

### 错误响应
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
    "detail": "应用窗口未出现（可能 ability_name 或 module_name 错误）"
  }
}
```

---

## 快速开始

### 1. 安装依赖

```bash
uv sync --all-packages
```

### 2. 启动 MCP Server

```bash
uv run harmonyos-dev-mcp
```

### 3. 确认设备连接

```bash
hdc list targets
# 输出示例：3QC0124C11000711
```

---

## 使用示例

保留 3 个常用示例，其他接口请参考工具列表与 `docs/` 文档。

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
element = await client.call_tool("find_element", {
    "device_id": "3QC0124C11000711",
    "text": "登录"
})
await client.call_tool("click_element", {
    "device_id": "3QC0124C11000711",
    "element_handle": element["structuredContent"]["result"]["elements"][0]
})
```

### 获取 UI 树

```python
ui_tree = await client.call_tool("get_ui_tree", {
    "device_id": "3QC0124C11000711"
})
# 返回：{"ui_tree": {...}, "node_count": 42}
```

---

## 环境要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.12+ | 运行环境 |
| DevEco Studio | 5.0+ | HarmonyOS SDK |
| hdc | 最新版 | 设备连接工具 |
| uv | 最新版 | Python 包管理 |

---

## MCP 客户端配置

### OpenCode 配置

配置文件路径：`~/.config/opencode/opencode.jsonc`

```jsonc
{
  "mcp": {
    "harmonyos-dev-mcp": {
      "type": "local",
      "command": ["uv", "run", "harmonyos-dev-mcp"],
      "enabled": true,
      "timeout": 120000,
      "env": {}
    }
  }
}
```

### 超时建议

- **常规工具**: `30000` ms (30 秒)
- **`build_app`**: 最少 `60000` ms，冷构建推荐 `120000` ms
- **`logs_query`**: 根据日志量调整，建议 `60000` ms

---

## 工具调用注意事项

### `build_app`
- 默认参数是 `build_mode="debug"`、`target="hap"`、`product="default"`。
- 普通项目如果已在 `build-profile.json5` 中配置 `signingConfig`，`build_app` 直接返回 hvigor 生成的最终包。
- 某些 MDM 项目会先生成 unsigned HAP，再调用 `project_root/hapsigner/2-<build_mode>-sign.bat` 脚本手工签名。
- 对这类项目，`build_app` 现在会在识别到 unsigned HAP 后自动尝试项目内脚本签名；成功后 `output_path` 会切换到签名后的包，例如 `project_root/hapsigner/signApp.hap`。
- 如果项目既没有 hvigor 签名配置，也没有项目内签名脚本，`build_app` 只能返回 unsigned HAP，后续安装会失败。

### `query_package`
- 查询 `abilities`/`main_ability`/`permissions` 时必须提供 `bundle_name`

### `input_text`
- `element_handle` 必须传对象，推荐复用 `find_element` 或 `wait_element` 返回的句柄
- **不要**把 `element_handle` 作为 JSON 字符串传入

**正确示例：**
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

**错误示例：**
```json
{
  "element_handle": "{\"window_id\":80,\"id\":\"420\"}",
  "text": "security"
}
```

### `build_app` MDM 签名说明
- 默认参数是 `build_mode="debug"`、`target="hap"`、`product="default"`。
- 普通项目如果已在 `build-profile.json5` 中配置 `signingConfig`，`build_app` 直接返回 hvigor 生成的最终包。
- 某些 MDM 项目会先生成 unsigned HAP，再调用 `project_root/hapsigner/2-<build_mode>-sign.bat` 脚本手工签名。
- 对这类项目，`build_app` 现在会在识别到 unsigned HAP 后自动尝试项目内脚本签名；成功后 `output_path` 会切换到签名后的包，例如 `project_root/hapsigner/signApp.hap`。
- 如果项目既没有 hvigor 签名配置，也没有项目内签名脚本，`build_app` 只能返回 unsigned HAP，后续安装会失败。

---

## 故障排查

### MCP Server 无法启动

```bash
# 手动测试启动
uv run harmonyos-dev-mcp

# 检查设备连接
hdc list targets

# 查看日志
cat logs/harmonyos-dev-mcp.stderr.log
```

### 工具调用超时

1. 确保设备已连接且屏幕已解锁
2. 检查 DevEco Studio / SDK / `hdc` 路径配置
3. 增加 MCP 客户端超时时间（建议 60 秒+）

### 构建失败

```bash
# 检查 Hvigor 路径
# 查看构建输出中的错误信息
# 确认项目路径正确
```

---

## 开发

### 运行测试

```bash
# 单元测试
uv run pytest services/harmonyos_dev_mcp/tests/unit -v

# 带覆盖率
uv run pytest services/harmonyos_dev_mcp/tests/unit -v --cov=harmonyos_dev_mcp
```

### 发布到 PyPI

```bash
# 设置 Token
export UV_PUBLISH_TOKEN="pypi-xxx"

# 发布
uv publish dist/*
```

---

## 相关文档

- [`docs/logs_query.md`](services/harmonyos_dev_mcp/docs/logs_query.md) - 日志查询详细文档

---

## License

Apache License 2.0

---

## 联系方式

- **作者**: huduanmu
- **邮箱**: 772927148@qq.com
- **PyPI**: 
  - [harmonyos-mcp-common](https://pypi.org/project/harmonyos-mcp-common/)
  - [harmonyos-dev-mcp](https://pypi.org/project/harmonyos-dev-mcp/)
