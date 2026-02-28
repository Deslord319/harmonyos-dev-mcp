# logs_query - 统一日志查询工具

> 合并原有 `hilog_receive`、`logs_fetch`、`logs_save_snapshot`、`logs_analyze` 为单一工具

## 概述

`logs_query` 实现 **拉取 -> 解析 -> 过滤 -> 分析 -> 保存** 一体化流程，支持：

- 从设备实时获取日志
- 从历史落盘文件获取日志（自动切换）
- 分析本地日志文件
- 多种结构化分析
- 保存日志快照
- 诊断统计信息
- 崩溃日志查询（根据包名+时间自动匹配）

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
| `tag` | string | null | Tag 过滤（匹配解析后的 tag 字段） |
| `tag_search` | string | null | Tag 搜索（在原始行中搜索，不依赖解析） |
| `keyword` | string | null | 关键字过滤（在原始行中搜索） |
| `domain` | string | null | hilog domain 过滤（支持 0x0006 或 C00006 格式） |
| `pid` | int | null | 进程 ID 过滤 |
| `package_name` | string | null | 应用包名过滤（自动获取 PID） |

### 时间参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `start_time` | string | 开始时间（HH:MM:SS 或 YYYY-MM-DD HH:MM:SS） |
| `end_time` | string | 结束时间 |
| `seconds` | int | 最近 N 秒（与 start_time/end_time 互斥） |
| `time_expr` | string | 自然语言时间表达式（如"最近10分钟"、"昨天下午"） |

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
| `custom` | 自定义正则匹配 |

### 输出参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `save_path` | string | 保存路径（指定后写入文件） |
| `include_diagnostics` | bool | 返回诊断统计信息（默认 false） |
| `include_crash` | bool | 是否包含崩溃日志（默认 false） |

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
    "lines": 500
  }
}
```

### 3. 按应用过滤

```json
{
  "name": "logs_query",
  "arguments": {
    "package_name": "com.example.myapp"
  }
}
```

### 4. 搜索特定 TAG（推荐使用 tag_search）

```json
{
  "name": "logs_query",
  "arguments": {
    "tag_search": "LogAuditService",
    "lines": 100
  }
}
```

### 5. 按 domain 过滤

```json
{
  "name": "logs_query",
  "arguments": {
    "domain": "0x0006",
    "lines": 100
  }
}
```

### 6. 查询日志 + 崩溃日志

```json
{
  "name": "logs_query",
  "arguments": {
    "package_name": "com.example.app",
    "start_time": "19:00:00",
    "end_time": "19:30:00",
    "include_crash": true
  }
}
```

### 7. 获取诊断信息

```json
{
  "name": "logs_query",
  "arguments": {
    "package_name": "com.example.app",
    "include_diagnostics": true
  }
}
```

### 8. 时间范围查询

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

### 9. 自然语言时间表达式

```json
{
  "name": "logs_query",
  "arguments": {
    "time_expr": "最近10分钟",
    "level": "E"
  }
}
```

### 10. 分析本地文件

```json
{
  "name": "logs_query",
  "arguments": {
    "input_file": "/path/to/hilog.txt"
  }
}
```

---

## 返回结构

### 基本返回

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
    "parsed_lines": 95,
    "level_stats": {"E": 50, "W": 30, "I": 20},
    "top_tags": [{"tag": "MyApp", "count": 45}],
    "time_range": {"start": "...", "end": "..."}
  },
  "total_entries_analyzed": 100
}
```

### 包含崩溃日志（include_crash=true）

```json
{
  "success": true,
  "logs": [...],
  "crash_info": {
    "type": "cppcrash",
    "file": "cppcrash-com.example.app-20020146-20251223192956865.log",
    "timestamp": "2025-12-23T19:29:56.865000",
    "module_name": "com.example.app",
    "reason": "Signal:SIGSEGV(SEGV_MAPERR)@0x0000000100000058",
    "summary": "原因: Signal:SIGSEGV(SEGV_MAPERR)@0x0000000100000058 | 位置: QSocketNotifier::setEnabled(bool) (libQt5Core.so)",
    "fault_thread": {
      "tid": 42195,
      "name": ".example.app",
      "backtrace": [
        {"pc": "00000000004fa408", "lib": "libQt5Core.so", "func": "QSocketNotifier::setEnabled(bool)", "offset": "24"},
        {"pc": "0000000000511fe0", "lib": "libQt5Core.so", "func": "QEventDispatcherUNIXPrivate::markPendingSocketNotifiers()", "offset": "960"}
      ]
    }
  }
}
```

### 包含诊断信息（include_diagnostics=true）

```json
{
  "success": true,
  "logs": [...],
  "diagnostics": {
    "total_scanned": 10000,
    "parse_success": 8500,
    "parse_failed": 1500,
    "filter_stats": {
      "level_filtered": 100,
      "tag_filtered": 50,
      "tag_search_filtered": 0,
      "keyword_filtered": 200,
      "domain_filtered": 0,
      "pid_filtered": 0,
      "time_filtered": 0,
      "package_filtered": 0,
      "noise_filtered": 300,
      "passed": 100
    }
  }
}
```

---

## 崩溃日志匹配逻辑

当 `include_crash=true` 时，自动根据以下条件匹配崩溃日志：

1. **路径**: `/data/log/faultlog/faultlogger/`
2. **文件名格式**: `{type}-{package}-{uid}-{timestamp}.log`
   - `type`: cppcrash / jscrash / appfreeze
   - `package`: 应用包名
   - `timestamp`: 崩溃时间
3. **匹配条件**:
   - 包名匹配
   - 时间范围匹配（如果指定了 start_time/end_time）

---

## tag vs tag_search

| 参数 | 说明 | 适用场景 |
|------|------|----------|
| `tag` | 匹配解析后的 entry.tag 字段 | 日志格式标准，解析成功 |
| `tag_search` | 在原始行中搜索 TAG | 日志格式不标准，解析失败 |

**推荐**：优先使用 `tag_search`，因为它不依赖解析结果。

---

## 噪音过滤

自动过滤以下系统噪音日志：

| 模式 | 说明 |
|------|------|
| `/sys/power/last_sr` | 电源状态文件读取 |
| `XCollie.*last_sr` | XCollie 相关 |
| `Failed to read file: /sys/` | 系统文件读取失败 |
| `logd.*prune` | 日志守护进程裁剪 |
| `healthd` | 健康守护进程 |
| `chatty.*identical` | 重复日志压缩提示 |
| `ServiceManager: Waiting for service` | 服务等待 |

---

## 设计说明

### 为什么合并为单一工具？

1. **减少 LLM 决策负担** - 不需要判断该调用哪个日志工具
2. **统一流程** - 获取、过滤、分析在一次调用中完成
3. **参数复用** - 过滤条件对所有场景通用

### 时间自动切换逻辑

- `start_time` 在 10 分钟内 → 实时缓冲区（hilog -t）
- `start_time` 超过 10 分钟 → 历史落盘文件（需要 hilogtool 解密）

### keyword 搜索优化

keyword 现在搜索整个原始行（raw_line），确保不会因为解析失败而遗漏日志。

### domain 格式

支持多种格式：
- `0x0006` → 转换为 `C00006`
- `C00006` → 直接使用
- `0006` → 转换为 `C00006`
