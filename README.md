# HarmonyOS MCP Server

[![PyPI - harmonyos-dev-mcp](https://img.shields.io/pypi/v/harmonyos-dev-mcp.svg?label=harmonyos-dev-mcp)](https://pypi.org/project/harmonyos-dev-mcp/)
[![PyPI - harmonyos-mcp-common](https://img.shields.io/pypi/v/harmonyos-mcp-common.svg?label=harmonyos-mcp-common)](https://pypi.org/project/harmonyos-mcp-common/)

MCP (Model Context Protocol) 服务器，为 HarmonyOS 应用开发提供 AI 辅助工具。

## 📋 目录结构

```
mcp_ho_dev/
├── packages/
│   └── common/              # 公共模块
│       └── src/common/
│           ├── config/          # 配置管理
│           │   └── settings.py  # 统一配置（环境变量、配置文件）
│           ├── tools/           # 工具基类和注册器
│           │   ├── base.py      # 工具基类（错误处理、参数校验）
│           │   ├── error_handler.py  # 统一错误处理（重试、分类）
│           │   ├── logger_config.py  # 日志配置（追踪、性能）
│           │   └── registry.py   # 工具注册器
│           └── server/          # 服务器基类
│               └── base_server.py  # 统一服务器基类
│
├── services/
│   ├── harmonyos_mcp/          # 主服务（设备管理、UI测试）
│   │   └── src/harmonyos_mcp/
│   │       ├── server.py          # MCP服务器入口
│   │       ├── container.py       # 设备容器管理
│   │       ├── config.py         # 服务配置
│   │       ├── tools/            # MCP工具
│   │       │   ├── general.py      # 通用工具（设备、包管理）
│   │       │   ├── build.py        # 构建部署工具
│   │       │   ├── ui.py           # UI自动化工具
│   │       │   ├── ui_tree.py     # UI树工具
│   │       │   └── log/            # 日志工具
│   │       │       └── query.py    # 日志查询
│   │       └── utils/            # 工具函数
│   │           └── logger.py     # 日志配置
│   │
│   └── harmonyos_compile_mcp/  # 编译服务
│       └── src/harmonyos_compile_mcp/
│           ├── server.py          # MCP服务器入口
│           ├── container.py       # 编译管理器
│           ├── config.py         # 服务配置
│           ├── tools/            # MCP工具
│           │   └── compile_tools.py  # 编译工具
│           └── utils/            # 工具函数
│               └── compile_wrapper.py  # 编译包装器
│
├免 pyproject.toml              # Python项目管理
├── .opencode/                  # OpenCode配置
│   └── AGENTS.md            # Agent职责定义
└── README.md                   # 本文档
```

## 🚀 快速开始

### 前置要求

- Python 3.10+
- uv (Python包管理器）
- HarmonyOS DevEco Studio
- HarmonyOS hdc 命令行工具

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd mcp_ho_dev

# 安装依赖
uv sync --all-packages

# 或使用 pip
pip install -e .
```

### 配置

#### 方式1: 环境变量（推荐）

```bash
# 日志级别
export HARMONYOS_LOG_LEVEL=INFO

# 最大重试次数
export HARMONYOS_MAX_RETRIES=3

# 重试延迟（秒）
export HARMONYOS_RETRY_DELAY=1.0

# 超时时间（秒）
export HARMONYOS_TIMEOUT=1800

# 设备超时（秒）
export HARMONYOS_DEVICE_TIMEOUT=30

# 编译超时（秒）
export HARMONYOS_COMPILE_TIMEOUT=1800

# 启用缓存
export HARMONYOS_CACHE_ENABLED=true
```

#### 方式2: 配置文件

创建 `~/.config/harmonyos_mcp/config.json`:

```json
{
  "log_level": "INFO",
  "max_retries": 3,
  "retry_delay": 1.0,
  "timeout": 1800,
  "cache_enabled": false,
  "cache_ttl": 3600,
  "device_timeout": 30,
  "compile_timeout": 1800
}
```

### 启动服务

```bash
# 启动 harmonyos-mcp 服务
uv run harmonyos-mcp

# 启动 harmonyos-compile-mcp 服务
uv run harmonyos-compile-mcp
```

## 🔧 MCP 工具列表

### harmonyos-mcp（17 个工具）

#### 通用工具（3个）

| 工具名 | 描述 | 错误码 | 重试 |
|--------|------|--------|------|
| `list_devices` | 列出所有连接的 HarmonyOS 设备 | DEVICE_LIST_ERROR | ✅ 3次 |
| `query_package` | 查询包信息（列表/Abilities/权限） | QUERY_PACKAGE_ERROR | ✅ 3次 |
| `logs_query` | 日志查询（拉取/解析/过滤/分析） | LOGS_QUERY_ERROR | ✅ 3次 |

#### 构建部署（4个）

| 工具名 | 描述 | 错误码 | 重试 |
|--------|------|--------|------|
| `build_app` | 构建 HarmonyOS 应用 | BUILD_APP_ERROR | ✅ 3次 |
| `install_app` | 安装 HAP 包到设备 | INSTALL_APP_ERROR | ✅ 3次 |
| `run_app` | 运行应用 | RUN_APP_ERROR | ❌ 不重试 |
| `uninstall_app` | 卸载应用 | UNINSTALL_APP_ERROR | ✅ 3次 |

#### UI 操作（6个）

| 工具名 | 描述 | 错误码 | 重试 |
|--------|------|--------|------|
| `screenshot` | 屏幕截图 | SCREENSHOT_ERROR | ✅ 3次 |
| `click_element` | 点击元素 | CLICK_ELEMENT_ERROR | ✅ 3次 |
| `long_press_element` | 长按元素 | LONG_PRESS_ERROR | ✅ 3次 |
| `input_text` | 输入文本 | INPUT_TEXT_ERROR | ✅ 3次 |
| `swipe` | 滑动操作 | SWIPE_ERROR | ✅ 3次 |
| `drag` | 拖拽操作 | DRAG_ERROR | ✅ 3次 |
| `press_key` | 模拟按键 | PRESS_KEY_ERROR | ✅ 3次 |
| `find_element` | 查找元素 | FIND_ELEMENT_ERROR | ✅ 3次 |

#### UI 树（2个）

| 工具名 | 描述 | 错误码 | 重试 |
|--------|------|--------|------|
| `get_ui_tree` | 获取 UI 组件树 | GET_UI_TREE_ERROR | ✅ 3次 |
| `list_windows` | 列出所有窗口 | LIST_WINDOWS_ERROR | ✅ 3次 |

### harmonyos-compile-mcp（8 个工具）

| 工具名 | 描述 | 错误码 | 重试 |
|--------|------|--------|------|
| `check_wsl` | 检查 WSL 环境 | WSL_CHECK_ERROR | ❌ 不重试 |
| `check_harmonyos_compiler_tools` | 检查编译工具链 | COMPILER_TOOLS_CHECK_ERROR | ❌ 不重试 |
| `clone_library` | 克隆三方库 | CLONE_LIBRARY_ERROR | ✅ 3次 |
| `analyze_build_system` | 分析构建系统 | ANALYZE_BUILD_ERROR | ✅ 3次 |
| `read_build_files` | 读取构建文件 | READ_BUILD_FILES_ERROR | ✅ 3次 |
| `write_compile_script` | 写入编译脚本 | WRITE_SCRIPT_ERROR | ✅ 3次 |
| `execute_compile_script` | 执行编译脚本 | EXECUTE_SCRIPT_ERROR | ❌ 不重试 |
| `verify_so_output` | 验证 .so 输出 | VERIFY_SO_ERROR | ✅ 3次 |

## 🔍 错误处理

### 错误分类

| 分类 | 说明 | 示例 |
|------|------|------|
| `network` | 网络连接错误 | 连接超时、DNS解析失败 |
| `timeout` | 操作超时 | 设备响应超时 |
| `permission` | 权限错误 | 设备权限不足 |
| `validation` | 参数校验错误 | 路径非法、参数缺失 |
| `device` | 设备错误 | 设备未连接、设备异常 |
| `compilation` | 编译错误 | 构建失败、链接错误 |

### 错误响应格式

所有错误响应包含以下字段：

```json
{
  "success": false,
  "error": "错误描述",
  "error_code": "ERROR_CODE",
  "error_category": "network",
  "context": {
    "device_id": "xxx",
    "operation": "xxx"
  },
  "retryable": true
}
```

### 重试机制

- **默认重试次数**: 3次
- **退避策略**: 指数退避（1s, 2s, 4s）
- **可重试错误**: network, timeout, device
- **不可重试错误**: validation, permission

## 📊 日志记录

### 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| `DEBUG` | 详细调试信息 | 函数调用、参数值 |
| `INFO` | 常规信息 | 工具执行成功、服务启动 |
| `WARNING` | 警告信息 | 重试、配置缺失 |
| `ERROR` | 错误信息 | 工具执行失败、异常捕获 |

### 结构化日志字段

```json
{
  "timestamp": "2026-02-28T10:30:00Z",
  "level": "INFO",
  "message": "工具执行成功: list_devices",
  "tool": "list_devices",
  "event": "tool_call",
  "request_id": "550e8400-...",
  "success": true,
  "duration_seconds": 1.234,
  "duration_formatted": "1.23s",
  "params": {
    "device_id": "xxx"
  }
}
```

### 性能追踪

每个工具调用自动记录：
- 执行时间
- 内存使用（可选）
- 请求ID
- 成功/失败状态

### 请求追踪

支持请求链追踪，每个请求有唯一ID：
```
request_id: 550e8400-e29b-4d9f-a8b1-2c3d4e5f6a7
tool: list_devices
event: request_start
↓
event: request_end
duration: 1.23s
```

## 🔌 故障排查

### 常见问题

#### 1. 设备未连接

**症状**: `list_devices` 返回空列表

**排查步骤**:
1. 检查 hdc 是否已安装: `hdc --version`
2. 检查设备连接: `hdc list targets`
3. 查看日志: `tail -f ~/.local/share/harmonyos_mcp/logs/mcp.log`

**解决方案**:
- 重启 hdc 服务
- 重新连接设备
- 检查 USB 线缆

#### 2. 编译失败

**症状**: `execute_compile_script` 返回非零退出码

**排查步骤**:
1. 检查 WSL 环境: `wsl --list --verbose`
2. 检查编译工具: `check_harmonyos_compiler_tools`
3. 查看编译日志: `cat build.log`

**解决方案**:
- 安装缺失的编译工具
- 配置正确的 WSL 环境
- 检查构建脚本语法

#### 3. UI自动化失败

**症状**: `find_element` 找不到元素

**排查步骤**:
1. 获取 UI 树: `get_ui_tree`
2. 截图检查: `screenshot`
3. 查看元素选择器

**解决方案**:
- 等待页面加载完成
- 使用更稳定的元素选择器
- 增加显式等待

### 日志位置

```bash
# Linux/macOS
~/.local/share/harmonyos_mcp/logs/

# Windows
%APPDATA%/harmonyos_mcp/logs/
```

### 调试模式

启用详细日志：

```bash
export HARMONYOS_LOG_LEVEL=DEBUG
uv run harmonyos-mcp
```

## 🧪 开发

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/unit/test_general.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=services/harmonyos_mcp --cov-report=html
```

### 代码规范

```bash
# 格式化代码
uv run black services/

# 检查代码规范
uv run ruff check services/

# 类型检查
uv run mypy services/
```

### 构建 wheel 包

```bash
# 构建 harmonyos-mcp
cd services/harmonyos_mcp
uv run hatch build

# 构建 harmonyos-compile-mcp
cd ../harmonyos_compile_mcp
uv run hatch build
```

## 📝 MCP 客户端配置

### Cursor

在项目根目录创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "harmonyos": {
      "command": "harmonyos-mcp",
      "env": {
        "HARMONYOS_LOG_LEVEL": "INFO"
      }
    },
    "harmonyos-compile": {
      "command": "harmonyos-compile-mcp"
    }
  }
}
```

### Cline (VSCode)

在 VSCode 设置中添加：

```json
{
  "cline.mcpServers": {
    "harmonyos": {
      "command": "harmonyos-mcp"
    },
    "harmonyos-compile": {
      "command": "harmonyos-compile-mcp"
    }
  }
}
```

### Augment

在 VSCode settings.json 中添加：

```json
{
  "augment.mcpServers": {
    "harmonyos": {
      "command": "harmonyos-mcp"
    },
    "harmonyos-compile": {
      "command": "harmonyos-compile-mcp"
    }
  }
}
```

### Claude Desktop

编辑 `~/AppData/Roaming/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "harmonyos": {
      "command": "harmonyos-mcp"
    },
    "harmonyos-compile": {
      "command": "harmonyos-compile-mcp"
    }
  }
}
```

### Qoder

在 Qoder 配置文件中添加：

```json
{
  "mcp_servers": {
    "harmonyos": {
      "command": "harmonyos-mcp",
      "enabled": true
    },
    "harmonyos-compile": {
      "command": "harmonyos-compile-mcp",
      "enabled": true
    }
  }
}
```

### LibreChat

在 `librechat.yaml` 中添加：

```yaml
mcpServers:
  harmonyos:
    command: harmonyos-mcp
    timeout: 60000
    env:
      HARMONYOS_LOG_LEVEL: INFO
  harmonyos-compile:
    command: harmonyos-compile-mcp
    timeout: 60000
```

## 🏗️ 架构设计

### 模块化设计

```
┌─────────────────────────────────┐
│         MCP Client (AI)          │
└────────────┬──────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼───┐         ┌──▼──────┐
│ harmonyos-│         │ harmonyos-│
│    mcp   │         │compile_mcp│
└────┬────┘         └────┬────┘
     │                    │
     └────────┬──────────┘
              │
         ┌────▼────┐
         │  Common  │
         │  Module  │
         └────┬────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼──┐ ┌──▼──┐ ┌──▼──┐
│ Tools  │ │Error │ │Logger │ │Config │
│Registry│ │Handler│ │Config │ │Manager│
└────────┘ └──────┘ └──────┘ └──────┘
```

### 职责分离

- **Common Module**: 可复用的基础设施
  - 工具基类和注册器
  - 错误处理和重试机制
  - 日志配置和性能追踪
  - 配置管理

- **harmonyos_mcp**: 设备管理和UI自动化
  - 设备连接和管理
  - 应用构建和部署
  - UI元素操作和自动化
  - 日志查询和分析

- **harmonyos_compile_mcp**: 编译工具链
  - WSL环境检查
  - 编译工具链管理
  - 三方库管理
  - 构建系统分析

## 📈 性能优化

### 缓存策略

- 启用请求缓存（默认TTL: 3600秒）
- 设备列表缓存
- 包信息缓存
- UI树缓存

### 并发控制

- 异步工具执行
- 连接池管理
- 请求限流

### 资源管理

- 自动清理临时文件
- 内存使用监控
- 连接复用

## 🔒 安全考虑

### 输入验证

- 路径安全检查（防止目录遍历）
- 参数类型验证
- 长度限制

### 敏感信息保护

- 日志中隐藏密码、token等敏感字段
- 错误响应中不暴露内部细节
- 配置文件权限控制

### 权限控制

- 设备操作权限验证
- 文件系统访问控制
- 编译操作沙箱隔离

## 📄 许可证

MIT License