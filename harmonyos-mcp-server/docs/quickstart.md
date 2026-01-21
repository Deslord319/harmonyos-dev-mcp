# 快速开始

本指南将帮助你快速设置和使用HarmonyOS MCP Server。

## 前置要求

1. **Python 3.8+**
2. **HarmonyOS SDK** (通过DevEco Studio安装)
3. **HarmonyOS设备或模拟器**
4. **Cursor或Cline** (AI IDE)

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-org/harmonyos-mcp-server.git
cd harmonyos-mcp-server
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

#### Windows (PowerShell)
```powershell
$env:HARMONYOS_SDK_PATH="C:\Huawei\Sdk"
```

#### Linux/Mac
```bash
export HARMONYOS_SDK_PATH="/path/to/harmonyos/sdk"
```

### 4. 验证安装

运行测试脚本验证基础功能:

```bash
python tests/test_basic.py
```

你应该看到:
- ✅ 配置验证成功
- ✅ 找到连接的设备
- ✅ 能够获取设备日志

## 配置Cursor

### 1. 创建配置文件

在你的HarmonyOS项目根目录创建 `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "harmonyos-tools": {
      "command": "python",
      "args": ["D:/path/to/harmonyos-mcp-server/src/main.py"],
      "env": {
        "HARMONYOS_SDK_PATH": "C:/Huawei/Sdk"
      }
    }
  }
}
```

**注意**: 将路径替换为你的实际路径。

### 2. 重启Cursor

关闭并重新打开Cursor,让配置生效。

### 3. 验证MCP连接

在Cursor的聊天窗口中输入:

```
@harmonyos-tools list_devices
```

如果配置成功,你应该看到连接的设备列表。

## 基础使用

### 列出设备

```
@harmonyos-tools 列出所有连接的设备
```

### 构建应用

```
@harmonyos-tools 构建当前项目的debug版本
```

### 安装应用

```
@harmonyos-tools 安装应用到设备
```

### 运行应用

```
@harmonyos-tools 运行应用 com.example.myapp
```

### 查看日志

```
@harmonyos-tools 获取最近100行日志
```

## 完整工作流示例

假设你正在开发一个登录界面:

1. **开发UI**
```
@harmonyos-tools 我想创建一个登录界面,包含用户名输入框、密码输入框和登录按钮
```

2. **构建应用**
```
@harmonyos-tools 构建应用
```

3. **安装到设备**
```
@harmonyos-tools 安装应用到第一个设备
```

4. **运行应用**
```
@harmonyos-tools 运行应用
```

5. **查看日志**
```
@harmonyos-tools 如果应用崩溃了,帮我看看日志
```

## 常见问题

### Q: 提示"未找到hdc工具"

**A**: 确保:
1. 已安装DevEco Studio和HarmonyOS SDK
2. `HARMONYOS_SDK_PATH` 环境变量设置正确
3. hdc工具在 `{SDK}/toolchains/` 目录下

### Q: 提示"没有找到连接的设备"

**A**: 确保:
1. 设备已通过USB连接或网络连接
2. 设备已开启开发者模式
3. 运行 `hdc list targets` 能看到设备

### Q: MCP工具无法调用

**A**: 检查:
1. `.cursor/mcp.json` 路径是否正确
2. Python路径是否正确
3. 查看Cursor的MCP日志

## 下一步

- 查看 [API参考](api-reference.md) 了解所有可用工具
- 查看 [架构设计](architecture.md) 了解系统原理
- 查看 [UI树获取](ui-tree.md) 了解核心功能

## 获取帮助

- [GitHub Issues](https://github.com/your-org/harmonyos-mcp-server/issues)
- [开发者论坛](https://developer.huawei.com/consumer/cn/forum/)

