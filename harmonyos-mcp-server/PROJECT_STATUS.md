# HarmonyOS MCP Server - 项目状态

**更新时间**: 2026-01-21

## 🎯 重大技术突破

### 🎊 Augment集成成功 (2026-01-21 11:03)

**状态**: ✅ **成功连接并可用**

**问题诊断过程**:
1. 初始配置使用相对路径 + `cwd` 参数 → 连接失败
2. 尝试多种配置格式（option1/2/3）→ 均失败
3. 查看Augment日志发现关键错误：
   ```
   Stderr: python.exe: can't open file 'C:\\Users\\admin\\AppData\\Local\\Programs\\Microsoft VS Code\\run_mcp.py'
   ```
4. **根本原因**: Augment **不遵守配置中的 `cwd` 参数**，在VSCode安装目录下查找脚本

**解决方案**:
- ❌ 错误配置: 使用相对路径 + `cwd`
  ```json
  {
    "command": "python.exe",
    "args": ["run_mcp.py"],
    "cwd": "d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server"
  }
  ```
- ✅ 正确配置: 在 `args` 中使用绝对路径
  ```json
  {
    "command": "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
    "args": ["d:/lxl/ho_dev_app_mcp/harmonyos-mcp-server/run_mcp.py"]
  }
  ```

**配置文件**: `augment-config-absolute-path.json`

**验证结果**:
- ✅ MCP服务器成功启动
- ✅ Augment显示"Connected"状态
- ✅ 8个MCP工具全部可用

**关键经验**:
1. Augment的MCP配置不在VSCode settings.json，而在Augment自己的设置面板
2. 顶层配置键必须是 `"mcpServers"`
3. **不要依赖 `cwd` 参数** - 使用绝对路径更可靠
4. 查看Augment日志是诊断问题的关键：`%APPDATA%\Code\logs\<日期>\window<N>\exthost\Augment.vscode-augment\Augment.log`

---

### hidumper工具方案 (2026-01-21)

**背景**: 原计划通过UITest框架API创建HAR模块来获取UI组件树，但发现UITest API只能在测试目录中使用。

**突破**: 发现HarmonyOS系统提供的 `hidumper` 工具可以直接获取UI组件树，无需修改应用代码！

**技术对比**:

| 方案 | UITest API + HAR模块 | hidumper系统工具 |
|------|---------------------|-----------------|
| 代码侵入性 | ❌ 需要集成HAR模块 | ✅ 零侵入 |
| API限制 | ❌ 只能在测试目录使用 | ✅ 无限制 |
| 部署复杂度 | ❌ 需要编译、签名、安装 | ✅ 直接命令行调用 |
| 通用性 | ❌ 每个应用都需要集成 | ✅ 适用于任何应用 |
| 自动化难度 | ❌ 高 | ✅ 低 |

**关键命令**:
```bash
# 获取窗口列表
hdc shell "hidumper -s WindowManagerService -a '-a'"

# 获取UI组件树
hdc shell "hidumper -s WindowManagerService -a '-w <窗口ID> -default -c'"
```

**影响**:
- ✅ 大幅简化技术方案
- ✅ 提高通用性和可维护性
- ✅ 加速开发进度

详见: [hidumper UI组件树获取指南](docs/hidumper-uitree-guide.md)

---

## 📊 当前进度

### ✅ 已完成

#### 第一阶段: 基础工具与可行性验证

- [x] **1.1 环境准备与项目初始化**
  - 创建项目结构
  - 配置依赖管理 (requirements.txt)
  - 设置日志系统
  - 配置管理模块

- [x] **1.2 hdc工具封装**
  - HdcWrapper类实现
  - 设备管理: list_devices
  - 应用管理: install_app, uninstall_app, start_app
  - 文件操作: push_file, pull_file
  - 日志收集: get_logs
  - Shell执行: execute_shell
  - 端口转发: forward_port

- [x] **1.3 hvigor构建工具封装** ⭐ **已完全重构**
  - HvigorWrapper类实现（355行，完全重写）
  - 自动检测DevEco Studio安装路径
  - 自动配置local.properties
  - 构建功能: build_har, build_hap, build_app
  - 清理功能: clean
  - 构建产物查找
  - **关键发现**: 必须使用DevEco Studio自带的hvigorw.js和Node.js

- [x] **1.4 核心攻关: UI树获取方案** ⭐ **技术方案已确定**
  - ~~原方案: UITest框架 + HAR模块~~ (已废弃)
  - ✅ **新方案: hidumper系统工具**
  - 无需修改应用代码
  - 直接通过命令行获取完整UI组件树
  - 包含组件层级、属性、状态变量等所有信息

- [x] **1.6 MCP基础工具实现** ✅ **已完成**
  - list_devices - 列出设备
  - get_logs - 获取日志
  - build_app - 构建应用
  - install_app - 安装应用
  - run_app - 运行应用
  - uninstall_app - 卸载应用

- [x] **1.5 MCP工具: get_ui_tree实现** ⭐ **已完成**
  - ✅ 基于hidumper工具实现
  - ✅ 在HdcWrapper中添加hidumper相关方法
  - ✅ 创建UITreeParser解析器
  - ✅ 实现get_ui_tree MCP工具
  - ✅ 实现list_windows MCP工具
  - ✅ 支持按包名自动查找窗口
  - ✅ 支持直接指定窗口ID

- [x] **命令行构建系统调研** ⭐ **重大成果**
  - 完整的构建流程验证
  - 详细的问题记录和解决方案
  - 自动化建议和最佳实践
  - 详见: [构建系统指南](docs/build-system-guide.md)

- [x] **1.7 Augment集成** ⭐ **已完成并成功连接**
  - ✅ 配置VSCode settings.json
  - ✅ 添加harmonyos-tools MCP服务器
  - ✅ 设置环境变量和工作目录
  - ✅ 创建集成文档和使用指南
  - ✅ **解决Augment cwd参数bug** (2026-01-21)
    - 发现问题: Augment不遵守配置中的`cwd`参数
    - 解决方案: 在`args`中使用绝对路径代替相对路径
    - 最终配置: `augment-config-absolute-path.json`
    - 状态: ✅ **成功连接**
  - 详见: [Augment集成指南](docs/augment-integration.md)

### 🚧 进行中

- [ ] **1.8 端到端测试**
  - ✅ Augment连接成功
  - [ ] 在Augment中测试MCP工具调用
  - [ ] 验证完整的开发工作流
  - [ ] 收集使用反馈和优化建议

### ⏳ 待开始

- [ ] **1.7 Cursor/Cline集成测试**
- [ ] **1.8 端到端流程验证**

## 📁 项目结构

```
harmonyos-mcp-server/
├── src/
│   ├── main.py                 # MCP服务器主入口 ✅ (399行)
│   ├── config.py               # 配置管理 ✅
│   ├── utils/
│   │   ├── __init__.py         # 工具模块初始化 ✅
│   │   ├── logger.py           # 日志配置 ✅
│   │   ├── hdc_wrapper.py      # hdc工具封装 ✅ (430行，新增hidumper支持)
│   │   ├── hvigor_wrapper.py   # hvigor工具封装 ✅ (355行)
│   │   └── uitree_parser.py    # UI树解析器 ✅ (150行，新增)
│   └── tools/
│       ├── ui_tools.py         # UI工具 (待开发)
│       ├── build_tools.py      # 构建工具 (待开发)
│       ├── device_tools.py     # 设备工具 (待开发)
│       └── signing_tools.py    # 签名工具 (待开发)
├── tests/
│   └── test_basic.py           # 基础测试 ✅
├── docs/
│   ├── quickstart.md           # 快速开始文档 ✅
│   ├── build-system-guide.md   # 构建系统指南 ✅ (150行)
│   └── hidumper-uitree-guide.md # hidumper使用指南 ✅ (150行)
├── .cursor/
│   └── mcp.json                # Cursor配置示例 ✅
├── requirements.txt            # Python依赖 ✅
├── .gitignore                  # Git忽略文件 ✅
└── README.md                   # 项目说明 ✅
```

## 🎯 已实现的MCP工具

| 工具名称 | 功能描述 | 状态 | 更新 |
|---------|---------|------|------|
| `list_devices` | 列出所有连接的设备 | ✅ | |
| `get_logs` | 获取设备日志（支持多种过滤） | ✅ | 2026-01-21 新增过滤功能 |
| `build_app` | 构建HarmonyOS应用 | ✅ | |
| `install_app` | 安装应用到设备 | ✅ | |
| `run_app` | 运行应用 | ✅ | |
| `uninstall_app` | 卸载应用 | ✅ | |
| `list_windows` | 列出所有窗口 | ✅ | |
| `get_ui_tree` | 获取UI树结构 | ✅ | |
| `find_element` | 查找UI元素 | ⏳ | |
| `click_element` | 点击UI元素 | ⏳ | |
| `input_text` | 输入文本 | ⏳ | |

### get_logs 工具详细说明

**支持的过滤参数**:
- `bundle_name` - 按应用包名过滤日志
- `tag` - 按日志标签过滤（如 "Ace", "JSAPP"）
- `pid` - 按进程ID过滤
- `lines` - 限制返回的日志行数（默认100）

**使用示例**:
```python
# 获取指定应用的日志
get_logs(bundle_name="com.example.myapp", lines=50)

# 获取特定标签的日志
get_logs(tag="Ace", lines=100)

# 组合过滤
get_logs(bundle_name="com.example.myapp", tag="Ace", lines=30)
```

**详细文档**: [日志过滤指南](docs/log-filtering-guide.md)

## 🔧 技术栈

- **语言**: Python 3.8+
- **MCP框架**: FastMCP
- **日志**: Loguru
- **HarmonyOS工具**: hdc, hvigorw, UITest

## 📝 下一步计划

### 优先级1: 核心功能 (本周)

1. **UI树提供模块开发**
   - 创建HarmonyOS测试应用
   - 集成UITest框架
   - 开发HTTP服务模块
   - 实现UI树遍历算法

2. **get_ui_tree工具实现**
   - 实现端口转发
   - HTTP请求处理
   - JSON解析和验证

### 优先级2: 集成测试 (下周)

1. **Cursor集成测试**
   - 配置.cursor/mcp.json
   - 测试工具调用
   - 验证返回结果

2. **端到端流程验证**
   - 创建完整测试场景
   - 验证工作流程
   - 性能测试

## ⚠️ 已知问题

1. **环境依赖**
   - 需要手动配置HARMONYOS_SDK_PATH环境变量
   - hdc工具路径自动检测可能在某些环境下失败

2. **错误处理**
   - 部分命令的错误处理需要增强
   - 超时机制需要优化

3. **文档**
   - API参考文档待完善
   - 架构设计文档待编写

## 🎉 里程碑

- [x] **M1**: 项目初始化 (2026-01-21)
- [x] **M2**: 基础工具封装完成 (2026-01-21)
- [x] **M2.5**: 命令行构建系统调研完成 (2026-01-21)
- [x] **M3**: UI树获取功能实现 (2026-01-21) ⭐ 基于hidumper方案
- [x] **M3.5**: Augment集成成功 (2026-01-21) ⭐ 解决cwd参数bug
- [ ] **M4**: 第一阶段完成 (预计2026-01-22)

---

## 🔨 HarmonyOS命令行构建实战经验

**更新时间**: 2026-01-21
**测试环境**: Windows 11, DevEco Studio 5.0.5, HarmonyOS SDK 6.0.2(22)
**测试设备**: HarmonyOS硬件设备 (ID: 3QC0124A24000365)

### 📚 背景

在开发MCP Server的过程中，我们需要实现自动化构建HarmonyOS应用的能力。这需要通过命令行调用DevEco Studio的工具链，而不是依赖IDE的GUI操作。本章节记录了完整的探索过程和最终解决方案。

### 🎯 目标

实现通过命令行工具完成以下操作：
1. 安装项目依赖
2. 构建HAR模块
3. 构建HAP应用
4. 构建最终的APP包

### 🔍 探索过程

#### 阶段1: 工具链定位 ✅

**任务**: 找到DevEco Studio的所有必要工具

**发现的工具路径**:
```
ohpm:   C:\Program Files\Huawei\DevEco Studio\tools\ohpm\bin\ohpm.bat
hvigor: C:\Program Files\Huawei\DevEco Studio\tools\hvigor\
node:   C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe
SDK:    C:\Program Files\Huawei\DevEco Studio\sdk\default\
```

**关键发现**:
- ✅ 所有工具都在DevEco Studio安装目录下
- ✅ 不需要单独安装Node.js，DevEco Studio自带
- ✅ SDK路径在 `sdk\default` 而非用户目录

#### 阶段2: 依赖安装 ✅

**命令**:
```bash
"C:\Program Files\Huawei\DevEco Studio\tools\ohpm\bin\ohpm.bat" install
```

**结果**: ✅ 成功 (耗时 0s 36ms)

**注意事项**:
- ⚠️ 不要在 `oh-package.json5` 中添加 `@ohos/hvigor` 或 `@ohos/hvigor-ohos-plugin` 依赖
- ⚠️ 这些包不在公共ohpm仓库中，由DevEco Studio内置提供

#### 阶段3: 构建工具选择 ⚠️

**错误尝试1**: 直接使用 hvigor.js
```bash
node "C:\Program Files\Huawei\DevEco Studio\tools\hvigor\hvigor\bin\hvigor.js" \
  -p product=default -p module=uitree_provider assembleHar
```
**结果**: ❌ 失败 - "SDK component missing"

**错误尝试2**: 设置环境变量
```bash
$env:DEVECO_SDK_HOME = "C:\Program Files\Huawei\DevEco Studio\sdk\default"
node hvigor.js ...
```
**结果**: ❌ 仍然失败

**正确方案**: 使用 hvigorw.js (wrapper脚本)
```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' \
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' \
  --mode module -p product=default -p module=uitree_provider assembleHar \
  --analyze=normal --parallel --incremental --daemon
```
**结果**: ✅ 成功 - 构建系统正常工作

### ✅ 最终解决方案

#### 1. 配置 local.properties

在项目根目录创建或修改 `local.properties`:
```properties
sdk.dir=C:\\Program Files\\Huawei\\DevEco Studio\\sdk\\default
nodejs.dir=C:\\Program Files\\Huawei\\DevEco Studio\\tools\\node
```

#### 2. 清理构建产物

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' \
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' \
  --sync -p product=default --analyze=normal --parallel --incremental --no-daemon
```

**输出示例**:
```
> hvigor Finished :entry:clean... after 2 ms
> hvigor Finished ::clean... after 1 ms
> hvigor BUILD SUCCESSFUL in 5 ms
```

#### 3. 构建HAR模块

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' \
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' \
  --mode module -p product=default -p module=<模块名> assembleHar \
  --analyze=normal --parallel --incremental --daemon
```

**参数说明**:
- `--mode module`: 指定构建模式为模块
- `-p product=default`: 指定品类（在build-profile.json5中定义）
- `-p module=<模块名>`: 指定要构建的模块名
- `assembleHar`: 构建HAR包的任务
- `--analyze=normal`: 启用构建分析
- `--parallel`: 并行构建
- `--incremental`: 增量构建
- `--daemon`: 使用守护进程模式

#### 4. 构建HAP应用

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' \
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' \
  --mode module -p product=default assembleHap \
  --analyze=normal --parallel --incremental --daemon
```

**输出示例**:
```
> hvigor Finished :entry:default@CompileArkTS... after 15 s 47 ms
> hvigor Finished :entry:default@PackageHap... after 185 ms
> hvigor BUILD SUCCESSFUL in 18 s 530 ms
```

#### 5. 构建APP包

```bash
& 'C:\Program Files\Huawei\DevEco Studio\tools\node\node.exe' \
  'C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.js' \
  -p product=default assembleApp \
  --analyze=normal --parallel --incremental --daemon
```

### 📋 关键经验总结

#### ✅ 成功要素

1. **使用正确的工具**
   - ✅ 使用 `hvigorw.js` 而非 `hvigor.js`
   - ✅ 使用DevEco Studio自带的Node.js

2. **正确的配置**
   - ✅ 配置 `local.properties` 文件
   - ✅ 不在 `oh-package.json5` 中声明hvigor依赖

3. **正确的命令参数**
   - ✅ 使用 `-p product=<品类名>` 指定品类
   - ✅ 使用 `-p module=<模块名>` 指定模块（构建HAR/HSP时）
   - ✅ 使用 `--daemon` 提升构建速度

#### ❌ 常见错误

1. **错误**: 在 `oh-package.json5` 中添加 `@ohos/hvigor` 依赖
   - **原因**: 这些包不在公共ohpm仓库
   - **解决**: 删除这些依赖声明

2. **错误**: 直接使用 `hvigor.js`
   - **原因**: 缺少wrapper脚本的环境初始化
   - **解决**: 使用 `hvigorw.js`

3. **错误**: SDK路径配置错误
   - **原因**: SDK在 `DevEco Studio\sdk\default` 而非用户目录
   - **解决**: 检查并修正 `local.properties`

4. **错误**: PowerShell引号问题
   - **原因**: 路径中有空格需要特殊处理
   - **解决**: 使用 `&` 操作符和单引号

### 🤖 自动化建议

基于以上经验，MCP Server的构建工具应该：

1. **自动检测DevEco Studio安装路径**
   ```python
   # Windows常见路径
   deveco_paths = [
       "C:\\Program Files\\Huawei\\DevEco Studio",
       "C:\\Program Files (x86)\\Huawei\\DevEco Studio",
   ]
   ```

2. **自动生成 local.properties**
   ```python
   def generate_local_properties(project_path, sdk_path, node_path):
       content = f"""sdk.dir={sdk_path.replace('\\', '\\\\')}
nodejs.dir={node_path.replace('\\', '\\\\')}
"""
       with open(f"{project_path}/local.properties", "w") as f:
           f.write(content)
   ```

3. **提供统一的构建接口**
   ```python
   def build_har(module_name, product="default"):
       cmd = [
           node_exe,
           hvigorw_js,
           "--mode", "module",
           "-p", f"product={product}",
           "-p", f"module={module_name}",
           "assembleHar",
           "--parallel",
           "--incremental",
           "--daemon"
       ]
       return subprocess.run(cmd, ...)
   ```

4. **错误诊断和自动修复**
   - 检测 `oh-package.json5` 中的错误依赖
   - 验证 `local.properties` 配置
   - 提供详细的错误提示

### 📊 性能数据

基于实际测试：

| 操作 | 耗时 | 备注 |
|------|------|------|
| ohpm install | 0.036s | 首次安装 |
| clean | 0.005s | 清理构建产物 |
| assembleHar | 变化 | 取决于代码量 |
| assembleHap | 18.5s | 包含ArkTS编译 |
| assembleApp | 变化 | 取决于模块数量 |

**优化建议**:
- ✅ 使用 `--daemon` 模式（守护进程）
- ✅ 使用 `--incremental` 模式（增量构建）
- ✅ 使用 `--parallel` 模式（并行构建）

### 🔗 参考资料

1. **官方文档**: [使用命令行工具构建应用](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/ide-command-line-building-app-V5)
2. **掘金文章**: [鸿蒙开发：hvigorw，编译构建，实现命令打包](https://juejin.cn/post/7511530724526571546)
3. **测试日志**: `ho_module_app/TESTING_LOG.md`

### 📝 待解决问题

1. **ArkTS严格模式限制**
   - UITest API只能在测试目录使用
   - 需要重新设计UI树提取方案

2. **签名配置**
   - 自动签名配置尚未测试
   - 需要研究调试签名和发布签名的自动化

3. **多模块构建**
   - 需要测试包含多个HAR/HSP的复杂项目
   - 依赖关系的处理

---

## 📞 联系方式

- GitHub: [项目仓库]
- Issues: [问题追踪]
- 文档: [在线文档]

