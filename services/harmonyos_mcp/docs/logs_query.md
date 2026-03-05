# logs_query

统一日志查询工具，覆盖：
- 实时日志抓取
- 历史日志抓取（按时间自动切换）
- 本地文件分析
- 过滤、统计、诊断、崩溃信息聚合
- 可选快照保存

## 参数

### 数据源参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `device_id` | string | `null` | 设备 ID |
| `logs` | string[] | `null` | 直接传入日志行，优先级最高 |
| `input_file` | string | `null` | 单个本地日志文件 |
| `input_files` | string[] | `null` | 多个本地日志文件 |

优先级：`logs` > `input_file/input_files` > 设备读取。

### 过滤参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `lines` | int | `100` | 返回最大行数 |
| `level` | string | `null` | `D/I/W/E/F` |
| `tag` | string | `null` | 解析后 tag 精确过滤 |
| `tag_search` | string | `null` | 原始行搜索 tag 关键字 |
| `keyword` | string | `null` | 原始行关键字 |
| `domain` | string | `null` | hilog domain |
| `pid` | int | `null` | 进程 ID |
| `package_name` | string | `null` | 包名（自动查 PID） |

### 时间参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `start_time` | string | `HH:MM:SS` 或 `YYYY-MM-DD HH:MM:SS` |
| `end_time` | string | 同上 |
| `seconds` | int | 最近 N 秒 |
| `time_expr` | string | 自然语言时间表达（例如“最近10分钟”） |

说明：当查询窗口超过实时缓冲覆盖范围时，自动切换历史日志读取。

### 分析与输出参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `analysis_type` | string | `summary` | `summary/custom` |
| `custom_regex` | string | `null` | `analysis_type=custom` 时生效 |
| `save_path` | string | `null` | 结果落盘路径 |
| `include_diagnostics` | bool | `false` | 返回过滤统计信息 |
| `include_crash` | bool | `false` | 聚合 crash 信息 |

## 返回结构

外层统一 MCP，业务结果在 `structuredContent`。

成功：

```json
{
  "tool": "logs_query",
  "ok": true,
  "result": {
    "device_id": "3QC0124C11000711",
    "source": "realtime_buffer",
    "logs": ["03-05 15:41:03.543 ..."],
    "total_lines": 1,
    "truncated": false,
    "filters_applied": {"level": "E"},
    "analysis_type": "summary",
    "analysis": {"level_stats": {"E": 1}},
    "total_entries_analyzed": 1
  },
  "error": null
}
```

失败：

```json
{
  "tool": "logs_query",
  "ok": false,
  "result": {
    "logs": [],
    "total_lines": 0,
    "truncated": false
  },
  "error": {
    "code": "APP_NOT_RUNNING",
    "detail": "app not running or pid not found: com.example.app"
  }
}
```

`error` 仅保留 `code/detail`。

## 典型调用

### 最近错误日志

```json
{
  "name": "logs_query",
  "arguments": {
    "level": "E",
    "lines": 300
  }
}
```

### 指定包最近 10 分钟

```json
{
  "name": "logs_query",
  "arguments": {
    "package_name": "com.example.myapplication",
    "time_expr": "最近10分钟",
    "include_diagnostics": true
  }
}
```

### 保存快照

```json
{
  "name": "logs_query",
  "arguments": {
    "package_name": "com.example.myapplication",
    "lines": 500,
    "save_path": "C:/Users/mu/Desktop/hilog_snapshot.txt"
  }
}
```

