# HarmonyOS hidumper UI组件树获取指南

**版本**: 1.0  
**更新时间**: 2026-01-21  
**适用环境**: HarmonyOS 6.0+

## 📖 概述

`hidumper` 是HarmonyOS系统提供的诊断工具，可以用于获取系统和应用的各种运行时信息，包括UI组件树。相比UITest框架，hidumper是系统级工具，无需修改应用代码即可使用。

## 🎯 核心优势

1. **无代码侵入** - 不需要在应用中集成任何代码
2. **系统级工具** - 无API使用限制
3. **信息完整** - 提供完整的组件层级和属性信息
4. **易于自动化** - 纯命令行操作，易于集成到CI/CD

## 🔧 基本用法

### 1. 列出所有系统服务

```bash
hdc shell "hidumper -ls"
```

**关键服务**:
- `WindowManagerService` - 窗口管理服务（用于获取UI组件树）
- `AbilityManagerService` - Ability管理服务
- `RenderService` - 渲染服务

### 2. 获取所有窗口信息

```bash
hdc shell "hidumper -s WindowManagerService -a '-a'"
```

**输出示例**:
```
WindowName           DisplayId PID     WinId Type Mode Flag Orient FirstFrame IsVisible ...
myapplication0       0         62173   142   1    102  0    -1     1          true      ...
settings0            0         10389   87    1    102  0    -1     0          true      ...
```

**关键字段**:
- `WindowName`: 窗口名称（通常是应用名或模块名）
- `PID`: 进程ID
- `WinId`: 窗口ID（用于后续查询）
- `bundleName`: 应用包名（在详细输出中）

### 3. 获取指定窗口的UI组件树

```bash
hdc shell "hidumper -s WindowManagerService -a '-w <窗口ID> -default -c'"
```

**参数说明**:
- `-s WindowManagerService`: 指定服务名称
- `-a`: 传递参数给服务
- `-w <窗口ID>`: 指定窗口ID
- `-default`: 使用默认输出格式
- `-c`: 包含组件树信息

**示例**:
```bash
hdc shell "hidumper -s WindowManagerService -a '-w 142 -default -c'"
```

## 📊 输出格式解析

### 组件树结构

输出采用缩进表示层级关系：

```
|-> Stack childSize:2
    | ID: 39
    | Depth: 5
    | FrameRect: RectT (0.00, 0.00) - [2091.00 x 70.30]
  |-> Row childSize:1
      | ID: 41
      | Depth: 6
    |-> Button childSize:1
        | ID: 45
        | Depth: 7
      |-> Image childSize:0
          | ID: 46
          | Depth: 8
```

### 关键属性

#### 基本信息
- `ID`: 组件唯一标识符
- `Depth`: 组件在树中的深度
- `childSize`: 子组件数量
- `InstanceId`: 实例ID
- `AccessibilityId`: 无障碍ID

#### 布局信息
- `FrameRect`: 组件的框架矩形 `RectT (x, y) - [width x height]`
- `PaintRect`: 绘制矩形（实际渲染区域）
- `top`, `left`: 相对于父组件的位置
- `ParentLayoutConstraint`: 父组件的布局约束
- `ContentConstraint`: 内容约束

#### 可见性
- `IsOnMaintree`: 是否在主树上（1=是，0=否）
- `Visible`: 可见性状态（0=可见，1=隐藏，2=消失）
- `IsVisible`: 是否可见（true/false）

#### 组件特定属性

**Button组件**:
```
| Type: NORMAL
| CreateWithLabel: false
| BorderRadius: radiusTopLeft: [4.00vp]...
| StateEffect: true
```

**Image组件**:
```
| url: resource:///125829923.svg
| SrcType: 6
| objectFit: COVER
| fillColor_value: #E5000000_cs0
| rawImageSize: [24.00 x 24.00]
```

**Text组件**:
```
| content: "Hello World"
| fontSize: 16.00fp
| fontColor: #FF000000
```

### 状态变量

组件的状态变量信息：

```
| decorator:"@State" propertyName:"message" value:"Hello"
| state Variable id: -123
| inRenderingElementId: -1
| dependentElementIds: {"mode":"Compatible Mode",...}
```

## 🔍 实用查询技巧

### 1. 查找特定应用的窗口

```bash
# 获取所有窗口，然后grep过滤
hdc shell "hidumper -s WindowManagerService -a '-a'" | grep "myapplication"
```

### 2. 保存组件树到文件

```bash
# Windows PowerShell
hdc shell "hidumper -s WindowManagerService -a '-w 142 -default -c'" > uitree.txt

# Linux/Mac
hdc shell "hidumper -s WindowManagerService -a '-w 142 -default -c'" > uitree.txt
```

### 3. 获取特定组件信息

```bash
# 获取所有Button组件
hdc shell "hidumper -s WindowManagerService -a '-w 142 -default -c'" | grep "Button"
```

## 🐍 Python自动化示例

```python
import subprocess
import re

def get_window_list():
    """获取所有窗口列表"""
    cmd = ['hdc', 'shell', 'hidumper -s WindowManagerService -a \'-a\'']
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def find_window_id(bundle_name):
    """根据包名查找窗口ID"""
    output = get_window_list()
    # 解析输出，查找匹配的窗口ID
    for line in output.split('\n'):
        if bundle_name in line:
            match = re.search(r'(\d+)\s+1\s+102', line)
            if match:
                return int(match.group(1))
    return None

def get_ui_tree(window_id):
    """获取指定窗口的UI组件树"""
    cmd = [
        'hdc', 'shell',
        f'hidumper -s WindowManagerService -a \'-w {window_id} -default -c\''
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

# 使用示例
window_id = find_window_id('com.demo.myapplication')
if window_id:
    ui_tree = get_ui_tree(window_id)
    print(f"Found window ID: {window_id}")
    print(ui_tree)
```

## 📝 注意事项

1. **权限要求**: 需要设备已连接且开启开发者模式
2. **窗口状态**: 只能获取当前可见窗口的组件树
3. **输出编码**: 注意处理中文字符的编码问题
4. **性能影响**: 频繁调用可能影响应用性能
5. **版本兼容**: 不同HarmonyOS版本输出格式可能略有差异

## 🔗 参考资料

1. [HarmonyOS官方文档 - hidumper](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hidumper)
2. [状态变量组件定位工具实践](https://developer.huawei.com/consumer/cn/forum/topic/0204147212943605039)
3. [帧率和丢帧分析实践](https://www.cnblogs.com/strengthen/p/18517566)

## 📞 问题反馈

如有问题或建议，请提交Issue或Pull Request。

