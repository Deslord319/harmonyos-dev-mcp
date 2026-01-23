# HarmonyOS MCP Server

一个为 HarmonyOS 应用开发设计的模型上下文协议 (MCP) 服务器，实现 AI 辅助开发的端到端自动化。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io/)

## ✨ 功能特性

| 类别 | 功能 |
|------|------|
| 🔌 **设备管理** | 列出设备、获取日志（支持过滤） |
| 🔨 **构建部署** | 编译、安装、运行、卸载应用 |
| 🌳 **UI 感知** | 获取 UI 树、查找元素、列出窗口 |
| 🎯 **UI 操作** | 点击、输入、滑动、长按、按键 |
| 🤖 **AI 集成** | 支持 Augment、Cursor、Cline、LibreChat 等 |

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

## 📄 许可证

MIT License

