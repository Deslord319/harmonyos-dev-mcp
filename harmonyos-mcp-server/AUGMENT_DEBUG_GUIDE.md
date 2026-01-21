# Augment MCP 调试指南

**更新时间**: 2026-01-21  
**测试状态**: ✅ MCP服务器stdio通信测试通过

## ✅ 已验证的信息

### 1. MCP服务器本身工作正常
```
✅ 所有模块导入成功
✅ 配置检查通过（SDK自动检测成功）
✅ hdc设备连接成功（找到设备 3QC0124A24000365）
✅ stdio通信测试通过（可以正确响应MCP协议请求）
```

### 2. 路径验证
```
✅ Python路径: C:\Users\admin\AppData\Local\Programs\Python\Python314\python.exe
✅ 工作目录: d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server
✅ main.py: d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server/src/main.py
```

## 🔍 问题定位

MCP服务器本身完全正常，问题在于Augment的配置或启动方式。

## 📋 配置方法（3种方式）

### 方法1: 通过VSCode Settings JSON直接配置（最可靠）

1. **打开VSCode Settings JSON**
   - 按 `Ctrl+Shift+P`
   - 输入 "Preferences: Open User Settings (JSON)"
   - 回车

2. **添加MCP配置**
   
   在JSON文件中添加（如果已有 `augment.mcpServers`，则合并）：
   
   ```json
   {
     "augment.mcpServers": {
       "harmonyos-tools": {
         "command": "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
         "args": ["src/main.py"],
         "cwd": "d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server"
       }
     }
   }
   ```

3. **保存文件** (Ctrl+S)

4. **重启VSCode**

### 方法2: 通过Augment UI导入（如果支持）

1. 打开VSCode设置 → Augment → MCP Servers
2. 点击 "Import from JSON"
3. 选择文件: `augment-mcp-config.json`

**注意**: 如果导入后仍然不工作，使用方法1。

### 方法3: 手动在Augment UI中添加

1. 打开VSCode设置 → Augment → MCP Servers
2. 点击 "Add MCP Server"
3. 填写：
   - **Name**: `harmonyos-tools`
   - **Command**: `C:\Users\admin\AppData\Local\Programs\Python\Python314\python.exe`
   - **Args**: `src/main.py`
   - **Working Directory**: `d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server`

## 🐛 调试步骤

### 步骤1: 查看Augment的MCP日志

1. 打开VSCode设置
2. 搜索 "Augment"
3. 找到 "MCP Servers" 部分
4. 点击 `harmonyos-tools` 旁边的日志图标 📋
5. 查看错误信息

**常见错误**:
- `ENOENT`: 找不到Python或main.py
- `Permission denied`: 权限问题
- `Module not found`: 依赖未安装

### 步骤2: 检查VSCode输出面板

1. 打开输出面板 (Ctrl+Shift+U 或 View → Output)
2. 在下拉菜单中选择 "Augment" 或 "MCP"
3. 查看启动日志

### 步骤3: 手动测试启动命令

在终端中运行Augment会执行的完整命令：

```powershell
cd d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server
C:\Users\admin\AppData\Local\Programs\Python\Python314\python.exe src/main.py
```

服务器应该启动并等待输入（不会退出）。

### 步骤4: 运行stdio通信测试

```bash
cd d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server
python test_mcp_stdio.py
```

应该看到：
```
✅ 测试通过！MCP服务器可以正常通信
```

## 📝 配置文件位置

### 已创建的配置文件

1. **augment-mcp-config.json** - 用于Augment UI导入
   ```
   d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server\augment-mcp-config.json
   ```

2. **augment-settings-snippet.json** - 用于VSCode settings.json
   ```
   d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server\augment-settings-snippet.json
   ```

### VSCode Settings位置

```
C:\Users\admin\AppData\Roaming\Code\User\settings.json
```

## 🔧 可能的解决方案

### 解决方案1: 使用反斜杠路径

某些情况下，Windows路径需要使用反斜杠：

```json
{
  "augment.mcpServers": {
    "harmonyos-tools": {
      "command": "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
      "args": ["src/main.py"],
      "cwd": "d:\\lxl\\ho_dev_app_mcp\\harmonyos-mcp-server"
    }
  }
}
```

### 解决方案2: 使用批处理文件

创建启动脚本 `start_mcp.bat`:
```batch
@echo off
cd /d d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server
C:\Users\admin\AppData\Local\Programs\Python\Python314\python.exe src/main.py
```

然后配置：
```json
{
  "augment.mcpServers": {
    "harmonyos-tools": {
      "command": "d:\\lxl\\ho_dev_app_mcp\\harmonyos-mcp-server\\start_mcp.bat",
      "args": []
    }
  }
}
```

### 解决方案3: 添加环境变量

```json
{
  "augment.mcpServers": {
    "harmonyos-tools": {
      "command": "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
      "args": ["src/main.py"],
      "cwd": "d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

## ✅ 验证成功的标志

当配置成功时：

1. ✅ Augment MCP Servers中 `harmonyos-tools` 显示绿色/已连接状态
2. ✅ 在Augment中输入 "列出所有HarmonyOS设备" 能返回结果
3. ✅ VSCode输出面板中没有MCP相关错误

## 📞 需要提供的调试信息

如果仍然无法连接，请提供：

1. **Augment MCP日志** - 从Augment设置中复制
2. **VSCode输出面板** - Augment/MCP相关的输出
3. **手动启动测试结果** - 运行上述手动测试命令的输出
4. **当前配置** - settings.json中的 `augment.mcpServers` 部分

## 🎯 下一步

1. 尝试**方法1**（直接编辑settings.json）
2. 重启VSCode
3. 查看Augment MCP日志
4. 如果仍有问题，提供上述调试信息

