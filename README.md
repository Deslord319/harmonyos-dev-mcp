# HarmonyOS MCP Server

一个为 HarmonyOS 应用开发设计的模型上下文协议 (MCP) 服务器，实现 AI 辅助开发的端到端自动化。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

## 功能特性

| 类别 | 功能 | 工具数 |
|------|------|--------|
| 通用 | 设备管理、包管理、日志查询 | 3 |
| 鸿蒙打包编译 | 编译、安装、运行、卸载应用 | 4 |
| UI 测试 | UI 树感知、元素查找、点击/输入/滑动、截图 | 8 |
| UI 树 | UI 组件树、窗口列表 | 2 |

**共计 17 个 MCP 工具**

---

## 三方库编译（独立 MCP 服务器）

三方库编译功能已拆分为独立的 MCP 服务器 `harmonyos-mcp-compile`，提供 AI 辅助的交叉编译能力。

**功能**：
- WSL 检查、编译工具检查
- 代码克隆、构建系统分析
- 编译脚本生成、执行、验证

**安装**：
```bash
pip install harmonyos-mcp-compile
```

**配置**：
```yaml
mcp_servers:
  harmonyos-compile:
    command: harmonyos-mcp-compile
```

**详情**：[mcp_ho_compile](https://github.com/Deslord319/mcp_ho_compile)

---

## 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | >= 3.10 | FastMCP 要求 |
| **DevEco Studio** | >= 4.0 | HarmonyOS 开发 IDE |
| **HarmonyOS 设备** | - | 真机或模拟器 |

---

## 快速开始

### 方式一：使用 ho-llm-cli（推荐）

ho-llm-cli 是一个支持 MCP 的 AI CLI 工具，可以直接使用：

```bash
# 安装 ho-llm-cli
pip install ho-llm-cli

# 启动对话
poetry run ho-llm-cli chat
```

在配置文件中添加 MCP 服务器：

```yaml
# config.yaml
mcp_servers:
  harmonyos:
    command: harmonyos-mcp
    args: []
```

### 方式二：直接安装 MCP Server

#### 1. 安装构建工具

```bash
pip install hatchling build
```

#### 2. 构建 wheel 包

在项目根目录下执行：

```bash
python -m build
```

构建完成后，wheel 包位于 dist/ 目录：

```
dist/
  harmonyos_mcp-0.4.0-py3-none-any.whl
  harmonyos_mcp-0.4.0.tar.gz
```

#### 3. 安装 wheel 包

```bash
pip install dist/harmonyos_mcp-0.4.0-py3-none-any.whl
```

升级安装：

```bash
pip install --force-reinstall dist/harmonyos_mcp-0.4.0-py3-none-any.whl
```

#### 4. 验证安装

```bash
# 查看已安装的包
pip show harmonyos-mcp

# 测试启动（会启动 MCP 服务器）
harmonyos-mcp
```

---

## 配置 MCP 服务

### ho-llm-cli（推荐）

在项目根目录创建 config.yaml：

```yaml
llm:
  provider: dashscope
  model: qwen3-235b-a22b

mcp_servers:
  harmonyos:
    command: harmonyos-mcp

mcp_manager:
  lazy_load: true
  idle_timeout: 600
```

### Augment（VSCode 插件）

1. 打开 VSCode 设置 (Ctrl+,)
2. 搜索 augment.mcpServers
3. 点击 "Edit in settings.json"
4. 添加以下配置：

```json
{
  "augment.mcpServers": {
    "harmonyos-tools": {
      "command": "harmonyos-mcp"
    }
  }
}
```

### Cursor

在项目根目录创建 .cursor/mcp.json：

```json
{
  "mcpServers": {
    "harmonyos-tools": {
      "command": "harmonyos-mcp"
    }
  }
}
```

### Cline（VSCode 插件）

在 Cline MCP 设置中添加：

```json
{
  "mcpServers": {
    "harmonyos-tools": {
      "command": "harmonyos-mcp"
    }
  }
}
```

### LibreChat

在 librechat.yaml 中添加：

```yaml
mcpServers:
  harmonyos-tools:
    command: harmonyos-mcp
    timeout: 60000
```

### 通用 stdio 方式

所有支持 MCP 的客户端均可通过 stdio 连接：

```json
{
  "command": "harmonyos-mcp",
  "transport": "stdio"
}
```

如果 harmonyos-mcp 不在 PATH 中，可使用完整路径：

```json
{
  "command": "python",
  "args": ["-m", "harmonyos_mcp"]
}
```

---

## 验证配置

在 AI IDE 中输入以下提示词测试：

```
列出所有连接的 HarmonyOS 设备
```

如果返回设备列表，说明配置成功。

---

## MCP 工具列表

### 一、通用 (General)

| 工具名 | 描述 |
|--------|------|
| list_devices | 列出所有连接的 HarmonyOS 设备和模拟器 |
| query_package | 统一的包查询工具（包列表/Abilities/权限等） |
| logs_query | 统一日志查询工具（拉取/解析/过滤/分析） |

> 工具详细参数见：[logs_query](docs/logs_query.md)、[query_package](docs/query_package.md)

### 二、鸿蒙打包编译 (Build)

| 工具名 | 描述 |
|--------|------|
| build_app | 构建 HarmonyOS 应用（debug/release） |
| install_app | 安装 HAP 包到设备 |
| run_app | 运行应用（支持自动检测主 Ability） |
| uninstall_app | 卸载应用 |

### 三、UI 测试 (UI Test)

| 工具名 | 描述 |
|--------|------|
| screenshot | 设备屏幕截图（支持全屏和区域截图） |
| click_element | 点击/双击元素（支持坐标或文本查找） |
| long_press_element | 长按元素 |
| input_text | 在输入框中输入文本 |
| swipe | 滑动操作（支持方向或坐标） |
| drag | 拖拽操作 |
| press_key | 模拟按键（Home/Back/Enter 等） |
| find_element | 在 UI 树中查找元素 |

### 四、UI 树 (UI Tree)

| 工具名 | 描述 |
|--------|------|
| get_ui_tree | 获取应用的 UI 组件树 |
| list_windows | 列出设备上的所有窗口 |

---

## 项目结构

```
mcp_ho_dev/
├── harmonyos_mcp/           # MCP 服务器核心
│   ├── tools/               # MCP 工具模块
│   │   ├── general.py       # 通用（设备+包管理+日志）
│   │   ├── log/             # 日志模块
│   │   │   ├── parser.py    # 日志解析器
│   │   │   ├── time_utils.py # 时间工具
│   │   │   ├── historian.py # 历史日志
│   │   │   └── query.py     # 主查询入口
│   │   ├── build.py         # 鸿蒙打包编译
│   │   ├── ui.py            # UI 测试（操作+截图）
│   │   └── ui_tree.py       # UI 测试（树+窗口）
│   ├── utils/               # 工具类
│   │   ├── hdc/             # hdc 命令封装
│   │   ├── wrappers/        # 各种包装器
│   │   └── ...
│   └── server.py            # FastMCP 服务器
├── docs/                    # 工具文档
│   ├── logs_query.md

│   └── query_package.md
├── tests/                   # 测试用例
├── pyproject.toml          # 项目配置
└── README.md
```

---

## 版本历史

### v0.4.0 (2025-02-27)

**重大变更**：
- ✨ 将三方库编译功能拆分为独立 MCP 服务器 `harmonyos-mcp-compile`
- 📦 主项目工具数量：25 → 17
- 📝 更新文档和配置示例

**迁移指南**：
- 三方库编译功能已移至 [mcp_ho_compile](https://github.com/Deslord319/mcp_ho_compile)
- 如需使用三方库编译功能，请安装 `harmonyos-mcp-compile`

### v0.3.0

- ✨ 添加三方库编译功能（8 个工具）
- ✨ 添加 UI 树查询功能
- 🐛 修复日志解析问题

### v0.2.0

- ✨ 添加 UI 测试功能（8 个工具）
- ✨ 添加日志查询功能
- 📝 完善文档

### v0.1.0

- 🎉 首次发布
- ✨ 基础功能（9 个工具）

---

## 许可证

MIT License
