# `logs_query`

Unified log query tool with two query modes:

- `mode="errors"`: default mode for effective error and suspicious-log extraction
- `mode="markers"`: marker lookup for confirming whether a business action completed

## Parameters

### Sources
| Parameter | Type | Default | Notes |
|---|---|---|---|
| `device_id` | string | `null` | Target device ID |
| `logs` | string[] | `null` | Inline raw log lines; highest priority |
| `input_file` | string | `null` | Single local log file |
| `input_files` | string[] | `null` | Multiple local log files |

Priority: `logs` > `input_file/input_files` > device capture

### Query parameters
| Parameter | Type | Default | Notes |
|---|---|---|---|
| `mode` | string | `errors` | Supported values: `errors`, `markers` |
| `lines` | int | `100` | Maximum returned result items |
| `level` | string | `null` | Minimum level filter: `D/I/W/E/F` |
| `tag` | string | `null` | Structured tag filter |
| `tag_search` | string | `null` | Raw-line tag text filter |
| `keyword` | string | `null` | Raw-line keyword filter |
| `domain` | string | `null` | hilog domain filter |
| `pid` | int | `null` | Strict process ID filter |
| `package_name` | string | `null` | Business package relevance filter; does not collapse to a single PID by default |
| `marker_keywords` | string[] | `null` | Extra business markers when `mode="markers"` |
| `realtime_wait_ms` | int | `1000` | Short realtime sampling window |
| `context_lines` | int | `0` | Context lines before and after each matched item |

### Time parameters
| Parameter | Type | Notes |
|---|---|---|
| `start_time` | string | `HH:MM:SS` or `YYYY-MM-DD HH:MM:SS` |
| `end_time` | string | Same as above |
| `seconds` | int | Last N seconds |
| `time_expr` | string | Natural-language time expression |
| `fallback_to_historical` | bool | Defaults to `false`; when realtime misses, optionally query historical logs |

Notes:
- Realtime logs are used first by default.
- Explicit `start_time/end_time` prefers historical logs.
- Historical fallback is disabled by default because of cost.

## Result shape

Successful calls return `structuredContent.result` with fields like:

```json
{
  "query_mode": "markers",
  "device_id": "3QC0124C11000711",
  "source_attempted": ["realtime_buffer"],
  "source_used": "realtime_buffer",
  "fallback_triggered": false,
  "matched": true,
  "match_count": 3,
  "group_count": 1,
  "filters_applied": {
    "mode": "markers",
    "package_name": "com.huawei.securitytool",
    "marker_keywords": ["saveResult", "resCode is 0"]
  },
  "items": [
    {
      "type": "marker_success",
      "timestamp": "2026-03-19T15:20:11.130000",
      "level": "I",
      "tag": "A03D00/com.huawei.securitytool/JSAPP",
      "pid": 40683,
      "message": "[picker] getDocumentPickerSaveResult saveResult: errorcode is = 0",
      "raw_line": "03-19 15:20:11.130 ...",
      "matched_keywords": ["saveResult", "resCode is 0"],
      "match_strength": "strong",
      "score": 120,
      "context_before": [],
      "context_after": []
    }
  ]
}
```

Semantics:
- `errors` mode with no match: no effective errors or suspicious items found
- `markers` mode with no match: target markers were not found; this does not prove the business action failed
- `match_count`: raw marker hits before grouping
- `group_count`: returned grouped marker items in `items`

## Recommended usage

### Recent errors
```json
{
  "name": "logs_query",
  "arguments": {
    "mode": "errors",
    "level": "E",
    "lines": 200
  }
}
```

### Confirm an export/save action
```json
{
  "name": "logs_query",
  "arguments": {
    "mode": "markers",
    "package_name": "com.huawei.securitytool",
    "marker_keywords": ["saveResult", "resCode is 0", "selecturi"],
    "seconds": 30,
    "realtime_wait_ms": 1500,
    "context_lines": 1
  }
}
```

### Retry with historical logs only when needed
```json
{
  "name": "logs_query",
  "arguments": {
    "mode": "markers",
    "package_name": "com.huawei.securitytool",
    "marker_keywords": ["saveResult", "resCode is 0"],
    "seconds": 120,
    "fallback_to_historical": true
  }
}
```

## Notes

- `logs_query` returns filtered analysis items, not a full raw log stream.
- `package_name` is a relevance hint, not a default single-PID restriction.
- `mode="markers"` works best with explicit business markers.
- Wide markers such as `success` or `completed` are intentionally treated as weak signals.
