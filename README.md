# HarmonyOS MCP Server

MCP (Model Context Protocol) 服务器，为 HarmonyOS 应用开发提供 AI 辅助工具。

## 项目结构

```
mcp_ho_dev/
├── packages/
│   └── common/
│       └── src/common/         # 公共模块
│
├── services/
│   ├── harmonyos_mcp/
│   │   └── src/harmonyos_mcp/  # 主服务（设备管理、UI测试）
│   │
│   └── harmonyos_compile_mcp/
│       └── src/harmonyos_compile_mcp/  # 编译服务
│
└── pyproject.toml
```

## 快速开始

### 开发模式

```bash
# 安装依赖
uv sync --all-packages

# 启动 harmonyos-mcp 服务
uv run harmonyos-mcp

# 启动 harmonyos-compile-mcp 服务
uv run harmonyos-compile-mcp
```

### 构建 wheel 包

```bash
# 构建 harmonyos-mcp
cd services/harmonyos_mcp
uv run hatch build
# 输出: dist/harmonyos_mcp-0.3.0-py3-none-any.whl

# 构建 harmonyos-compile-mcp
cd ../harmonyos_compile_mcp
uv run hatch build
# 输出: dist/harmonyos_compile_mcp-0.1.0-py3-none-any.whl
```

### 安装 wheel 包

```bash
# 使用 uv 安装
uv pip install harmonyos_mcp-0.3.0-py3-none-any.whl

# 验证安装
harmonyos-mcp --help
```

## MCP 工具列表

### harmonyos-mcp（17 个工具）

#### 通用工具
| 工具名 | 描述 |
|--------|------|
| list_devices | 列出所有连接的 HarmonyOS 设备 |
| query_package | 查询包信息（列表/Abilities/权限） |
| logs_query | 日志查询（拉取/解析/过滤/分析） |

#### 构建部署
| 工具名 | 描述 |
|--------|------|
| build_app | 构建 HarmonyOS 应用 |
| install_app | 安装 HAP 包到设备 |
| run_app | 运行应用 |
| uninstall_app | 卸载应用 |

#### UI 操作
| 工具名 | 描述 |
|--------|------|
| screenshot | 屏幕截图 |
| click_element | 点击元素 |
| long_press_element | 长按元素 |
| input_text | 输入文本 |
| swipe | 滑动操作 |
| drag | 拖拽操作 |
| press_key | 模拟按键 |
| find_element | 查找元素 |

#### UI 树
| 工具名 | 描述 |
|--------|------|
| get_ui_tree | 获取 UI 组件树 |
| list_windows | 列出所有窗口 |

### harmonyos-compile-mcp（8 个工具）

| 工具名 | 描述 |
|--------|------|
| check_wsl | 检查 WSL 环境 |
| check_harmonyos_compiler_tools | 检查编译工具链 |
| clone_library | 克隆三方库 |
| analyze_build_system | 分析构建系统 |
| read_build_files | 读取构建文件 |
| write_compile_script | 写入编译脚本 |
| execute_compile_script | 执行编译脚本 |
| verify_so_output | 验证 .so 输出 |

## MCP 客户端配置

### Cursor

在项目根目录创建 `.cursor/mcp.json`：

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
  harmonyos-compile:
    command: harmonyos-compile-mcp
    timeout: 60000
```

## 许可证

MIT License
