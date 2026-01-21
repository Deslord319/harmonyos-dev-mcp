# HarmonyOS MCP Server - 快速开始指南

**状态**: ✅ 测试通过，可以使用  
**测试日期**: 2026-01-21

## 🎯 一分钟快速配置

### 1. 安装依赖（首次使用）

```bash
cd harmonyos-mcp-server
pip install -r requirements.txt
```

### 2. 验证安装

```bash
python test_mcp_startup.py
```

应该看到：
```
🎉 所有测试通过！MCP服务器可以正常启动。
```

### 3. 在Augment中导入配置

**方法A: 通过JSON导入（推荐）**

1. 打开VSCode设置 → Augment → Integrations → MCP Servers
2. 点击 "Import from JSON"
3. 选择文件: `harmonyos-mcp-server/augment-mcp-config.json`
4. 完成！

**方法B: 手动添加**

1. 打开VSCode设置 → Augment → Integrations → MCP Servers
2. 点击 "Add MCP"
3. 填写以下信息：
   - **Server Name**: `harmonyos-tools`
   - **Command**: `python`
   - **Arguments**: `src/main.py`
   - **Working Directory**: `d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server`
   - **Environment Variables**:
     - Key: `HARMONYOS_SDK_PATH`
     - Value: `C:\Program Files\Huawei\DevEco Studio\sdk\default`

### 4. 重启VSCode

完全关闭并重新打开VSCode，让Augment重新加载MCP配置。

### 5. 验证连接

在Augment中输入：
```
列出所有HarmonyOS设备
```

如果返回设备列表（如 `3QC0124A24000365`），说明配置成功！

## 🛠️ 可用的MCP工具

配置成功后，你可以在Augment中使用以下工具：

1. **list_devices** - 列出所有连接的HarmonyOS设备
2. **list_windows** - 列出设备上的所有窗口
3. **get_ui_tree** - 获取应用的UI组件树
4. **build_app** - 构建HarmonyOS应用
5. **install_app** - 安装应用到设备
6. **run_app** - 运行应用
7. **uninstall_app** - 卸载应用
8. **get_logs** - 获取设备日志

## 💡 使用示例

### 示例1: 查看设备
```
请列出所有连接的HarmonyOS设备
```

### 示例2: 获取UI树
```
获取myapplication应用的UI组件树
```

### 示例3: 完整工作流
```
帮我完成以下任务：
1. 构建ho_module_app项目
2. 安装到设备
3. 启动应用
4. 获取UI树并分析
```

## 🐛 故障排除

### 问题1: MCP服务器显示"Disconnected"

**检查Python**:
```bash
python --version
```

**检查依赖**:
```bash
pip list | findstr fastmcp
```

**重新安装依赖**:
```bash
pip install -r requirements.txt
```

### 问题2: 找不到设备

**检查设备连接**:
```bash
hdc list targets
```

**检查hdc路径**:
```bash
where hdc
```

### 问题3: 工具调用失败

**查看MCP服务器日志**:
- 检查 `harmonyos-mcp-server/logs/` 目录下的日志文件

**手动测试工具**:
```bash
cd harmonyos-mcp-server
python test_mcp_startup.py
```

## 📚 更多文档

- [完整配置指南](AUGMENT_SETUP.md)
- [项目状态](PROJECT_STATUS.md)
- [构建系统指南](docs/build-system-guide.md)
- [hidumper使用指南](docs/hidumper-uitree-guide.md)

## 🎉 开始使用

现在你可以：

✅ 让AI帮你管理HarmonyOS设备  
✅ 自动化构建和部署流程  
✅ 分析应用UI结构  
✅ 获取实时日志  
✅ 完整的端到端开发工作流

享受AI辅助的HarmonyOS开发！🚀

