# HarmonyOS MCP Server - 构建系统阻塞问题修复总结

## 问题描述

在使用 `build_app` MCP 工具时，遇到了严重的阻塞问题：
- ✅ 构建本身成功完成（1-5秒）
- ✅ HAP 文件正确生成
- ✅ Python 脚本直接调用工作正常
- ❌ **MCP 工具调用无限期挂起**，需要手动取消

## 根本原因

### 问题分析

当使用 `subprocess.run()` 配合 `capture_output=True` 或 `PIPE` 时：

1. Python 等待子进程退出
2. **同时等待所有持有 stdout/stderr 文件描述符的进程关闭**
3. hvigor 启动的 daemon 进程或子进程持有这些文件描述符
4. 即使主 hvigor 进程退出，daemon 进程仍然持有文件描述符
5. 导致 `subprocess.run()` 无限期阻塞
6. Python 函数执行完毕并到达 `return`，但进程仍被阻塞
7. **MCP 服务器无法发送响应给客户端**

### 关键发现

通过文件日志调试发现：
- `build_app` 函数**完全执行**到 `return` 语句
- 构建**成功完成**
- 但 **`return` 之后响应无法发送**
- 问题在于 subprocess 文件描述符管理

## 解决方案

### 核心修改

在 `hvigor_wrapper.py` 的 `_execute_command()` 方法中：

```python
result = subprocess.run(
    cmd,
    cwd=str(self.project_path),
    stdout=subprocess.DEVNULL,  # 丢弃输出，避免管道阻塞
    stderr=subprocess.DEVNULL,  # 丢弃错误输出
    stdin=subprocess.DEVNULL,   # 不接受输入
    timeout=timeout,
    env=env,
    close_fds=True  # 关闭所有文件描述符，防止子进程继承
)
```

### 关键点

1. **`subprocess.DEVNULL`**: 完全丢弃输出，避免管道阻塞
2. **`close_fds=True`**: 确保子进程不继承任何文件描述符
3. **移除所有 `--daemon` 和 `--no-daemon` 参数**: 不再需要

### 错误信息获取

虽然使用 DEVNULL 丢弃了输出，但构建失败时仍能获取错误信息：

在 `main.py` 的 `build_app()` 函数中：
```python
if not result['success']:
    try:
        log_file = Path(project_path) / '.hvigor' / 'outputs' / 'build-logs' / 'build.log'
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                error_lines = [line.strip() for line in lines if 'ERROR' in line or 'Error Message' in line]
                if error_lines:
                    response['error'] = '\n'.join(error_lines[-3:])
    except Exception as e:
        debug_log(f"读取日志文件失败: {e}")
```

## 修改的文件

### 1. `harmonyos-mcp-server/src/utils/hvigor_wrapper.py`

**修改的方法**：
- `_execute_command()` - 使用 DEVNULL 和 close_fds
- `clean()` - 移除 `--no-daemon` 参数
- `build_har()` - 已移除 `--daemon` 参数
- `build_hap()` - 已移除 `--daemon` 参数
- `build_app()` - 已移除 `--daemon` 参数

**影响范围**：所有调用 hvigor 的操作都受益于此修复

### 2. `harmonyos-mcp-server/src/main.py`

**修改的工具**：
- `build_app()` - 添加了从日志文件读取错误信息的逻辑

## 测试结果

### ✅ 成功场景
```json
{
  "success": true,
  "hap_path": "D:\\...\\entry-default-unsigned.hap",
  "message": "构建成功，耗时: 1.31秒"
}
```

### ❌ 失败场景（SDK 配置错误）
```json
{
  "success": false,
  "hap_path": null,
  "message": "构建失败，耗时: 0.96秒",
  "error": "00303217 Configuration Error\nInvalid value of 'DEVECO_SDK_HOME'..."
}
```

### ❌ 失败场景（TypeScript 编译错误）
```json
{
  "success": false,
  "hap_path": null,
  "message": "构建失败，耗时: 2.45秒",
  "error": "Cannot find name 'nonExistentFunction'. At File: .../Index.ets:20:23\nCOMPILE RESULT:FAIL {ERROR:4 WARN:1}"
}
```

## 性能表现

- **增量构建**: 1-2 秒
- **完整构建**: 根据项目大小
- **失败检测**: < 1 秒
- **无阻塞**: ✅ 立即返回

## 未来扩展

所有使用 `_execute_command()` 的方法都已修复：
- ✅ `clean()` - 清理构建产物
- ✅ `build_har()` - 构建 HAR 包
- ✅ `build_hap()` - 构建 HAP 包
- ✅ `build_app()` - 构建 APP 包

如果未来添加新的 MCP 工具使用这些方法，它们将自动受益于此修复。

## 总结

这个修复解决了一个非常典型的 subprocess 管道阻塞问题，关键在于：
1. 理解 subprocess 的文件描述符继承机制
2. 使用 DEVNULL 避免管道阻塞
3. 使用 close_fds 防止子进程继承文件描述符
4. 通过日志文件获取错误信息，而不是依赖 stdout/stderr

修复日期：2026-01-21

