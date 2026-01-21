# HarmonyOS AI编程开发方案调研 - 第一阶段

## 调研时间
2026年1月19日

## 1. HarmonyOS开发环境和工具链

### 1.1 DevEco Studio IDE现状
- **最新版本**：DevEco Studio 5.0.0及以上（已更新至6.0.0 Beta5）
- **官方AI工具**：CodeGenie（深度集成的AI辅助编程工具）
- **主要功能**：
  - 编译构建、UI实时预览、代码调试、性能调优、模拟器
  - AI代码生成、编译报错智能解析
  - 自然语言交互、行内续写、编辑区生成

### 1.2 IDE对第三方AI插件的支持情况
**问题确认**：DevEco Studio对主流AI编程插件支持度确实很差
- **GitHub Copilot**：需要安装特定版本（1.4.6.4092以下）才能工作
- **Cursor、Augment、Qoder等**：官方不支持安装
- **官方立场**：华为开发者论坛确认DevEco Studio考虑支持其他主流AI插件，但目前仍无明确时间表

### 1.3 HarmonyOS SDK支持
- **最新版本**：HarmonyOS 5.0及以上
- **开发语言**：ArkTS（优选语言）
- **框架**：ArkUI（UI框架）、ArkData（数据管理）、ArkWeb（Web组件）
- **工具链**：包括ArkCompiler、Hvigor构建系统等

---

## 2. AI编程工具集成方案

### 2.1 官方CodeGenie工具
**优点**：
- 深度集成DevEco Studio，无需额外配置
- 支持HarmonyOS特定知识和ArkTS代码补全
- 支持编译报错智能分析

**局限**：
- 功能相对基础，不如Cursor等专业AI编程工具
- 不支持自定义工具集成
- 无法使用Claude等高级LLM

### 2.2 第三方AI工具的集成困境
- DevEco Studio基于IntelliJ IDEA，但对插件生态的开放度有限
- GitHub Copilot版本限制问题
- Cursor等现代AI编程工具无法直接集成

### 2.3 替代方案
- **Trae**：被认为是Claude的完美替代方案（国内可用）
- **豆包MarsCode**：腾讯AI代码助手，支持多语言和编辑器
- **其他方案**：使用外部AI工具生成代码后手动集成

---

## 3. HarmonyOS应用调试和自动化能力

### 3.1 UI测试框架（UITest）
**核心功能**：
- 控件查找与操作（基于多种属性匹配）
- UI交互操作（点击、滑动、文本输入等）
- 外设行为模拟（键盘、鼠标、触控板、手写笔）
- 截图和UI事件监听

**API接口**：
```
- Driver.findComponent(ON.type('Button'))：查找控件
- Component.click()：点击操作
- Driver.click(x, y)：坐标级操作
- 支持相对位置查找（within操作）
```

### 3.2 DOM树访问可行性
**重要发现**：
- HarmonyOS提供ArkUI Inspector工具，可在DevEco Studio中查看UI树
- UITest框架支持获取控件属性信息
- 但**没有直接的DOM树导出API**
- 需要通过UITest框架间接访问UI结构

### 3.3 调试工具
- **ArkUI Inspector**：可视化查看应用UI显示效果
- **DevTools**：用于ArkWeb组件调试
- **DevEco Profiler**：性能分析工具（CPU、内存、网络）
- **JSVM调试工具**：用于逻辑执行调试

### 3.4 自动化测试框架
- **Hypium**：HarmonyOS NEXT配套UI自动化测试框架
- **支持语言**：Python和ArkTS
- **覆盖场景**：全场景多形态设备测试

---

## 4. MCP（Model Context Protocol）概述

### 4.1 MCP基本概念
- **定义**：模型上下文协议，用于AI模型与外部系统交互
- **核心价值**：标准化工具集成，减少资源冗余和Prompt调试成本
- **支持语言**：Python、Node.js、TypeScript、Java、Kotlin

### 4.2 MCP架构
- **MCP服务器**：为LLM提供上下文、数据和功能的外部服务
- **MCP客户端**：连接到MCP服务器的应用程序
- **协议**：基于JSON-RPC的标准化通信

### 4.3 MCP与AI编程工具的集成
- **Cursor**：原生支持MCP
- **Claude Desktop**：支持MCP服务器集成
- **OpenAI SDK**：通过openai-agents支持MCP

### 4.4 已有HarmonyOS MCP项目
- **HarmonyOS-mcp-server**：用于操控HarmonyOS设备的MCP服务器
- **Harmony Tools MCP**：基于FastMCP的HarmonyOS命令行工具封装
- 这些项目证明了MCP与HarmonyOS集成的可行性

---

## 5. HarmonyOS开发者账号和签名配置

### 5.1 自动签名方案
- **调试签名**：DevEco Studio提供自动签名方案
- **两种模式**：
  1. 关联注册应用进行签名（与AGC绑定，支持开放能力）
  2. 未关联注册应用进行签名（简化模式）

### 5.2 签名流程自动化可能性
- **自动签名条件**：
  - 需要登录华为账号（Sign In）
  - 系统时间需与北京时间同步
  - 支持通过DevEco Studio UI自动完成

- **自动化困难**：
  - 登录涉及账号密码或OAuth认证
  - 需要与AGC系统交互
  - 涉及用户隐私和安全问题

### 5.3 AppGallery Connect（AGC）
- **功能**：全生命周期服务平台
- **API支持**：提供Publishing API等开放接口
- **自动化可能**：可通过API进行应用管理和签名相关操作

---

## 6. 关键问题和技术障碍

### 6.1 IDE集成问题
| 问题 | 现状 | 可行性 |
|------|------|--------|
| DevEco Studio支持Cursor | 不支持 | 低 - 需要DevEco改进 |
| DevEco Studio支持Copilot | 部分支持（版本限制） | 中 - 可用但有限制 |
| 官方CodeGenie功能 | 基础AI能力 | 高 - 可直接使用 |
| 外部AI工具集成 | 困难 | 低 - 需要变通方案 |

### 6.2 DOM树访问问题
- **直接导出**：不可行 - 官方无此API
- **间接访问**：可行 - 通过UITest框架
- **需要开发**：自定义MCP工具来封装UITest API

### 6.3 开发者账号自动化
- **登录自动化**：困难 - 涉及安全认证
- **签名自动化**：可行 - DevEco Studio支持自动签名
- **AGC操作自动化**：可行 - 提供API接口

---

## 7. 现有开源项目参考

### 7.1 HarmonyOS MCP相关项目
1. **HarmonyOS-mcp-server**
   - 用途：操控HarmonyOS设备
   - 兼容：Claude Desktop、OpenAI SDK
   - 状态：已实现

2. **Harmony Tools MCP**
   - 用途：HarmonyOS命令行工具封装
   - 基础：FastMCP框架
   - 工具：hdc、hvigor等

### 7.2 参考架构
- MCP服务器可以封装DevEco Studio命令行工具
- 可以通过hdc（HarmonyOS Device Connector）进行设备交互
- 可以通过hvigor构建系统进行编译自动化

---

## 8. 初步结论

### 8.1 可行性评估

| 方案组件 | 可行性 | 难度 | 优先级 |
|---------|--------|------|--------|
| 官方CodeGenie集成 | 高 | 低 | 高 |
| 自定义MCP工具开发 | 高 | 中 | 高 |
| DOM树拉取MCP工具 | 中 | 中 | 中 |
| 开发者账号自动化 | 中 | 高 | 中 |
| 签名配置自动化 | 高 | 中 | 高 |
| 第三方IDE插件集成 | 低 | 高 | 低 |

### 8.2 推荐方案方向
1. **短期**：基于官方CodeGenie + 自定义MCP工具
2. **中期**：开发HarmonyOS专用MCP工具集
3. **长期**：考虑与DevEco Studio深度集成或开发插件

---

## 9. 后续调研需求

### 9.1 需要深入研究的方向
1. **MCP工具开发**：
   - 如何基于UITest框架开发MCP工具
   - DOM树结构的提取方法
   - 性能和实时性考虑

2. **自动化签名**：
   - DevEco Studio CLI自动签名命令
   - AGC API的签名相关接口
   - 账号认证的自动化方案

3. **AI模型集成**：
   - Claude SDK对HarmonyOS的支持
   - 本地LLM部署在HarmonyOS上的可行性
   - Context Protocol的最佳实践

4. **开发工具链**：
   - hdc命令行工具的完整功能
   - hvigor构建系统的自动化能力
   - DevEco Studio的命令行接口

### 9.2 需要获取的资源
- DevEco Studio命令行工具文档
- HarmonyOS UITest框架完整API文档
- AGC开放API文档
- MCP服务器开发完整示例

