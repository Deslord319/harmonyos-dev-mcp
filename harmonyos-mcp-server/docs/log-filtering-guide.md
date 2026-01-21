# HarmonyOS日志过滤指南

**版本**: 1.0  
**更新时间**: 2026-01-21  
**适用工具**: get_logs MCP工具

---

## 📖 概述

`get_logs` 工具支持多种日志过滤方式，可以帮助你快速定位特定应用、进程或标签的日志信息。

## 🎯 支持的过滤参数

### 1. bundle_name - 按应用包名过滤

**用途**: 只显示指定应用的日志

**示例**:
```python
get_logs(bundle_name="com.example.myapp")
```

**在Augment中使用**:
```
获取com.example.myapp应用的日志
```

**适用场景**:
- 调试特定应用
- 查看应用崩溃日志
- 监控应用运行状态

### 2. tag - 按日志标签过滤

**用途**: 只显示特定标签的日志

**常用标签**:
- `Ace` - ArkUI框架日志
- `JSAPP` - JavaScript应用日志
- `AbilityManager` - Ability管理日志
- `WindowManager` - 窗口管理日志
- `RenderService` - 渲染服务日志

**示例**:
```python
get_logs(tag="Ace")
```

**在Augment中使用**:
```
获取标签为Ace的日志
```

**适用场景**:
- 调试UI渲染问题
- 查看框架层日志
- 分析系统服务日志

### 3. pid - 按进程ID过滤

**用途**: 只显示特定进程的日志

**示例**:
```python
get_logs(pid=12345)
```

**在Augment中使用**:
```
获取进程12345的日志
```

**适用场景**:
- 调试多进程应用
- 跟踪特定进程的行为
- 分析进程间通信

### 4. lines - 限制日志行数

**用途**: 控制返回的日志行数

**默认值**: 100行

**示例**:
```python
get_logs(lines=50)  # 获取最后50行
```

**在Augment中使用**:
```
获取最近50行日志
```

---

## 🔧 组合过滤

你可以组合多个过滤参数以获得更精确的结果。

### 示例1: 包名 + 标签

```python
get_logs(bundle_name="com.example.myapp", tag="Ace")
```

**在Augment中**:
```
获取com.example.myapp应用中标签为Ace的日志
```

### 示例2: 包名 + 行数

```python
get_logs(bundle_name="com.example.myapp", lines=50)
```

**在Augment中**:
```
获取com.example.myapp应用的最近50行日志
```

### 示例3: 标签 + 进程ID

```python
get_logs(tag="Ace", pid=12345)
```

**在Augment中**:
```
获取进程12345中标签为Ace的日志
```

---

## 💡 实用技巧

### 1. 查找应用崩溃日志

```
获取com.example.myapp应用的最近200行日志
```

然后在返回的日志中搜索 "FATAL" 或 "ERROR" 关键词。

### 2. 监控UI渲染性能

```
获取标签为Ace的最近100行日志
```

查看是否有性能警告或错误。

### 3. 调试特定功能

先运行应用的特定功能，然后立即获取日志：

```
获取com.example.myapp应用的最近30行日志
```

### 4. 对比不同时间点的日志

```
# 第一次获取
获取com.example.myapp的最近50行日志

# 执行某个操作后再次获取
获取com.example.myapp的最近50行日志
```

---

## 🔍 hilog命令参考

`get_logs` 工具底层使用 `hilog` 命令，以下是相关参数：

### 基本命令

```bash
# 获取所有日志
hdc shell hilog

# 按标签过滤
hdc shell hilog -T Ace

# 按进程ID过滤
hdc shell hilog -P 12345

# 按包名过滤（通过grep）
hdc shell "hilog | grep com.example.myapp"
```

### 其他有用的hilog参数

```bash
# 清空日志缓存
hdc shell hilog -r

# 设置日志级别
hdc shell hilog -L D  # Debug级别

# 彩色输出
hdc shell hilog -v color
```

---

## 📊 日志级别说明

HarmonyOS日志分为以下级别：

| 级别 | 代码 | 说明 |
|------|------|------|
| DEBUG | D | 调试信息 |
| INFO | I | 一般信息 |
| WARN | W | 警告信息 |
| ERROR | E | 错误信息 |
| FATAL | F | 致命错误 |

---

## 🚀 最佳实践

1. **从宽到窄**: 先获取较多日志，然后逐步添加过滤条件
2. **使用包名过滤**: 对于应用调试，优先使用 `bundle_name` 参数
3. **合理设置行数**: 根据需要调整 `lines` 参数，避免返回过多无用日志
4. **结合标签**: 对于框架层问题，使用 `tag` 参数定位问题
5. **保存重要日志**: 对于重要的错误日志，建议保存到文件中

---

## 📝 常见问题

### Q: 如何知道应用的包名？

A: 可以通过以下方式获取：
- 查看应用的 `app.json5` 或 `module.json5` 文件中的 `bundleName` 字段
- 使用命令: `hdc shell bm dump -a` 列出所有已安装应用

### Q: 如何找到进程ID？

A: 使用以下命令：
```bash
hdc shell ps | grep <应用包名>
```

### Q: 日志太多怎么办？

A: 
1. 使用更精确的过滤条件（如 `bundle_name` + `tag`）
2. 减少 `lines` 参数的值
3. 在获取日志前清空日志缓存: `hdc shell hilog -r`

---

## 🔗 相关文档

- [Augment集成指南](augment-integration.md)
- [HarmonyOS官方文档 - hilog](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/hilog-guidelines-V5)

