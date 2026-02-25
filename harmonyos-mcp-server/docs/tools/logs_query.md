# logs_query - 统一日志查询工具

> 合并原有 `hilog_receive`、`logs_fetch`、`logs_save_snapshot`、`logs_analyze` 为单一工具

## 概述

`logs_query` 实现 **拉取 -> 解析 -> 过滤 -> 分析 -> 保存** 一体化流程，支持：

- 从设备实时获取日志
- 从历史落盘文件获取日志（自动切换）
- 分析本地日志文件
- 多种结构化分析
- 保存日志快照

---

## 参数说明

### 数据源参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `device_id` | string | null | 设备ID，为空时使用第一个设备 |
| `logs` | string[] | null | 直接传入日志行列表（优先级最高） |
| `input_file` | string | null | 本地日志文件路径 |
| `input_files` | string[] | null | 多个本地文件路径（合并分析） |

**优先级**: `logs` > `input_file`/`input_files` > 设备获取

### 过滤参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lines` | int | 100 | 最大返回行数（上限 50000） |
| `level` | string | null | 日志级别过滤：D/I/W/E/F |
| `tag` | string | null | Tag 过滤（模糊匹配） |
| `keyword` | string | null | 关键字过滤 |
| `pid` | int | null | 进程 ID 过滤 |
| `package_name` | string | null | 应用包名过滤（自动获取 PID） |

### 时间参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `start_time` | string | 开始时间（HH:MM:SS 或 YYYY-MM-DD HH:MM:SS） |
| `end_time` | string | 结束时间 |
| `seconds` | int | 最近 N 秒（与 start_time/end_time 互斥） |

> 当 `start_time` 超过 10 分钟前，自动切换到历史文件读取模式

### 分析参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `analysis_type` | string | "summary" | 分析类型（见下表） |
| `custom_regex` | string | null | 自定义正则（仅 custom 类型） |

**分析类型**:

| 类型 | 说明 |
|------|------|
| `summary` | 摘要统计：级别分布、Top Tags、时间范围 |
| `errors` | 错误分析：E/F 级别分组、异常类型识别 |
| `crashes` | 崩溃分析：Crash/ANR/Exception 识别 |
| `keywords` | 关键词提取：错误码、组件名、异常名 |
| `custom` | 自定义正则匹配 |

### 输出参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `save_path` | string | 保存路径（指定后写入文件） |

---

## 典型使用场景

### 1. 最简调用（实时日志 + 摘要）

```json
{"name": "logs_query", "arguments": {}}
```

### 2. 按级别过滤错误

```json
{
  "name": "logs_query",
  "arguments": {
    "level": "E",
    "lines": 500,
    "analysis_type": "errors"
  }
}
```

### 3. 按应用过滤

```json
{
  "name": "logs_query",
  "arguments": {
    "package_name": "com.example.myapp",
    "analysis_type": "crashes"
  }
}
```

### 4. 时间范围查询

```json
{
  "name": "logs_query",
  "arguments": {
    "start_time": "10:00:00",
    "end_time": "10:30:00",
    "level": "W"
  }
}
```

### 5. 最近 5 分钟日志

```json
{
  "name": "logs_query",
  "arguments": {
    "seconds": 300,
    "keyword": "crash"
  }
}
```

### 6. 分析本地文件

```json
{
  "name": "logs_query",
  "arguments": {
    "input_file": "/path/to/hilog.txt",
    "analysis_type": "keywords"
  }
}
```

### 7. 保存日志快照

```json
{
  "name": "logs_query",
  "arguments": {
    "package_name": "com.example.app",
    "lines": 2000,
    "save_path": "./crash_logs.txt"
  }
}
```

---

## 返回结构

```json
{
  "success": true,
  "device_id": "device_001",
  "source": "realtime_buffer",
  "logs": ["01-31 10:00:00.123 ..."],
  "total_lines": 100,
  "truncated": false,
  "filters_applied": {"level": "E"},
  "analysis_type": "summary",
  "analysis": {
    "total_lines": 100,
    "level_stats": {"E": 50, "W": 30, "I": 20},
    "top_tags": [{"tag": "MyApp", "count": 45}],
    "time_range": {"start": "...", "end": "..."}
  },
  "evidence_lines": ["..."],
  "total_entries_analyzed": 100
}
```

---

## 设计说明

### 为什么合并为单一工具？

1. **减少 LLM 决策负担** - 不需要判断该调用哪个日志工具
2. **统一流程** - 获取、过滤、分析在一次调用中完成
3. **参数复用** - 过滤条件对所有场景通用

### 时间自动切换逻辑

- `start_time` 在 10 分钟内 → 实时缓冲区（hilog -t）
- `start_time` 超过 10 分钟 → 历史落盘文件（需要 hilogtool 解密）
