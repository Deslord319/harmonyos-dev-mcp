# HarmonyOS MCP Server

**状态**: ✅ **已成功集成Augment并可用** | **版本**: 0.1.0 | **更新日期**: 2026-01-21

一个为HarmonyOS应用开发设计的模型上下文协议(MCP)工具,实现AI辅助开发的端到端自动化。

**🎊 重大进展 (2026-01-21)**:
- ✅ **Augment集成成功** - MCP服务器已成功连接到Augment
- ✅ **8个MCP工具全部可用** - 可通过AI对话直接调用
- ✅ 所有核心功能已实现并测试通过
- ✅ 成功在真实硬件设备上测试（设备ID: 3QC0124A24000365）
- ✅ UI树获取功能完整可用（支持1900+节点的大型UI树）
- ✅ 基于hidumper的零侵入UI树获取方案

## 🎯 项目目标

- **全流程自动化**: 覆盖从代码编写、编译构建、安装部署到UI测试的全过程
- **深度IDE集成**: 通过MCP协议与主流AI IDE(Cursor、Cline)无缝集成
- **UI感知能力**: 通过UITest框架实现对HarmonyOS应用UI结构的实时感知
- **开发效率提升**: 让AI能够理解并操作HarmonyOS应用,提供真正的上下文感知辅助

## 🏗️ 架构设计

```
AI IDE (Cursor/Cline)
    ↓
MCP Client (内置)
    ↓
HarmonyOS MCP Server (Python + FastMCP)
    ├── UITools - UI感知与操作
    ├── BuildTools - 构建与编译
    ├── DeviceTools - 设备管理
    └── SigningTools - 签名管理
    ↓
HarmonyOS工具链 (hdc, hvigorw, UITest)
    ↓
HarmonyOS设备/模拟器
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- HarmonyOS SDK (DevEco Studio)
- HarmonyOS设备或模拟器
- Augment (VSCode扩展)

### 方式1: Augment集成（推荐）⭐ **已验证可用**

**最简单的使用方式 - 3步完成配置！**

1. **安装依赖**
```bash
cd harmonyos-mcp-server
pip install -r requirements.txt
```

2. **在Augment中导入MCP配置**
   - 打开VSCode设置 → Augment → Integrations → MCP Servers
   - 点击 "Import from JSON"
   - 选择文件: `augment-config-absolute-path.json` ⭐ **推荐使用此配置**

3. **验证连接**
   - 查看Augment设置中 `harmonyos-tools` 状态应显示 "Connected" ✅
   - 在Augment中输入: "列出所有HarmonyOS设备"
   - AI将自动调用MCP工具并返回设备列表！

📖 **详细文档**:
- [集成成功报告](AUGMENT_INTEGRATION_SUCCESS.md) - 包含完整的问题诊断和解决方案
- [配置指南](AUGMENT_SETUP.md) - 详细的配置步骤

### 方式2: 命令行使用

```bash
# 克隆项目
git clone https://github.com/your-org/harmonyos-mcp-server.git
cd harmonyos-mcp-server

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export HARMONYOS_SDK_PATH=/path/to/harmonyos/sdk
```

### 配置Cursor/Cline

在项目根目录创建 `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "harmonyos-tools": {
      "command": "python",
      "args": ["path/to/harmonyos-mcp-server/src/main.py"],
      "env": {
        "HARMONYOS_SDK_PATH": "/path/to/harmonyos/sdk"
      }
    }
  }
}
```

## 📚 核心功能

### UI感知与操作
- `get_ui_tree` - 获取应用UI树结构
- `find_element` - 查找UI元素
- `click_element` - 点击UI元素
- `input_text` - 输入文本

### 构建与部署
- `build_app` - 构建HarmonyOS应用
- `install_app` - 安装应用到设备
- `run_app` - 运行应用

### 设备管理
- `list_devices` - 列出所有连接的设备
- `get_logs` - 获取应用日志

### 签名管理
- `configure_signing` - 配置应用签名
- `get_signing_status` - 获取签名状态

## 📖 文档

- [安装指南](docs/installation.md)
- [快速开始](docs/quickstart.md)
- [API参考](docs/api-reference.md)
- [架构设计](docs/architecture.md)

## 🤝 贡献

欢迎贡献! 请查看 [贡献指南](CONTRIBUTING.md)

## 📄 许可证

MIT License

## 🔗 相关资源

- [HarmonyOS开发者文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides)
- [MCP协议规范](https://modelcontextprotocol.io/)
- [FastMCP框架](https://github.com/jlowin/fastmcp)

