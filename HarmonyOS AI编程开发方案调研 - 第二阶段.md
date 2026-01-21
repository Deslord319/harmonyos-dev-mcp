# HarmonyOS AI编程开发方案调研 - 第二阶段

## 调研时间
2026年1月19日

## 1. 主流AI编程工具对比

### 1.1 Cursor IDE

**基本信息**：
- **基础**：基于VS Code
- **开发语言**：TypeScript、JavaScript
- **支持语言**：Python、JavaScript、Java、C++、C#、Ruby、Go、Swift等主流语言
- **国内可用性**：可直接使用

**核心功能**：
- Tab自动补全（基于定制模型）
- Agent功能（将想法转化为代码）
- 智能代码建议和自动完成
- 多模型集成（Claude 3.5、GPT-4等）

**MCP支持**：
- **原生支持MCP**（Model Context Protocol）
- 支持三种传输方式：
  1. **STDIO**：本地命令行服务器（由Cursor管理）
  2. **SSE**：服务器发送事件（本地/远程）
  3. **Streamable HTTP**：HTTP端点（本地/远程）
- 支持MCP协议能力：Tools、Prompts、Resources、Roots、Elicitation
- 可通过mcp.json配置自定义MCP服务器
- 支持一键安装MCP服务器（从官方库）
- 支持OAuth认证和静态凭证

**配置方式**：
```json
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["mcp-server.py"],
      "env": {
        "API_KEY": "value"
      }
    }
  }
}
```

**HarmonyOS兼容性**：
- 理论上支持ArkTS（TypeScript方言）
- 但需要通过MCP工具来获取HarmonyOS特定知识
- 官方没有HarmonyOS专用MCP服务器

### 1.2 Windsurf IDE

**基本信息**：
- **新一代AI IDE**，由Codeium开发
- **开发基础**：基于VS Code
- **特点**：实时协同、上下文感知

**核心功能**：
- Cascade功能（比Cursor的Agent更强大）
- 深度上下文感知
- 多模型协同
- 实时协作支持
- 智能代码补全

**优势**：
- 提供免费额度
- 对国内用户友好
- 实时协同能力强于Cursor

**劣势**：
- 对国内用户的支持可能不如Cursor稳定
- MCP支持情况未明确说明

**HarmonyOS兼容性**：
- 与Cursor类似，需要MCP工具支持
- 暂无官方HarmonyOS支持

### 1.3 Cline（VS Code插件）

**基本信息**：
- **形式**：VS Code插件（开源）
- **特点**：可在Cursor和Windsurf中使用
- **灵活性**：高度可定制

**核心功能**：
- 强大的MCP支持
- 文件操作和代码生成
- 复杂任务的上下文理解
- 与多个AI模型集成

**MCP支持**：
- **全面支持MCP**
- 允许用户通过配置参数自行添加MCP服务
- 作为MCP的"主机(Host)"角色
- 能够发现、连接并调用MCP Server提供的工具

**优势**：
- 开源，可自定义
- MCP生态支持最好
- 可在多个IDE中使用
- 完全免费

**HarmonyOS兼容性**：
- 与Cursor相同，需要MCP工具
- 作为MCP客户端，最适合与自定义HarmonyOS MCP工具集成

### 1.4 GitHub Copilot

**基本信息**：
- **集成方式**：IDE插件
- **DevEco Studio支持**：需要特定版本（1.4.6.4092以下）

**HarmonyOS兼容性**：
- 可在DevEco Studio中使用（版本限制）
- 功能相对基础
- 对ArkTS的支持有限

---

## 2. AI编程工具与HarmonyOS的集成方案

### 2.1 推荐方案对比

| 方案 | 工具组合 | 可行性 | 优势 | 劣势 | 优先级 |
|------|---------|--------|------|------|--------|
| **方案A** | Cursor + 自定义HarmonyOS MCP | 高 | 原生MCP支持、功能强大、国内可用 | 需要开发MCP工具 | 高 |
| **方案B** | Cline + 自定义HarmonyOS MCP | 高 | 开源免费、MCP生态最好、可定制 | 需要自行配置 | 高 |
| **方案C** | Windsurf + 自定义HarmonyOS MCP | 中 | 免费额度、上下文感知强 | 国内支持不确定 | 中 |
| **方案D** | DevEco Studio + CodeGenie | 高 | 官方集成、无需额外配置 | 功能有限、不支持第三方工具 | 中 |
| **方案E** | DevEco Studio + GitHub Copilot | 中 | 功能相对完整 | 版本限制、集成困难 | 低 |

### 2.2 方案A详细设计：Cursor + HarmonyOS MCP

**架构**：
```
Cursor IDE
    ↓
MCP Client (内置)
    ↓
HarmonyOS MCP Server (自定义)
    ├── UITest API封装
    ├── DevEco CLI工具
    ├── hdc设备连接
    ├── hvigor构建系统
    └── AGC API集成
```

**实现步骤**：
1. 开发HarmonyOS MCP Server（Python或Node.js）
2. 在Cursor的mcp.json中配置MCP服务器
3. 在Cursor中使用MCP工具进行HarmonyOS开发
4. 通过MCP获取DOM树、执行构建、运行应用等

**优势**：
- Cursor原生支持MCP，无需额外配置
- 可以充分利用Cursor的Agent功能
- MCP工具可复用于其他IDE（Windsurf、Cline等）
- 支持多种传输方式（本地STDIO或远程HTTP）

**实现难度**：中等（需要开发MCP工具）

### 2.3 方案B详细设计：Cline + HarmonyOS MCP

**架构**：
```
VS Code
    ↓
Cline插件
    ↓
MCP Client (Cline内置)
    ↓
HarmonyOS MCP Server (自定义)
```

**实现步骤**：
1. 在VS Code中安装Cline插件
2. 开发HarmonyOS MCP Server
3. 在Cline配置中添加MCP服务器
4. 使用Cline进行HarmonyOS开发

**优势**：
- 完全开源免费
- Cline的MCP支持最为完善
- 可在Cursor或Windsurf中同时使用
- 最灵活的定制选项

**实现难度**：中等（需要开发MCP工具和配置）

### 2.4 官方CodeGenie方案

**现状**：
- DevEco Studio 5.0.0+内置CodeGenie
- 支持ArkTS代码补全和生成
- 支持编译报错智能分析
- 免费使用

**局限**：
- 功能相对基础
- 不支持自定义工具集成
- 无法使用高级LLM（如Claude）
- 不支持MCP

**使用场景**：
- 快速原型开发
- 学习HarmonyOS开发
- 简单代码补全

---

## 3. HarmonyOS MCP工具的设计方案

### 3.1 MCP工具的核心功能需求

基于前期调研，HarmonyOS MCP工具应包含以下功能：

| 功能模块 | 描述 | 技术方案 | 优先级 |
|---------|------|---------|--------|
| **DOM树拉取** | 获取应用UI结构 | 通过UITest框架 + hdc | 高 |
| **元素查找** | 基于属性查找UI元素 | UITest API包装 | 高 |
| **元素操作** | 点击、输入、滑动等 | UITest API包装 | 高 |
| **应用构建** | 编译HarmonyOS应用 | hvigor命令行工具 | 高 |
| **应用部署** | 安装和运行应用 | hdc命令行工具 | 高 |
| **设备管理** | 连接和管理设备 | hdc设备连接 | 中 |
| **日志收集** | 获取应用日志 | hdc logcat | 中 |
| **性能分析** | 获取性能数据 | DevEco Profiler | 中 |
| **签名管理** | 自动签名配置 | DevEco CLI + AGC API | 中 |
| **代码生成** | 基于需求生成代码 | 与LLM集成 | 高 |

### 3.2 MCP工具的实现技术栈

**推荐方案**：Python + FastMCP

**理由**：
- FastMCP是MCP的Python实现框架
- 开发效率高
- 易于集成系统命令（hdc、hvigor等）
- 已有成熟的HarmonyOS工具集成案例

**项目结构**：
```
harmonyos-mcp-server/
├── src/
│   ├── main.py                 # 主入口
│   ├── tools/
│   │   ├── ui_tools.py        # UI相关工具（DOM树、元素操作）
│   │   ├── build_tools.py     # 构建工具（hvigor集成）
│   │   ├── device_tools.py    # 设备工具（hdc集成）
│   │   ├── signing_tools.py   # 签名工具（自动签名）
│   │   ├── log_tools.py       # 日志工具
│   │   └── agc_tools.py       # AppGallery Connect API
│   ├── utils/
│   │   ├── hdc_wrapper.py     # hdc命令包装
│   │   ├── hvigor_wrapper.py  # hvigor命令包装
│   │   ├── deveco_cli.py      # DevEco CLI包装
│   │   └── agc_client.py      # AGC API客户端
│   └── config.py              # 配置管理
├── requirements.txt
├── mcp.json                   # Cursor MCP配置示例
└── README.md
```

### 3.3 DOM树拉取的技术方案

**可行性分析**：

| 方法 | 可行性 | 技术难度 | 说明 |
|------|--------|---------|------|
| **直接API** | 低 | 低 | HarmonyOS无直接DOM导出API |
| **UITest框架** | 高 | 中 | 通过UITest获取控件信息并构建树 |
| **ArkUI Inspector** | 中 | 高 | 需要解析DevEco Studio的输出 |
| **hdc dump** | 中 | 中 | 通过hdc命令获取窗口信息 |

**推荐方案**：UITest框架 + hdc dump

**实现流程**：
1. 使用hdc连接设备
2. 通过UITest API遍历当前页面的控件树
3. 获取每个控件的属性（id、type、text、bounds等）
4. 构建JSON格式的DOM树
5. 返回给MCP客户端

**示例输出**：
```json
{
  "root": {
    "type": "Page",
    "id": "page_root",
    "children": [
      {
        "type": "Button",
        "id": "btn_submit",
        "text": "提交",
        "bounds": {
          "x": 100,
          "y": 200,
          "width": 200,
          "height": 50
        },
        "enabled": true,
        "visible": true
      },
      {
        "type": "TextInput",
        "id": "input_name",
        "text": "",
        "bounds": {
          "x": 100,
          "y": 100,
          "width": 200,
          "height": 40
        }
      }
    ]
  }
}
```

### 3.4 MCP工具的Tool定义

**UITest相关工具**：

```python
@server.tool()
def get_ui_tree(bundle_name: str) -> dict:
    """获取应用的UI树结构"""
    # 实现逻辑

@server.tool()
def find_element(bundle_name: str, selector: dict) -> list:
    """查找UI元素"""
    # 实现逻辑

@server.tool()
def click_element(bundle_name: str, element_id: str) -> bool:
    """点击UI元素"""
    # 实现逻辑

@server.tool()
def input_text(bundle_name: str, element_id: str, text: str) -> bool:
    """在输入框输入文本"""
    # 实现逻辑
```

**构建和部署工具**：

```python
@server.tool()
def build_app(project_path: str, build_type: str = "debug") -> dict:
    """构建HarmonyOS应用"""
    # 实现逻辑

@server.tool()
def install_app(device_id: str, app_path: str) -> bool:
    """安装应用到设备"""
    # 实现逻辑

@server.tool()
def run_app(device_id: str, bundle_name: str) -> bool:
    """运行应用"""
    # 实现逻辑

@server.tool()
def get_app_logs(device_id: str, bundle_name: str, lines: int = 100) -> str:
    """获取应用日志"""
    # 实现逻辑
```

**设备管理工具**：

```python
@server.tool()
def list_devices() -> list:
    """列出所有连接的设备"""
    # 实现逻辑

@server.tool()
def get_device_info(device_id: str) -> dict:
    """获取设备信息"""
    # 实现逻辑

@server.tool()
def connect_device(device_ip: str, port: int = 5555) -> bool:
    """连接远程设备"""
    # 实现逻辑
```

---

## 4. 与DevEco Studio的集成方案

### 4.1 命令行工具集成

DevEco Studio提供命令行工具，可用于自动化：

**可用命令**：
- `deveco build`：编译应用
- `deveco run`：运行应用
- `deveco sign`：签名应用
- `deveco install`：安装应用

**集成方式**：
在MCP工具中封装这些命令，通过subprocess调用

### 4.2 自动签名集成

**自动签名流程**：
1. 登录华为账号（需要处理认证）
2. 关联AGC应用
3. 自动生成签名证书
4. 配置到build-profile.json5

**MCP工具实现**：
```python
@server.tool()
def auto_sign_app(project_path: str, bundle_name: str, team_id: str = None) -> dict:
    """自动签名应用"""
    # 1. 检查登录状态
    # 2. 获取AGC应用信息
    # 3. 生成签名证书
    # 4. 更新build-profile.json5
    # 返回签名结果
```

**限制**：
- 需要用户提前在DevEco Studio中登录
- 或需要存储用户凭证（安全风险）
- 建议使用OAuth流程

---

## 5. 与Claude/LLM的集成

### 5.1 集成方式

**方案1：通过Cursor集成**
- 使用Cursor的Agent功能
- Agent自动调用MCP工具
- 无需额外集成

**方案2：直接使用Claude SDK**
- 在MCP工具中调用Claude API
- 用于代码生成和分析
- 需要API密钥

**方案3：本地LLM**
- 部署本地LLM（如Ollama）
- 用于离线开发
- 性能和准确度可能较低

### 5.2 推荐方案

**Cursor + HarmonyOS MCP + Claude**

流程：
1. 开发者在Cursor中描述需求
2. Cursor的Agent调用HarmonyOS MCP工具
3. MCP工具获取应用状态、DOM树等信息
4. Agent基于信息和Claude的能力生成代码
5. 开发者审查并应用代码

---

## 6. 现有开源项目参考

### 6.1 HarmonyOS MCP相关项目

**HarmonyOS-mcp-server**
- 用途：操控HarmonyOS设备
- 兼容：Claude Desktop、OpenAI SDK
- 状态：已实现
- 参考价值：高

**Harmony Tools MCP**
- 用途：HarmonyOS命令行工具封装
- 基础：FastMCP框架
- 工具：hdc、hvigor等
- 参考价值：高

### 6.2 其他MCP项目参考

- **GitHub MCP Server**：文件系统操作
- **Google Drive MCP Server**：云存储集成
- **Slack MCP Server**：消息通知
- **Database MCP Server**：数据库操作

---

## 7. 实施路线图

### 第一阶段（基础工具）
- 开发HarmonyOS MCP Server基础框架
- 实现UITest工具集成
- 实现hdc设备连接
- 实现基本的DOM树拉取

**时间**：2-3周
**优先级**：高

### 第二阶段（构建和部署）
- 集成hvigor构建系统
- 实现自动签名功能
- 实现应用安装和运行
- 实现日志收集

**时间**：2-3周
**优先级**：高

### 第三阶段（高级功能）
- 集成AGC API
- 实现性能分析工具
- 实现代码生成工具
- 优化MCP工具性能

**时间**：3-4周
**优先级**：中

### 第四阶段（IDE集成）
- 开发Cursor集成指南
- 开发Cline集成指南
- 开发DevEco Studio插件（可选）
- 发布到开源社区

**时间**：2-3周
**优先级**：中

---

## 8. 关键技术决策

### 8.1 MCP服务器的实现语言

**选择**：Python + FastMCP

**理由**：
- FastMCP是官方推荐的Python框架
- 开发效率高
- 易于集成系统命令
- 已有成熟的HarmonyOS工具集成案例
- 社区活跃

### 8.2 传输方式

**选择**：STDIO（本地开发）+ HTTP（远程部署）

**理由**：
- STDIO用于本地开发，无需额外配置
- HTTP用于团队协作和远程开发
- 支持OAuth认证
- 易于扩展

### 8.3 与LLM的集成

**选择**：通过Cursor/Cline集成，而非直接集成

**理由**：
- Cursor/Cline已有完整的LLM集成
- 避免重复开发
- 用户可自由选择LLM
- 更灵活的架构

---

## 9. 风险和挑战

### 9.1 技术风险

| 风险 | 影响 | 缓解方案 |
|------|------|---------|
| HarmonyOS API变化 | 工具失效 | 定期维护、版本管理 |
| UITest框架限制 | DOM树不完整 | 结合hdc dump、文档补充 |
| 设备连接不稳定 | 工具调用失败 | 重试机制、错误处理 |
| 签名流程复杂 | 自动化困难 | 分步实现、用户指导 |

### 9.2 安全风险

| 风险 | 影响 | 缓解方案 |
|------|------|---------|
| 账号凭证泄露 | 账号被盗 | 使用OAuth、环境变量 |
| 代码注入 | 应用被篡改 | 输入验证、沙箱执行 |
| 设备访问权限 | 隐私泄露 | 权限管理、用户确认 |

### 9.3 可维护性风险

| 风险 | 影响 | 缓解方案 |
|------|------|---------|
| 文档不完整 | 使用困难 | 详细文档、示例代码 |
| 社区支持不足 | 问题无法解决 | 积极维护、社区建设 |
| 版本兼容性 | 工具失效 | 版本管理、CI/CD测试 |

