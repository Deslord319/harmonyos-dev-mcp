# HarmonyOS MCP Server 故障排除指南

## 问题: MCP服务器显示"未连接"或"初始化失败"

### 诊断步骤

#### 步骤1: 验证Python环境

```bash
# 检查Python版本
python --version

# 检查Python路径
where python

# 应该显示类似:
# C:\Users\admin\AppData\Local\Programs\Python\Python314\python.exe
```

#### 步骤2: 验证依赖安装

```bash
cd d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server

# 检查fastmcp
python -c "import fastmcp; print('✅ fastmcp:', fastmcp.__version__)"

# 检查loguru
python -c "import loguru; print('✅ loguru 已安装')"
```

#### 步骤3: 运行启动测试

```bash
python test_mcp_startup.py
```

**期望输出**:
```
🎉 所有测试通过！MCP服务器可以正常启动。
总计: 4/4 测试通过
```

#### 步骤4: 手动启动MCP服务器

```bash
python src/main.py
```

**期望输出**:
```
2026-01-21 10:37:49 | INFO | HarmonyOS MCP Server 启动
2026-01-21 10:37:49 | INFO | hdc路径: C:\Program Files\...
```

如果服务器正常启动，它会一直运行等待连接（不会退出）。

### 常见问题和解决方案

#### 问题1: "ModuleNotFoundError: No module named 'fastmcp'"

**解决方案**:
```bash
pip install -r requirements.txt
```

#### 问题2: "配置验证失败,请检查环境变量"

**原因**: 无法找到hdc工具

**解决方案**:
```bash
# 检查hdc是否存在
dir "C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"

# 如果不存在，检查DevEco Studio是否正确安装
```

#### 问题3: Augment中MCP服务器显示"Disconnected"

**可能原因**:
1. Python不在PATH中
2. 工作目录路径不正确
3. 环境变量未正确传递

**解决方案A: 使用绝对Python路径**

修改 `augment-mcp-config.json`:
```json
{
  "harmonyos-tools": {
    "command": "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
    "args": ["src/main.py"],
    "cwd": "d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server",
    "env": {
      "HARMONYOS_SDK_PATH": "C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default"
    }
  }
}
```

**解决方案B: 检查工作目录**

确保 `cwd` 路径正确:
```bash
# 检查目录是否存在
dir d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server

# 检查src/main.py是否存在
dir d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server\src\main.py
```

**解决方案C: 查看Augment日志**

1. 打开VSCode设置
2. 搜索 "Augment"
3. 找到 "MCP Servers" 部分
4. 点击 `harmonyos-tools` 旁边的日志图标
5. 查看错误信息

#### 问题4: "找不到设备"

**解决方案**:
```bash
# 检查设备连接
hdc list targets

# 应该显示:
# 3QC0124A24000365
```

### 完整的重新配置步骤

如果以上都不行，尝试完全重新配置：

#### 1. 卸载并重新安装依赖

```bash
cd d:\lxl\ho_dev_app_mcp\harmonyos-mcp-server
pip uninstall fastmcp loguru -y
pip install -r requirements.txt
```

#### 2. 验证安装

```bash
python test_mcp_startup.py
```

#### 3. 获取Python完整路径

```bash
where python
# 复制输出的路径，例如:
# C:\Users\admin\AppData\Local\Programs\Python\Python314\python.exe
```

#### 4. 更新Augment配置

使用完整的Python路径更新 `augment-mcp-config.json`:

```json
{
  "harmonyos-tools": {
    "command": "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
    "args": ["src/main.py"],
    "cwd": "d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server"
  }
}
```

注意: 移除了 `env` 部分，因为现在会自动检测SDK路径。

#### 5. 重新导入到Augment

1. 打开VSCode设置 → Augment → MCP Servers
2. 删除现有的 `harmonyos-tools` 配置
3. 点击 "Import from JSON"
4. 选择更新后的 `augment-mcp-config.json`

#### 6. 重启VSCode

完全关闭并重新打开VSCode。

#### 7. 验证连接

在Augment中输入:
```
列出所有HarmonyOS设备
```

### 获取帮助

如果问题仍然存在，请提供以下信息：

1. **Python版本**: `python --version`
2. **测试结果**: `python test_mcp_startup.py` 的完整输出
3. **Augment日志**: MCP服务器的错误日志
4. **配置文件**: `augment-mcp-config.json` 的内容

## 成功标志

当一切正常时，你应该看到：

✅ `python test_mcp_startup.py` 显示 "4/4 测试通过"  
✅ Augment MCP Servers 中 `harmonyos-tools` 显示 "Connected"  
✅ 在Augment中可以成功调用MCP工具  
✅ 能够列出设备: `3QC0124A24000365`

