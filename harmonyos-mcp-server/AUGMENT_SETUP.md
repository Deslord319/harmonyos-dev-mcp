# Augment MCP服务器配置指南

## 📋 快速配置步骤

### 方法1: 通过Augment UI导入（推荐）

1. **打开Augment设置**
   - 在VSCode中，点击左下角的齿轮图标 ⚙️
   - 选择 "Settings"
   - 搜索 "Augment"
   - 找到 "Integrations" → "MCP Servers"

2. **导入MCP配置**
   - 点击 "Import from JSON" 按钮
   - 选择文件: `d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server\augment-mcp-config.json`
   - 或者复制下面的JSON内容，点击 "Add MCP" 手动添加

3. **验证配置**
   - 在MCP Servers列表中应该能看到 `harmonyos-tools`
   - 状态应该显示为 "Connected" 或 "Running"

### 方法2: 手动添加MCP服务器

如果导入失败，可以手动添加：

1. **点击 "Add MCP" 按钮**

2. **填写配置信息**:
   - **Server Name**: `harmonyos-tools`
   - **Command**: `python`
   - **Arguments**: 
     ```
     src/main.py
     ```
   - **Working Directory**: 
     ```
     d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server
     ```
   - **Environment Variables**:
     - Key: `HARMONYOS_SDK_PATH`
     - Value: `C:\Program Files\Huawei\DevEco Studio\sdk\default`

3. **保存配置**

## 📄 完整配置JSON

如果需要手动编辑配置文件，使用以下JSON：

```json
{
  "harmonyos-tools": {
    "command": "python",
    "args": [
      "src/main.py"
    ],
    "cwd": "d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server",
    "env": {
      "HARMONYOS_SDK_PATH": "C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default"
    }
  }
}
```

## ✅ 验证配置

### 1. 检查MCP服务器状态

在Augment设置的MCP Servers部分，应该看到：
- ✅ Server Name: `harmonyos-tools`
- ✅ Status: Connected/Running
- ✅ Tools: 8个工具可用

### 2. 测试工具调用

在Augment聊天窗口中输入：

```
请使用list_devices工具列出所有连接的HarmonyOS设备
```

如果返回设备列表（如 `3QC0124A24000365`），说明配置成功！

### 3. 查看可用工具

在Augment中询问：

```
harmonyos-tools有哪些可用的工具？
```

应该看到以下8个工具：
1. `list_devices` - 列出设备
2. `list_windows` - 列出窗口
3. `get_logs` - 获取日志
4. `build_app` - 构建应用
5. `install_app` - 安装应用
6. `run_app` - 运行应用
7. `uninstall_app` - 卸载应用
8. `get_ui_tree` - 获取UI树

## 🎯 使用示例

### 示例1: 查看设备
```
列出所有HarmonyOS设备
```

### 示例2: 获取UI树
```
获取myapplication应用的UI组件树
```

### 示例3: 构建项目
```
构建d:\lxl\ho_dev_app_mcp\ho_module_app项目
```

### 示例4: 完整工作流
```
帮我完成以下任务：
1. 构建ho_module_app项目
2. 安装到设备
3. 启动应用
4. 获取UI树并分析
```

## 🐛 故障排除

### 问题1: MCP服务器显示"Disconnected"

**可能原因**:
- Python未安装或不在PATH中
- 依赖包未安装

**解决方案**:
```bash
# 检查Python
python --version

# 安装依赖
cd d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server
pip install -r requirements.txt
```

### 问题2: 工具调用失败

**可能原因**:
- 设备未连接
- SDK路径不正确

**解决方案**:
```bash
# 检查设备连接
hdc list targets

# 检查SDK路径
dir "C:\Program Files\Huawei\DevEco Studio\sdk\default"
```

### 问题3: 找不到配置文件

**解决方案**:
确保配置文件路径正确：
```
d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server\augment-mcp-config.json
```

如果路径不同，请修改JSON中的 `cwd` 字段。

## 📝 配置文件位置

- **MCP配置JSON**: `harmonyos-mcp-server/augment-mcp-config.json`
- **MCP服务器主程序**: `harmonyos-mcp-server/src/main.py`
- **依赖列表**: `harmonyos-mcp-server/requirements.txt`

## 🔄 更新配置

如果需要修改配置：

1. 在Augment设置中找到 `harmonyos-tools`
2. 点击编辑按钮 ✏️
3. 修改配置
4. 保存并重启MCP服务器

## 📚 相关文档

- [项目README](README.md)
- [快速开始](docs/quickstart.md)
- [构建系统指南](docs/build-system-guide.md)
- [hidumper使用指南](docs/hidumper-uitree-guide.md)
- [项目状态](PROJECT_STATUS.md)

## 🎉 开始使用

配置完成后，你可以：

1. ✅ 让AI帮你管理HarmonyOS设备
2. ✅ 自动化构建和部署流程
3. ✅ 分析应用UI结构
4. ✅ 获取实时日志
5. ✅ 完整的端到端开发工作流

享受AI辅助的HarmonyOS开发！🚀

