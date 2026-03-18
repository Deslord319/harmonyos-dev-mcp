# harmonyos-mcp-common

HarmonyOS MCP 通用组件库，提供 MCP 服务器基础架构。

## 功能特性

- **MCP 服务器基础** - 统一的服务器创建和运行框架
- **工具注册系统** - 装饰器驱动的工具注册和管理
- **容器管理** - 依赖注入和服务容器
- **配置管理** - 统一的配置加载和验证
- **通用工具类** - 设备管理、UI 操作、构建工具的基础类

## 安装

```bash
pip install harmonyos-mcp-common
```

## 使用示例

```python
from common.server.base import create_server, run_server
from common.tools.registry import mcp_tool

# 创建 MCP 服务器
mcp = create_server("my-server")

# 注册工具
@mcp_tool(category="general")
async def my_tool(param: str) -> dict:
    return {"result": param}

# 运行服务器
run_server(mcp)
```

## 相关项目

- [harmonyos-dev-mcp](https://pypi.org/project/harmonyos-dev-mcp/) - 完整的 HarmonyOS MCP 服务器

## License

Apache License 2.0
