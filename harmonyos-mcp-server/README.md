# HarmonyOS MCP Server

一个为 HarmonyOS 应用开发设计的模型上下文协议 (MCP) 服务器，实现 AI 辅助开发的端到端自动化。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

## ✨ 功能特性

- 🔌 **设备管理** - 列出设备、获取日志
- 🔨 **构建部署** - 编译、安装、运行应用
- 🌳 **UI 感知** - 获取 UI 树、查找元素
- 🎯 **UI 操作** - 点击、输入、滑动、长按
- 🤖 **AI 集成** - 支持 Augment、Cursor、Cline 等 AI IDE

## 📋 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | >= 3.10 | FastMCP 要求 |
| **DevEco Studio** | >= 4.0 | HarmonyOS 开发 IDE |
| **HarmonyOS 设备** | - | 真机或模拟器 |

## 🚀 快速开始

### 1. 安装 Python 依赖

```bash
cd harmonyos-mcp-server
pip install -r requirements.txt
```

### 2. 配置环境（可选）

程序会自动检测 DevEco Studio 和 SDK 路径。如果自动检测失败，请设置以下环境变量：

#### Windows (PowerShell)

```powershell
# 设置 DevEco Studio 路径
$env:DEVECO_STUDIO_PATH = "C:\Program Files\Huawei\DevEco Studio"

# 或者直接设置 hdc 路径
$env:HDC_PATH = "C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
```

#### Windows (永久设置)

```powershell
# 打开系统环境变量设置
[System.Environment]::SetEnvironmentVariable("DEVECO_STUDIO_PATH", "C:\Program Files\Huawei\DevEco Studio", "User")
```

#### macOS / Linux

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export DEVECO_STUDIO_PATH="/Applications/DevEco Studio.app/Contents"
export HARMONYOS_SDK_PATH="$HOME/Library/Huawei/Sdk"
```

### 3. 配置 AI IDE

#### Augment（推荐）

1. 打开 VSCode 设置 → Augment → Integrations → MCP Servers
2. 添加以下配置：

```json
{
  "harmonyos-tools": {
    "command": "python",
    "args": ["D:\\your\\path\\to\\harmonyos-mcp-server\\src\\main.py"]
  }
}
```

> ⚠️ **重要**: Augment 需要使用**绝对路径**

#### Cursor / Cline

在项目根目录创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "harmonyos-tools": {
      "command": "python",
      "args": ["./harmonyos-mcp-server/src/main.py"],
      "env": {
        "DEVECO_STUDIO_PATH": "C:\\Program Files\\Huawei\\DevEco Studio"
      }
    }
  }
}
```

### 4. 验证安装

在 AI IDE 中输入：

```
列出所有连接的 HarmonyOS 设备
```

如果看到设备列表，说明配置成功！

## ⚙️ 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DEVECO_STUDIO_PATH` | DevEco Studio 安装路径 | `C:\Program Files\Huawei\DevEco Studio` |
| `HARMONYOS_SDK_PATH` | HarmonyOS SDK 路径 | `C:\Program Files\Huawei\DevEco Studio\sdk\default` |
| `HDC_PATH` | hdc 工具完整路径 | `...\toolchains\hdc.exe` |
| `LOG_LEVEL` | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `COMMAND_TIMEOUT` | 命令超时时间（秒） | `300` |
| `BUILD_TIMEOUT` | 构建超时时间（秒） | `600` |

> 💡 **提示**: 大多数情况下只需设置 `DEVECO_STUDIO_PATH`，其他路径会自动检测

## 🛠️ MCP 工具列表

### 设备管理

| 工具 | 功能 |
|------|------|
| `list_devices` | 列出所有连接的设备 |
| `get_logs` | 获取设备日志（支持按包名、标签、PID 过滤） |

### 构建部署

| 工具 | 功能 |
|------|------|
| `build_app` | 构建 HarmonyOS 应用 |
| `install_app` | 安装 HAP 包到设备 |
| `run_app` | 运行应用 |
| `uninstall_app` | 卸载应用 |

### UI 感知

| 工具 | 功能 |
|------|------|
| `list_windows` | 列出设备上所有窗口 |
| `get_ui_tree` | 获取应用 UI 组件树 |
| `find_element` | 在 UI 树中查找元素 |

### UI 操作

| 工具 | 功能 |
|------|------|
| `click_element` | 点击指定坐标或元素 |
| `long_press_element` | 长按元素 |
| `swipe` | 滑动操作 |
| `input_text` | 输入文本 |
| `press_key` | 模拟按键（Home、Back 等） |

## 📁 项目结构

```
harmonyos-mcp-server/
├── src/
│   ├── main.py              # MCP 服务器入口
│   ├── config.py            # 配置管理
│   └── utils/
│       ├── hdc_wrapper.py   # hdc 命令封装
│       ├── hvigor_wrapper.py # hvigor 构建封装
│       ├── ui_operations.py  # UI 操作封装
│       └── uitree_parser.py  # UI 树解析器
├── requirements.txt         # Python 依赖
└── README.md
```

## 🔧 故障排除

### 找不到 hdc 工具

```
❌ 未找到 hdc 工具，请设置 HDC_PATH 环境变量或安装 DevEco Studio
```

**解决方案**:
1. 确保已安装 DevEco Studio
2. 设置环境变量 `DEVECO_STUDIO_PATH` 或 `HDC_PATH`

### 设备列表为空

**解决方案**:
1. 确保设备已通过 USB 连接
2. 在设备上启用开发者选项和 USB 调试
3. 运行 `hdc list targets` 手动验证

### 构建失败

**解决方案**:
1. 确保项目可以在 DevEco Studio 中正常构建
2. 检查 `local.properties` 中的 SDK 路径配置

## 📄 许可证

MIT License

## 🔗 相关资源

- [HarmonyOS 开发者文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [FastMCP 框架](https://github.com/jlowin/fastmcp)

