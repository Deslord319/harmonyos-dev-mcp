# HarmonyOS应用测试日志

**测试目标**: ~~在硬件设备上成功构建、安装并运行集成了uitree_provider HAR模块的应用~~ **已转向使用hidumper工具获取UI组件树**

**测试时间**: 2026-01-21

**测试环境**:
- 设备: HarmonyOS硬件设备 (ID: 3QC0124A24000365)
- SDK版本: HarmonyOS 6.0.2(22)
- DevEco Studio版本: 5.0.5
- 项目路径: D:\lxl\ho_dev_app_mcp\ho_module_app

---

## 🎯 重大发现：hidumper工具获取UI组件树

### 发现时间
2026-01-21

### 背景
原计划通过UITest框架API创建HAR模块来获取UI组件树，但发现UITest API只能在测试目录中使用，无法在生产代码中使用。经过调研，发现HarmonyOS提供了 `hidumper` 系统工具，可以直接通过命令行获取UI组件树。

### 关键命令

#### 1. 获取所有窗口信息
```bash
hdc shell "hidumper -s WindowManagerService -a '-a'"
```

**输出示例**:
```
myapplication0       0         62173   142   1    102  0    -1   0           [ 613  399  2091 1394 ]
```

**关键信息**:
- 窗口名称: `myapplication0`
- 进程PID: `62173`
- 窗口ID: `142`
- 窗口位置和大小: `[613, 399, 2091, 1394]`

#### 2. 获取指定窗口的完整UI组件树
```bash
hdc shell "hidumper -s WindowManagerService -a '-w <窗口ID> -default -c'"
```

**实际命令**:
```bash
hdc shell "hidumper -s WindowManagerService -a '-w 142 -default -c'"
```

**输出内容**:
- ✅ 完整的组件层级结构（Stack, Row, Button, Image等）
- ✅ 每个组件的详细属性（ID, Depth, FrameRect, Visibility等）
- ✅ 状态变量信息（@State装饰器的变量）
- ✅ 布局约束信息（LayoutConstraint）
- ✅ 渲染节点信息（rsNode）
- ✅ 组件关系（父子关系、兄弟关系）

### 优势分析

| 对比项 | UITest API方案 | hidumper工具方案 |
|--------|---------------|-----------------|
| **代码侵入性** | ❌ 需要在应用中集成HAR模块 | ✅ 无需修改应用代码 |
| **API限制** | ❌ 只能在测试目录使用 | ✅ 系统级工具，无限制 |
| **部署复杂度** | ❌ 需要编译、签名、安装 | ✅ 直接通过hdc调用 |
| **通用性** | ❌ 每个应用都需要集成 | ✅ 适用于任何HarmonyOS应用 |
| **信息完整性** | ⚠️ 需要自己实现采集逻辑 | ✅ 系统提供完整信息 |
| **自动化难度** | ❌ 高（需要处理构建流程） | ✅ 低（直接命令行调用） |

### 技术方案调整

**原方案**:
```
MCP Server → HTTP请求 → HAR模块(UITest API) → UI树数据
```

**新方案**:
```
MCP Server → hdc shell → hidumper → UI树数据
```

---

## 测试步骤记录

### 步骤1: 检查设备连接

**命令**:
```bash
hdc list targets
```

**预期结果**: 显示已连接的设备ID

**实际结果**: ✅ 成功
```
3QC0124A24000365
```

**问题**: 无

**解决方案**: N/A

**自动化可能性**:
- [x] 可以通过MCP工具自动检测
- [ ] 需要手动操作
- [ ] 部分自动化

**自动化建议**: 已在MCP Server中实现 `list_devices` 工具

---

### 步骤2: 测试hidumper获取窗口列表

**命令**:
```bash
hdc shell "hidumper -s WindowManagerService -a '-a'"
```

**预期结果**: 显示所有窗口信息

**实际结果**: ✅ 成功
- 找到应用窗口: `myapplication0`
- 窗口ID: `142`
- 进程PID: `62173`

**问题**: 无

**解决方案**: N/A

**自动化可能性**:
- [x] 可以完全自动化
- [ ] 需要手动操作
- [ ] 部分自动化

**自动化建议**:
1. 解析窗口列表输出
2. 根据bundleName或窗口名称匹配目标应用
3. 提取窗口ID用于后续查询

---

### 步骤3: 测试hidumper获取UI组件树

**命令**:
```bash
hdc shell "hidumper -s WindowManagerService -a '-w 142 -default -c'"
```

**预期结果**: 获取完整的UI组件树

**实际结果**: ✅ 成功
- 获取到完整的组件层级结构
- 包含所有组件属性和状态变量
- 输出格式为文本，易于解析

**问题**: 无

**解决方案**: N/A

**自动化可能性**:
- [x] 可以完全自动化
- [ ] 需要手动操作
- [ ] 部分自动化

**自动化建议**:
1. 实现输出解析器，提取组件信息
2. 构建树形数据结构
3. 提供JSON格式输出供MCP工具使用

---

### 步骤2: 检查项目配置（已废弃）

**说明**: 由于采用hidumper方案，不再需要构建HAR模块，此步骤已废弃。

**检查项**:
- [x] ~~build-profile.json5 配置正确~~
- [x] ~~oh-package.json5 依赖配置~~
- [x] ~~module.json5 权限配置~~
- [x] ~~签名配置~~

**发现的问题**:

**自动化可能性**:

---

### 步骤3: 构建HAR模块

**命令**:
```bash
cd D:\lxl\ho_dev_app_mcp\ho_module_app
hvigorw assembleHar --mode module -p module=uitree_provider
```

**预期结果**: HAR文件成功生成

**实际结果**:

**遇到的错误**:

**错误类型**:
- [ ] 编译错误
- [ ] 依赖错误
- [ ] 配置错误
- [ ] 其他

**错误详情**:

**解决方案**:

**自动化可能性**:

---

### 步骤4: 安装依赖

**命令**:
```bash
"C:\Program Files\Huawei\DevEco Studio\tools\ohpm\bin\ohpm.bat" install
```

**预期结果**: 依赖安装成功

**实际结果**: ✅ 成功
```
install completed in 0s 36ms
```

**遇到的问题**:
1. ❌ ohpm不在系统PATH中
2. ❌ 需要使用完整路径: `C:\Program Files\Huawei\DevEco Studio\tools\ohpm\bin\ohpm.bat`
3. ⚠️ 只安装了测试依赖(hamock, hypium),没有安装hvigor构建工具
4. ⚠️ 项目缺少hvigorw包装脚本
5. ⚠️ hvigor目录为空,缺少hvigor-wrapper.js等关键文件

**自动化可能性**:
- [x] 可以自动检测ohpm路径
- [x] 可以自动执行ohpm install
- [ ] 需要解决hvigor缺失问题

---

### 步骤5: 构建应用HAP

**命令**:
```bash
hvigorw assembleHap --mode module -p module=entry
```

**预期结果**: HAP文件成功生成

**实际结果**:

**遇到的错误**:

**错误分类**:
- [ ] TypeScript编译错误
- [ ] 资源错误
- [ ] 签名错误
- [ ] 依赖错误
- [ ] 其他

**错误详情**:

**解决方案**:

**自动化可能性**:

---

### 步骤6: 签名配置

**问题**: HarmonyOS应用需要签名才能安装

**当前签名状态**:
- [ ] 已配置自动签名
- [ ] 需要手动签名
- [ ] 使用调试签名
- [ ] 使用发布签名

**签名配置位置**:
- build-profile.json5 -> signingConfigs
- local.properties

**遇到的问题**:

**解决步骤**:

**自动化可能性**:
- [ ] 可以自动生成调试签名
- [ ] 可以自动配置签名文件
- [ ] 需要手动配置
- [ ] 可以通过MCP工具辅助

---

### 步骤7: 安装应用到设备

**命令**:
```bash
hdc install entry/build/default/outputs/default/entry-default-signed.hap
```

**预期结果**: 应用安装成功

**实际结果**:

**遇到的错误**:

**错误类型**:
- [ ] 签名验证失败
- [ ] 版本冲突
- [ ] 权限不足
- [ ] 设备空间不足
- [ ] 其他

**解决方案**:

**自动化可能性**:

---

### 步骤8: 运行应用

**命令**:
```bash
hdc shell aa start -a EntryAbility -b <bundle_name>
```

**预期结果**: 应用成功启动

**实际结果**:

**遇到的问题**:

**自动化可能性**:

---

### 步骤9: 验证UITreeService启动

**验证方法**:
1. 查看应用日志
2. 检查端口是否监听
3. 尝试访问HTTP服务

**命令**:
```bash
# 查看日志
hdc hilog | grep UITree

# 检查端口转发
hdc fport tcp:8080 tcp:8080

# 测试HTTP服务
curl http://localhost:8080/get-ui-tree
```

**实际结果**:

**遇到的问题**:

**自动化可能性**:

---

## 问题汇总

### 编译相关问题

| 问题编号 | 问题描述 | 严重程度 | 是否可自动化 | 解决方案 | 状态 |
|---------|---------|---------|------------|---------|------|
| C-001 | @ohos/hvigor-ohos-plugin在公共ohpm仓库不存在 | 🔴 严重 | ❌ 否 | 不应在oh-package.json5中声明此依赖 | ✅ 已解决 |
| C-002 | 使用了错误的构建工具 | 🔴 严重 | ✅ 是 | 应使用hvigorw.js而非hvigor.js | ✅ 已解决 |
| C-003 | oh-package.json5中main路径错误 | 🟡 中等 | ✅ 是 | 修正为./src/main/ets/index.ets | ✅ 已解决 |
| C-004 | ArkTS代码不符合严格模式 | 🟡 中等 | ⚠️ 部分 | 需要修复代码以符合ArkTS规范 | 🔄 进行中 |

### 配置相关问题

| 问题编号 | 问题描述 | 严重程度 | 是否可自动化 | 解决方案 |
|---------|---------|---------|---------|---------|
| CF-001 | | | | |

### 签名相关问题

| 问题编号 | 问题描述 | 严重程度 | 是否可自动化 | 解决方案 |
|---------|---------|---------|---------|---------|
| S-001 | | | | |

### 运行时问题

| 问题编号 | 问题描述 | 严重程度 | 是否可自动化 | 解决方案 |
|---------|---------|---------|---------|---------|
| R-001 | | | | |

---

## 自动化机会分析

### 高优先级自动化项

1. **自动签名配置**
   - 当前状态: 
   - 自动化方案: 
   - 预期收益: 

2. **依赖管理**
   - 当前状态: 
   - 自动化方案: 
   - 预期收益: 

3. **构建流程**
   - 当前状态: 
   - 自动化方案: 
   - 预期收益: 

### 中优先级自动化项

### 低优先级自动化项

---

## 测试结论

**测试状态**: 
- [ ] 成功
- [ ] 部分成功
- [ ] 失败

**成功标准**:
- [ ] HAR模块成功构建
- [ ] 应用成功安装
- [ ] 应用成功运行
- [ ] UITreeService成功启动
- [ ] 可以获取UI树数据

**下一步行动**:
1. 在DevEco Studio中尝试构建项目，观察IDE执行的命令
2. 检查是否需要下载特定版本的SDK组件
3. 查看DevEco Studio的构建日志，了解完整的构建流程

**需要改进的地方**:
- SDK路径配置的自动检测
- 环境变量的自动设置
- 缺失组件的自动诊断

**可以立即自动化的项目**:
- 设备连接检测
- ohpm依赖安装
- 工具路径自动发现

---

## 📊 当前测试状态总结 (2026-01-21)

### ✅ 已成功完成
1. **设备连接** - 设备ID: `3QC0124A24000365`
2. **工具定位** - ohpm, hvigor, SDK路径均已找到
3. **依赖安装** - `ohpm install` 成功
4. **配置文件** - local.properties 已配置

### 🔴 当前阻塞
**问题**: `hvigor assembleHar` 报错 "SDK component missing"

**已尝试**:
- 设置 DEVECO_SDK_HOME 环境变量
- 配置 local.properties (sdk.dir, nodejs.dir)
- 使用本地 hvigor 工具

**待解决**: 需要确认SDK组件是否完整，或是否需要在IDE中首次构建

