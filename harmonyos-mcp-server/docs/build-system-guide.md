# HarmonyOS命令行构建系统完全指南

**版本**: 1.0  
**更新时间**: 2026-01-21  
**适用环境**: Windows 11, DevEco Studio 5.0.5, HarmonyOS SDK 6.0.2(22)

## 📖 概述

本指南详细记录了如何通过命令行工具构建HarmonyOS应用，而不依赖DevEco Studio的GUI界面。这对于实现CI/CD流水线、自动化测试和MCP Server集成至关重要。

## 🎯 核心发现

### 关键要点

1. **使用hvigorw.js而非hvigor.js**
   - ❌ 错误: 直接调用 `hvigor.js`
   - ✅ 正确: 使用 `hvigorw.js` wrapper脚本

2. **不要在oh-package.json5中声明hvigor依赖**
   - ❌ 错误: 添加 `@ohos/hvigor` 或 `@ohos/hvigor-ohos-plugin`
   - ✅ 正确: 这些工具由DevEco Studio内置提供

3. **使用DevEco Studio自带的Node.js**
   - ❌ 错误: 使用系统安装的Node.js
   - ✅ 正确: 使用 `DevEco Studio\tools\node\node.exe`

4. **正确配置local.properties**
   - 必须包含 `sdk.dir` 和 `nodejs.dir`
   - 路径使用双反斜杠 `\\`

## 🛠️ 工具链路径

### Windows环境

```
DevEco Studio根目录: C:\Program Files\Huawei\DevEco Studio\

关键工具:
├── tools\
│   ├── node\node.exe           # Node.js运行时
│   ├── hvigor\bin\hvigorw.js   # 构建wrapper脚本
│   ├── hvigor\hvigor\          # hvigor核心
│   ├── hvigor\hvigor-ohos-plugin\  # HarmonyOS插件
│   └── ohpm\bin\ohpm.bat       # 包管理器
└── sdk\default\                # SDK根目录
    ├── openharmony\            # OpenHarmony SDK
    └── hms\                    # HMS SDK
```

## 📝 完整构建流程

### 步骤1: 配置local.properties

在项目根目录创建或修改 `local.properties`:

```properties
sdk.dir=C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default
nodejs.dir=C:\\Program Files\\Huawei\\DevEco Studio\\tools\\node
```

### 步骤2: 安装依赖

```bash
"C:\Program Files\Huawei\DevEco Studio\tools\ohpm\bin\ohpm.bat" install
```

### 步骤3: 清理构建产物

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' `
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' `
  --sync -p product=default `
  --analyze=normal --parallel --incremental --no-daemon
```

### 步骤4: 构建HAR模块

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' `
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' `
  --mode module -p product=default -p module=<模块名> assembleHar `
  --analyze=normal --parallel --incremental --daemon
```

### 步骤5: 构建HAP应用

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' `
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' `
  --mode module -p product=default assembleHap `
  --analyze=normal --parallel --incremental --daemon
```

### 步骤6: 构建APP包

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' `
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' `
  -p product=default assembleApp `
  --analyze=normal --parallel --incremental --daemon
```

## 🔧 命令参数详解

| 参数 | 说明 | 示例 |
|------|------|------|
| `--mode module` | 指定构建模式为模块 | 构建HAR/HAP时使用 |
| `-p product=<品类>` | 指定品类信息 | `-p product=default` |
| `-p module=<模块名>` | 指定模块名称 | `-p module=uitree_provider` |
| `assembleHar` | 构建HAR包任务 | 静态共享包 |
| `assembleHsp` | 构建HSP包任务 | 动态共享包 |
| `assembleHap` | 构建HAP包任务 | 应用模块 |
| `assembleApp` | 构建APP包任务 | 最终上架包 |
| `--analyze=normal` | 启用构建分析 | 生成性能报告 |
| `--parallel` | 并行构建 | 提升构建速度 |
| `--incremental` | 增量构建 | 只构建变更部分 |
| `--daemon` | 守护进程模式 | 提升后续构建速度 |
| `--no-daemon` | 非守护进程模式 | 清理时使用 |

## ⚠️ 常见错误及解决方案

### 错误1: SDK component missing

**原因**: SDK路径配置错误或缺失

**解决方案**:
1. 检查 `local.properties` 中的 `sdk.dir` 配置
2. 确认路径为: `C:\Program Files\Huawei\DevEco Studio\sdk\default`
3. 确认路径使用双反斜杠: `\\`

### 错误2: @ohos/hvigor-ohos-plugin not found (404)

**原因**: 在 `oh-package.json5` 中错误声明了hvigor依赖

**解决方案**:
删除 `oh-package.json5` 中的以下依赖:
```json5
// 删除这些
"@ohos/hvigor": "^5.0.0",
"@ohos/hvigor-ohos-plugin": "^5.0.0"
```

### 错误3: Invalid main file 'index.ets'

**原因**: HAR模块的 `oh-package.json5` 中 `main` 字段路径错误

**解决方案**:
修正为完整路径:
```json5
{
  "main": "./src/main/ets/index.ets"  // 正确
  // "main": "index.ets"  // 错误
}
```

## 📊 性能优化建议

1. **使用守护进程模式** (`--daemon`)
   - 首次构建后，守护进程会保持运行
   - 后续构建速度显著提升

2. **启用增量构建** (`--incremental`)
   - 只编译变更的文件
   - 大幅减少构建时间

3. **启用并行构建** (`--parallel`)
   - 充分利用多核CPU
   - 适合大型项目

## 🤖 Python自动化示例

参见 `harmonyos-mcp-server/src/utils/hvigor_wrapper.py` 中的完整实现。

关键代码片段:

```python
class HvigorWrapper:
    def __init__(self, project_path, deveco_path=None):
        # 自动检测DevEco Studio路径
        self.deveco_path = self._find_deveco_studio(deveco_path)
        self.node_exe = self.deveco_path / "tools/node/node.exe"
        self.hvigorw_js = self.deveco_path / "tools/hvigor/bin/hvigorw.js"
        
        # 自动配置local.properties
        self._ensure_local_properties()
    
    def build_har(self, module_name, product="default"):
        cmd = [
            str(self.node_exe),
            str(self.hvigorw_js),
            "--mode", "module",
            "-p", f"product={product}",
            "-p", f"module={module_name}",
            "assembleHar",
            "--parallel", "--incremental", "--daemon"
        ]
        return subprocess.run(cmd, cwd=self.project_path, ...)
```

## 📚 参考资料

1. [HarmonyOS官方文档 - 命令行构建](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/ide-command-line-building-app-V5)
2. [掘金文章 - hvigorw编译构建](https://juejin.cn/post/7511530724526571546)
3. [项目测试日志](../ho_module_app/TESTING_LOG.md)
4. [项目状态文档](../PROJECT_STATUS.md)

## 📞 问题反馈

如有问题或建议，请提交Issue或Pull Request。

