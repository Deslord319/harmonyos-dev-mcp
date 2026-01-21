# Augment集成指南

**版本**: 1.0  
**更新时间**: 2026-01-21  
**状态**: ✅ 已配置完成

## 📋 概述

HarmonyOS MCP Server已成功集成到Augment中，可以通过AI助手直接调用HarmonyOS开发工具。

## ✅ 已完成的配置

### 1. VSCode Settings配置

配置文件位置: `C:\Users\admin\AppData\Roaming\Code\User\settings.json`

已添加的配置:
```json
{
  "augment.mcpServers": {
    "harmonyos-tools": {
      "command": "python",
      "args": ["src/main.py"],
      "cwd": "d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server",
      "env": {
        "HARMONYOS_SDK_PATH": "C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default"
      }
    }
  }
}
```

### 2. 环境变量

- `HARMONYOS_SDK_PATH`: DevEco Studio SDK路径
- 自动检测hdc工具路径
- 自动检测hvigor工具路径

## 🎯 可用的MCP工具

配置完成后，在Augment中可以使用以下工具：

### 设备管理
- **list_devices** - 列出所有连接的HarmonyOS设备
- **list_windows** - 列出设备上的所有窗口

### 应用构建
- **build_app** - 构建HarmonyOS应用
  - 参数: `project_path` (项目路径)

### 应用部署
- **install_app** - 安装应用到设备
  - 参数: `hap_path` (HAP包路径), `device_id` (可选)
- **run_app** - 运行应用
  - 参数: `bundle_name` (包名), `device_id` (可选)
- **uninstall_app** - 卸载应用
  - 参数: `bundle_name` (包名), `device_id` (可选)

### UI树获取
- **get_ui_tree** - 获取应用的UI组件树
  - 参数: `device_id` (可选), `bundle_name` (可选), `window_id` (可选)
  - 返回: 结构化的UI树JSON数据

### 日志查看
- **get_logs** - 获取设备日志（支持多种过滤方式）
  - 参数:
    - `device_id` (可选) - 设备ID
    - `lines` (可选，默认100) - 返回的日志行数
    - `bundle_name` (可选) - 按应用包名过滤日志
    - `tag` (可选) - 按日志标签过滤
    - `pid` (可选) - 按进程ID过滤

## 🚀 使用示例

### 示例1: 查看连接的设备

在Augment中询问:
```
请列出所有连接的HarmonyOS设备
```

AI将调用 `list_devices` 工具并返回设备列表。

### 示例2: 获取应用UI树

在Augment中询问:
```
获取myapplication应用的UI组件树
```

AI将调用 `get_ui_tree` 工具，自动查找窗口并返回UI树结构。

### 示例3: 构建并安装应用

在Augment中询问:
```
构建ho_module_app项目并安装到设备
```

AI将依次调用:
1. `build_app` - 构建项目
2. `install_app` - 安装到设备
3. `run_app` - 启动应用

### 示例4: 查看应用日志（支持过滤）

在Augment中询问:
```
获取com.example.myapp应用的最近50行日志
```

AI将调用 `get_logs` 工具，使用 `bundle_name` 参数过滤指定应用的日志。

**更多日志过滤示例**:
- 按包名过滤: "获取com.example.myapp的日志"
- 按标签过滤: "获取标签为Ace的日志"
- 按进程ID过滤: "获取进程12345的日志"
- 组合过滤: "获取com.example.myapp应用中标签为Ace的日志"

### 示例5: 分析UI结构

在Augment中询问:
```
分析myapplication的UI结构，找出所有Button组件
```

AI将:
1. 调用 `get_ui_tree` 获取UI树
2. 分析JSON数据
3. 列出所有Button组件及其属性

## 🔧 验证配置

### 方法1: 重启VSCode

1. 完全关闭VSCode
2. 重新打开VSCode
3. 打开Augment面板
4. 查看MCP服务器状态

### 方法2: 查看MCP服务器日志

在Augment面板中应该能看到 `harmonyos-tools` 服务器已连接。

### 方法3: 测试工具调用

在Augment中输入:
```
使用harmonyos-tools的list_devices工具列出设备
```

如果返回设备列表，说明配置成功。

## 📝 配置文件备份

配置文件已备份到:
- `d:\lxl\ho_dev_app_mcp\vscode_settings_backup.json`

如需恢复，可以从备份文件复制。

## 🐛 故障排除

### 问题1: MCP服务器未启动

**症状**: Augment中看不到harmonyos-tools服务器

**解决方案**:
1. 检查Python是否在PATH中: `python --version`
2. 检查依赖是否安装: `pip list | findstr fastmcp`
3. 手动测试启动: `python d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server\src\main.py`

### 问题2: 工具调用失败

**症状**: 调用工具时返回错误

**解决方案**:
1. 检查设备是否连接: `hdc list targets`
2. 检查SDK路径是否正确
3. 查看MCP服务器日志

### 问题3: 找不到hdc工具

**症状**: 提示"hdc工具路径未配置"

**解决方案**:
1. 确认DevEco Studio已安装
2. 检查环境变量 `HARMONYOS_SDK_PATH`
3. 手动设置hdc路径

## 📚 相关文档

- [快速开始指南](quickstart.md)
- [构建系统指南](build-system-guide.md)
- [hidumper使用指南](hidumper-uitree-guide.md)
- [项目状态](../PROJECT_STATUS.md)

## 🎉 下一步

现在你可以:

1. **在Augment中测试工具** - 尝试各种MCP工具调用
2. **开发HarmonyOS应用** - 让AI帮助你编写、构建、测试应用
3. **分析UI结构** - 使用UI树工具分析应用界面
4. **自动化工作流** - 让AI自动完成构建-部署-测试流程

享受AI辅助的HarmonyOS开发体验！🚀

