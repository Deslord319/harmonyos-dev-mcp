# query_package - 统一包查询工具

## 概述

`query_package` 实现统一的包查询功能，支持：

- 列出设备上所有已安装的应用包
- 获取指定包的所有 Abilities
- 获取指定包的主入口 Ability
- 获取指定包的权限列表

---

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `device_id` | string | null | 设备ID，为空时使用第一个设备 |
| `bundle_name` | string | null | 应用包名（指定后查询该包详情） |
| `keyword` | string | null | 关键字过滤（仅 list 模式生效） |
| `info_type` | string | "list" | 查询类型：list/abilities/main_ability/permissions |

### info_type 说明

| 值 | 说明 |
|----|------|
| `list` | 列出所有包（默认） |
| `abilities` | 获取指定包的所有 Abilities |
| `main_ability` | 获取指定包的主入口 Ability |
| `permissions` | 获取指定包的权限列表 |

---

## 使用示例

### 列出所有已安装的应用

```python
query_package()
```

返回：
```json
{
  "success": true,
  "device_id": "xxx",
  "packages": [
    {"bundle_name": "com.example.app1", "label": "应用1"},
    {"bundle_name": "com.example.app2", "label": "应用2"}
  ],
  "total": 2
}
```

### 根据关键字过滤包

```python
query_package(keyword="camera")
```

### 获取指定包的所有 Abilities

```python
query_package(bundle_name="com.example.myapp", info_type="abilities")
```

### 获取指定包的主 Ability

```python
query_package(bundle_name="com.example.myapp", info_type="main_ability")
```

### 获取指定包的权限列表

```python
query_package(bundle_name="com.example.myapp", info_type="permissions")
```

---

## 返回结果结构

### list 模式

```json
{
  "success": true,
  "device_id": "xxx",
  "packages": [
    {
      "bundle_name": "com.example.app",
      "label": "应用名称",
      "version": "1.0.0"
    }
  ],
  "total": 1
}
```

### abilities 模式

```json
{
  "success": true,
  "bundle_name": "com.example.app",
  "abilities": [
    {
      "name": "EntryAbility",
      "type": "page",
      "uri": "ability://com.example.app/entry"
    }
  ]
}
```

### main_ability 模式

```json
{
  "success": true,
  "bundle_name": "com.example.app",
  "main_ability": {
    "name": "EntryAbility",
    "type": "page",
    "uri": "ability://com.example.app/entry"
  }
}
```

### permissions 模式

```json
{
  "success": true,
  "bundle_name": "com.example.app",
  "permissions": [
    "ohos.permission.INTERNET",
    "ohos.permission.CAMERA"
  ]
}
```
