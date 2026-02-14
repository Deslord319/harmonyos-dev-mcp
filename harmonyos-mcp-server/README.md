# HarmonyOS MCP Server

一个为 HarmonyOS 应用开发设计的模型上下文协议 (MCP) 服务器，实现 AI 辅助开发的端到端自动化。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

## 功能特性

| 类别 | 功能 | 工具数 |
|------|------|--------|
| 设备管理 | 列出设备、获取 hilog 文件 | 2 |
| 三方库编译 | WSL 检查、克隆仓库、分析构建系统、交叉编译 | 8 |
| 构建部署 | 编译、安装、运行、卸载应用 | 4 |
| 包管理 | 列出包、获取 Abilities、查询主入口 | 3 |
| UI 感知 | 获取 UI 树、查找元素、列出窗口 | 2 |
| UI 操作 | 点击、输入、滑动、长按、按键、查找 | 6 |
| 日志分析 | 获取日志、保存快照、结构化分析 | 3 |

**共计 28 个 MCP 工具**

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

`ash
# 安装 ho-llm-cli
pip install ho-llm-cli

# 启动对话
poetry run ho-llm-cli chat
`

在配置文件中添加 MCP 服务器：

`yaml
# config.yaml
mcp_servers:
  harmonyos:
    command: harmonyos-mcp
    args: []
`

### 方式二：直接安装 MCP Server

#### 1. 安装构建工具

`ash
pip install hatchling build
`

#### 2. 构建 wheel 包

在 harmonyos-mcp-server/ 目录下执行：

`ash
python -m build
`

构建完成后，wheel 包位于 dist/ 目录：

`
dist/
  harmonyos_mcp-0.2.0-py3-none-any.whl
  harmonyos_mcp-0.2.0.tar.gz
`

#### 3. 安装 wheel 包

`ash
pip install dist/harmonyos_mcp-0.2.0-py3-none-any.whl
`

升级安装：

`ash
pip install --force-reinstall dist/harmonyos_mcp-0.2.0-py3-none-any.whl
`

#### 4. 验证安装

`ash
# 查看已安装的包
pip show harmonyos-mcp

# 测试启动（会启动 MCP 服务器）
harmonyos-mcp
`

---

## 配置 MCP 服务

### ho-llm-cli（推荐）

在项目根目录创建 config.yaml：

`yaml
llm:
  provider: dashscope
  model: qwen3-235b-a22b

mcp_servers:
  harmonyos:
    command: harmonyos-mcp

mcp_manager:
  lazy_load: true
  idle_timeout: 600
`

### Augment（VSCode 插件）

1. 打开 VSCode 设置 (Ctrl+,)
2. 搜索 ugment.mcpServers
3. 点击 "Edit in settings.json"
4. 添加以下配置：

`json
{
  "augment.mcpServers": {
    "harmonyos-tools": {
      "command": "harmonyos-mcp"
    }
  }
}
`

### Cursor

在项目根目录创建 .cursor/mcp.json：

`json
{
  "mcpServers": {
    "harmonyos-tools": {
      "command": "harmonyos-mcp"
    }
  }
}
`

### Cline（VSCode 插件）

在 Cline MCP 设置中添加：

`json
{
  "mcpServers": {
    "harmonyos-tools": {
      "command": "harmonyos-mcp"
    }
  }
}
`

### LibreChat

在 librechat.yaml 中添加：

`yaml
mcpServers:
  harmonyos-tools:
    command: harmonyos-mcp
    timeout: 60000
`

### 通用 stdio 方式

所有支持 MCP 的客户端均可通过 stdio 连接：

`json
{
  "command": "harmonyos-mcp",
  "transport": "stdio"
}
`

如果 harmonyos-mcp 不在 PATH 中，可使用完整路径：

`json
{
  "command": "python",
  "args": ["-m", "harmonyos_mcp"]
}
`

---

## 验证配置

在 AI IDE 中输入以下提示词测试：

`
列出所有连接的 HarmonyOS 设备
`

如果返回设备列表，说明配置成功。

---

## MCP 工具列表

### 设备管理 (Device)

| 工具名 | 描述 |
|--------|------|
| list_devices | 列出所有连接的 HarmonyOS 设备和模拟器 |
| hilog_receive | 从设备获取 hilog 日志文件 |

### 构建部署 (Build)

| 工具名 | 描述 |
|--------|------|
| uild_app | 构建 HarmonyOS 应用 |
| install_app | 安装应用到设备 |
| un_app | 运行应用 |
| uninstall_app | 卸载应用 |

### 包管理 (Packages)

| 工具名 | 描述 |
|--------|------|
| list_packages | 列出设备上已安装的应用包 |
| get_package_abilities | 获取指定包的所有 Abilities |
| get_main_ability | 获取指定包的主入口 Ability |

### UI 感知 (UI Tree)

| 工具名 | 描述 |
|--------|------|
| get_ui_tree | 获取应用的 UI 组件树 |
| list_windows | 列出设备上的所有窗口 |

### UI 操作 (UI)

| 工具名 | 描述 |
|--------|------|
| click_element | 点击屏幕上的元素 |
| long_press_element | 长按屏幕上的元素 |
| swipe | 滑动操作 |
| input_text | 在输入框中输入文本 |
| press_key | 模拟按键操作 |
| ind_element | 在 UI 树中查找元素 |

### 日志分析 (Logs)

| 工具名 | 描述 |
|--------|------|
| logs_fetch | 从设备获取日志（支持多种过滤条件） |
| logs_save_snapshot | 保存日志快照到本地文件 |
| logs_analyze | 对日志进行结构化分析 |

### 三方库编译 (Compile)

| 工具名 | 描述 |
|--------|------|
| check_wsl | 检查 WSL 环境是否可用 |
| check_harmonyos_compiler_tools | 检查 HarmonyOS 编译工具 |
| clone_library | 拉取三方库代码仓库 |
| nalyze_build_system | 分析项目构建系统类型 |
| ead_build_files | 读取构建系统文件 |
| write_compile_script | 生成编译脚本 |
| execute_compile_script | 执行编译脚本 |
| erify_so_output | 验证编译输出的 .so 文件 |

---

## 项目路线图

详见 [TASKS.md](TASKS.md)

---

## 许可证

MIT License
