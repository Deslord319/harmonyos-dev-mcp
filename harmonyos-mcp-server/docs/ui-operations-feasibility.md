# UI 操作工具可行性分析报告

**日期**: 2026-01-21  
**阶段**: 第二阶段 - 任务 2.1

---

## 📋 概述

本文档分析在 HarmonyOS MCP Server 中实现 UI 操作工具的可行性，包括技术方案、可用命令、实现难度和风险评估。

---

## ✅ 可行性结论

**结论**: **完全可行** ✅

HarmonyOS 提供了两套完整的 UI 操作命令：
1. **`hdc shell uitest uiInput`** - UITest 框架提供的 UI 输入命令
2. **`hdc shell uinput`** - 系统级输入模拟命令

这两套命令都可以通过 hdc 直接调用，无需修改应用代码，完全符合我们的零侵入原则。

---

## 🛠️ 技术方案

### 方案一：uitest uiInput（推荐）

**命令格式**: `hdc shell uitest uiInput <operation> <parameters>`

#### 支持的操作类型

| 操作类型 | 命令 | 参数说明 | 示例 |
|---------|------|---------|------|
| **点击** | `click` | `x y` | `hdc shell uitest uiInput click 100 100` |
| **双击** | `doubleClick` | `x y` | `hdc shell uitest uiInput doubleClick 100 100` |
| **长按** | `longClick` | `x y` | `hdc shell uitest uiInput longClick 100 100` |
| **快滑** | `fling` | `from_x from_y to_x to_y [speed] [stepLength]` | `hdc shell uitest uiInput fling 10 10 200 200 500` |
| **慢滑** | `swipe` | `from_x from_y to_x to_y [speed]` | `hdc shell uitest uiInput swipe 10 10 200 200 500` |
| **拖拽** | `drag` | `from_x from_y to_x to_y [speed]` | `hdc shell uitest uiInput drag 10 10 100 100 500` |
| **方向滑动** | `dircFling` | `direction [speed] [stepLength]` | `hdc shell uitest uiInput dircFling 0 500` |
| **文本输入** | `inputText` | `x y text` | `hdc shell uitest uiInput inputText 100 100 hello` |
| **按键事件** | `keyEvent` | `keyID [keyID2]` | `hdc shell uitest uiInput keyEvent Home` |

#### 方向滑动参数

- `0` - 左滑
- `1` - 右滑
- `2` - 上滑
- `3` - 下滑

#### 常用按键

- `Home` - 返回主页
- `Back` - 返回上一步
- `2072 2038` - 组合键粘贴操作

**优点**:
- ✅ 命令简洁易用
- ✅ 参数清晰明确
- ✅ 支持速度和步长控制
- ✅ 官方推荐的 UI 自动化方案

**缺点**:
- ⚠️ 需要坐标信息（可通过 UI 树获取）

---

### 方案二：uinput（备选）

**命令格式**: `hdc shell uinput <option> <command> <arg>...`

#### 支持的选项

```bash
-M --mouse      # 鼠标操作
-K --keyboard   # 键盘操作
-T --touch      # 触摸操作
-t --trackpad   # 触控板操作
-J --joystick   # 游戏手柄操作
-S --stylus     # 手写笔操作
```

#### 触摸操作示例

```bash
# 点击
hdc shell uinput -T -d 0 0 -m 0 0 0 800 -u 0 800

# 滑动（从(0,0)滑动到(0,800)）
hdc shell uinput -T -d 0 0 -m 0 0 0 800 -u 0 800
```

**优点**:
- ✅ 系统级命令，更底层
- ✅ 支持多种输入设备

**缺点**:
- ⚠️ 命令参数复杂
- ⚠️ 文档相对较少

---

## 📦 实现计划

### 需要实现的 MCP 工具

基于 uitest uiInput 方案，我们需要实现以下 MCP 工具：

#### 1. `click_element` - 点击元素
```python
@server.tool()
def click_element(device_id: str = None, x: int = None, y: int = None, 
                  element_id: str = None, double_click: bool = False) -> dict:
    """
    点击屏幕上的元素
    
    Args:
        device_id: 设备ID
        x: X坐标（与element_id二选一）
        y: Y坐标（与element_id二选一）
        element_id: 元素ID（自动从UI树获取坐标）
        double_click: 是否双击
    
    Returns:
        操作结果
    """
```

#### 2. `long_press_element` - 长按元素
```python
@server.tool()
def long_press_element(device_id: str = None, x: int = None, y: int = None,
                       element_id: str = None) -> dict:
    """长按屏幕上的元素"""
```

#### 3. `swipe` - 滑动
```python
@server.tool()
def swipe(device_id: str = None, from_x: int = None, from_y: int = None,
          to_x: int = None, to_y: int = None, speed: int = 600,
          direction: str = None) -> dict:
    """
    滑动操作
    
    Args:
        device_id: 设备ID
        from_x, from_y: 起点坐标（与direction二选一）
        to_x, to_y: 终点坐标（与direction二选一）
        speed: 滑动速度 (200-40000, 默认600)
        direction: 滑动方向 (left/right/up/down)
    
    Returns:
        操作结果
    """
```

#### 4. `input_text` - 输入文本
```python
@server.tool()
def input_text(device_id: str = None, x: int = None, y: int = None,
               element_id: str = None, text: str = None) -> dict:
    """
    在输入框中输入文本
    
    Args:
        device_id: 设备ID
        x, y: 输入框坐标（与element_id二选一）
        element_id: 输入框元素ID
        text: 要输入的文本
    
    Returns:
        操作结果
    """
```

#### 5. `press_key` - 按键操作
```python
@server.tool()
def press_key(device_id: str = None, key: str = None) -> dict:
    """
    模拟按键操作
    
    Args:
        device_id: 设备ID
        key: 按键名称 (Home/Back/Enter等)
    
    Returns:
        操作结果
    """
```

#### 6. `find_element` - 查找元素
```python
@server.tool()
def find_element(device_id: str = None, text: str = None, 
                 element_type: str = None, element_id: str = None) -> dict:
    """
    在UI树中查找元素
    
    Args:
        device_id: 设备ID
        text: 元素文本
        element_type: 元素类型
        element_id: 元素ID
    
    Returns:
        元素信息（包含坐标、bounds等）
    """
```

---

## 🔄 工作流程

### 典型使用场景

1. **获取 UI 树** → `get_ui_tree`
2. **查找目标元素** → `find_element`
3. **执行操作** → `click_element` / `input_text` / `swipe`

### 示例：点击登录按钮

```python
# 1. 获取UI树
ui_tree = get_ui_tree(bundle_name="com.example.app")

# 2. 查找登录按钮
login_button = find_element(text="登录")
# 返回: {"x": 500, "y": 1000, "bounds": "[450,950][550,1050]"}

# 3. 点击按钮
click_element(x=500, y=1000)
# 或者直接使用element_id
click_element(element_id="login_button_id")
```

---

## ⚠️ 技术挑战

### 1. 坐标计算
- **问题**: UI 树返回的 bounds 格式为 `[left,top][right,bottom]`
- **解决**: 计算中心点坐标 `x = (left + right) / 2, y = (top + bottom) / 2`

### 2. 元素定位
- **问题**: 需要在 UI 树中准确定位元素
- **解决**: 支持多种定位方式（text、type、id、bounds）

### 3. 等待机制
- **问题**: 操作后需要等待界面响应
- **解决**: 添加可选的 `wait_time` 参数

### 4. 错误处理
- **问题**: 元素不存在、坐标超出屏幕等
- **解决**: 完善的错误检查和提示

---

## 📊 实现难度评估

| 工具 | 难度 | 预计时间 | 优先级 |
|------|------|---------|--------|
| `click_element` | ⭐⭐ | 2小时 | 高 |
| `long_press_element` | ⭐ | 1小时 | 中 |
| `swipe` | ⭐⭐ | 2小时 | 高 |
| `input_text` | ⭐⭐ | 2小时 | 高 |
| `press_key` | ⭐ | 1小时 | 中 |
| `find_element` | ⭐⭐⭐ | 3小时 | 高 |

**总计**: 约 11 小时（1-2 个工作日）

---

## 🎯 下一步行动

1. ✅ **可行性分析完成** - 本文档
2. ⏭️ **创建 UI 操作工具模块** - `src/utils/ui_operations.py`
3. ⏭️ **实现基础操作** - click, swipe, input_text
4. ⏭️ **实现元素查找** - find_element
5. ⏭️ **添加 MCP 工具** - 在 main.py 中注册
6. ⏭️ **编写测试用例** - 验证所有操作
7. ⏭️ **更新文档** - 使用指南

---

## 📚 参考资料

- [HarmonyOS UITest 指南](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/uitest-guidelines)
- [awesome-hdc GitHub](https://github.com/codematrixer/awesome-hdc)
- [HarmonyOS uinput 文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/uinput)

---

**结论**: UI 操作工具完全可行，技术方案成熟，可以立即开始实现。

