# query_package - 统一包查询工具

> 合并原有 `list_packages`、`get_package_abilities`、`get_main_ability` 为单一工具

## 概述

`query_package` 实现统一的包查询入口，遵循 CQRS 原则（查询与执行分离），支持：

- 列出设备上所有已安装的应用包
- 根据关键字搜索包名
- 获取指定包的所有 Abilities
- 获取指定包的主入口 Ability

---

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `device_id` | string | null | 设备ID，为空时使用第一个设备 |
| `bundle_name` | string | null | 应用包名（指定后查询该包详情） |
| `keyword` | string | null | 关键字过滤（仅 list 模式生效） |
| `info_type` | string | "list" | 查询类型（见下表） |

### info_type 查询类型

| 类型 | 说明 | 是否需要 bundle_name |
|------|------|---------------------|
| `list` | 列出所有包（默认） | 否 |
| `abilities` | 获取指定包的所有 Abilities | 是 |
| `main_ability` | 获取指定包的主入口 Ability | 是 |

> **智能切换**：当指定 `bundle_name` 但 `info_type` 为 "list" 时，自动切换到 "abilities" 模式

---

## 典型使用场景

### 1. 列出所有已安装的包

```json
{"name": "query_package", "arguments": {}}
```

### 2. 搜索包含关键字的包

```json
{
  "name": "query_package",
  "arguments": {
    "keyword": "settings"
  }
}
```

### 3. 获取指定包的所有 Abilities

```json
{
  "name": "query_package",
  "arguments": {
    "bundle_name": "com.huawei.hmos.settings",
    "info_type": "abilities"
  }
}
```

或简写（自动切换）：

```json
{
  "name": "query_package",
  "arguments": {
    "bundle_name": "com.huawei.hmos.settings"
  }
}
```

### 4. 获取指定包的主 Ability

```json
{
  "name": "query_package",
  "arguments": {
    "bundle_name": "com.huawei.hmos.settings",
    "info_type": "main_ability"
  }
}
```

---

## 返回结构

### list 模式

```json
{
  "success": true,
  "device_id": "device_001",
  "info_type": "list",
  "packages": [
    "com.huawei.hmos.settings",
    "com.huawei.hmos.contacts",
    "com.example.myapp"
  ],
  "count": 3,
  "keyword": ""
}
```

### abilities 模式

```json
{
  "success": true,
  "device_id": "device_001",
  "info_type": "abilities",
  "bundle_name": "com.huawei.hmos.settings",
  "abilities": [
    {
      "name": "MainAbility",
      "type": "page",
      "module": "entry",
      "visible": true,
      "hasHomeAction": true
    }
  ],
  "modules": [{"name": "entry"}],
  "main_ability": {
    "name": "MainAbility",
    "module": "entry"
  },
  "ability_count": 1
}
```

### main_ability 模式

```json
{
  "success": true,
  "device_id": "device_001",
  "info_type": "main_ability",
  "bundle_name": "com.huawei.hmos.settings",
  "ability_name": "MainAbility",
  "module_name": "entry"
}
```

---

## 底层实现

### 获取包列表

```bash
hdc shell bm dump -a
```

### 获取包详情

```bash
hdc shell bm dump -n <bundle_name>
```

输出 JSON 格式，解析 `hapModuleInfos` → `abilityInfos` 获取 Abilities 信息。

---

## 设计说明

### 为什么合并为单一工具？

1. **减少工具数量** - 从 3 个工具精简为 1 个
2. **统一入口** - 所有包查询操作使用同一工具
3. **CQRS 原则** - 查询（query_package）与执行（run_app）分离
4. **智能默认** - 指定 bundle_name 自动切换到详情模式

### 与 run_app 的关系

| 工具 | 职责 |
|------|------|
| `query_package` | 查询包信息（只读） |
| `run_app` | 启动应用（执行操作，内置 auto_detect） |

用户无需先调用 `query_package` 获取主 Ability 再调用 `run_app`，因为 `run_app` 已内置自动检测功能。
