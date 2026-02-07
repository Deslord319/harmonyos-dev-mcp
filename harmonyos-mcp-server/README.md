# HarmonyOS MCP Server

一个为 HarmonyOS 应用开发设计的模型上下文协议 (MCP) 服务器，实现 AI 辅助开发的端到端自动化。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

## ✨ 功能特性

| 类别 | 功能 | 工具数 |
|------|------|--------|
| 🔌 **设备管理** | 列出设备、获取 hilog 文件、环境检查 | 3 |
| 🔧 **三方库编译** | WSL 检查、克隆仓库、分析构建系统、交叉编译 | 6 |
| 🔨 **构建部署** | 编译、安装、运行、卸载应用 | 4 |
| 📦 **包管理** | 列出包、获取 Abilities、查询主入口 | 3 |
| 🌳 **UI 感知** | 获取 UI 树、查找元素、列出窗口 | 3 |
| 🎯 **UI 操作** | 点击、输入、滑动、长按、按键 | 5 |
| 📊 **日志分析** | 获取日志、保存快照、结构化分析、解析加密日志 | 4 |
| 🤖 **AI 集成** | 支持 Augment、Cursor、Cline、LibreChat 等 | - |

**共计 28 个 MCP 工具**

---

## 🛠️ MCP 工具列表

### 设备管理 (Device Management)

| 工具名 | 描述 | 主要参数 |
|--------|------|----------|
| `list_devices` | 列出所有连接的 HarmonyOS 设备和模拟器 | - |
| `health_check` | 检查 hdc 和 hilogtool 环境状态 | - |

### 构建部署 (Build & Deploy)

| 工具名 | 描述 | 主要参数 |
|--------|------|----------|
| `build_app` | 构建 HarmonyOS 应用 | `project_path`, `build_mode` |
| `install_app` | 安装应用到设备 | `hap_path`, `device_id` |
| `run_app` | 运行应用 | `bundle_name`, `device_id`, `ability_name` |
| `uninstall_app` | 卸载应用 | `bundle_name`, `device_id` |

### UI 感知 (UI Awareness)

| 工具名 | 描述 | 主要参数 |
|--------|------|----------|
| `get_ui_tree` | 获取应用的 UI 组件树 | `device_id`, `bundle_name`, `window_id` |
| `list_windows` | 列出设备上的所有窗口 | `device_id` |
| `find_element` | 在 UI 树中查找元素 | `text`, `element_type`, `element_id` |

### UI 操作 (UI Operations)

| 工具名 | 描述 | 主要参数 |
|--------|------|----------|
| `click_element` | 点击屏幕上的元素 | `x`, `y`, `text`, `double_click` |
| `long_press_element` | 长按屏幕上的元素 | `x`, `y`, `text` |
| `swipe` | 滑动操作 | `from_x`, `from_y`, `to_x`, `to_y`, `direction` |
| `input_text` | 在输入框中输入文本 | `x`, `y`, `text` |
| `press_key` | 模拟按键操作 | `key` (Home/Back/Enter 等) |

### 日志分析 (Log Analysis)

| 工具名 | 描述 | 主要参数 |
|--------|------|----------|
| `logs_fetch` | 从设备获取日志（支持多种过滤条件） | `lines`, `level`, `tag`, `keyword`, `package_name`, `pid`, `seconds` |
| `logs_save_snapshot` | 保存日志快照到本地文件 | `output_path`, `lines`, `package_name`, `include_analysis` |
| `logs_analyze` | 对日志进行结构化分析 | `analysis_type` (summary/errors/performance/crashes) |
| `logs_parse_hilog_files` | 解析本地的 hilog 加密日志文件 | `hilog_dir`, `dict_path` |

---

## 📋 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | >= 3.10 | FastMCP 要求 |
| **DevEco Studio** | >= 4.0 | HarmonyOS 开发 IDE |
| **HarmonyOS 设备** | - | 真机或模拟器 |

---

## 🚀 安装部署

### 1. 安装 wheel 包

```bash
pip install harmonyos_mcp-0.1.0-py3-none-any.whl
```

### 2. 验证安装

```bash
# 查看已安装的包
pip show harmonyos-mcp

# 测试运行（会启动 MCP 服务器）
harmonyos-mcp
```

---

## 🤖 AI IDE 集成

### Augment（VSCode 插件）

1. 打开 VSCode 设置 (Ctrl+,)
2. 搜索 `augment.mcpServers`
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

### Cursor / Cline

在项目根目录创建 `.cursor/mcp.json`：

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

在 `librechat.yaml` 中添加：

```yaml
mcpServers:
  harmonyos-tools:
    command: harmonyos-mcp
    timeout: 60000
```

---

## ✅ 验证配置

在 AI IDE 中输入以下提示词测试：

```
列出所有连接的 HarmonyOS 设备
```

如果返回设备列表，说明配置成功！

---

## 💡 使用示例

### 日志抓取

```
# 获取最近 100 行日志
获取设备日志

# 按包名过滤日志
抓取 com.example.myapplication 最新的日志

# 按级别过滤（只看错误）
获取最近的错误日志，级别 E

# 保存日志快照
保存 com.example.myapplication 的日志到本地
```

### 应用操作

```
# 构建并安装应用
构建项目 D:\MyProject 并安装到设备

# 运行应用
启动 com.example.myapplication

# 卸载应用
卸载 com.example.myapplication
```

### UI 自动化

```
# 获取当前界面元素
获取当前应用的 UI 树

# 点击按钮
点击文本为"登录"的按钮

# 输入文本
在搜索框输入"HarmonyOS"
```

---

## 📄 许可证

MIT License

