# HarmonyOS AI编程开发方案调研 - 第三阶段

## 调研时间
2026年1月19日

## 1. HarmonyOS开发工具链详解

### 1.1 hdc（HarmonyOS Device Connector）工具

**基本功能**：
- 设备连接和管理
- 应用安装/卸载
- 文件传输
- 日志收集
- Shell命令执行

**核心命令集**：

| 命令类别 | 命令 | 功能描述 | 示例 |
|---------|------|---------|------|
| **版本和帮助** | `hdc -v` | 查看hdc版本 | `hdc -v` |
| | `hdc -h` | 查看帮助信息 | `hdc -h` |
| **设备管理** | `hdc list targets` | 列出所有连接设备 | `hdc list targets` |
| | `hdc target -t <device_id>` | 指定目标设备 | `hdc target -t emulator-5554` |
| | `hdc shell "bm get --udid"` | 获取设备UDID | `hdc shell "bm get --udid"` |
| **应用管理** | `hdc install <hap_path>` | 安装应用 | `hdc install app.hap` |
| | `hdc uninstall <bundle_name>` | 卸载应用 | `hdc uninstall com.example.app` |
| | `hdc shell "bm list -a"` | 列出已安装应用 | `hdc shell "bm list -a"` |
| **文件操作** | `hdc file send <local> <remote>` | 推送文件到设备 | `hdc file send ./test.txt /data/` |
| | `hdc file recv <remote> <local>` | 拉取文件到本地 | `hdc file recv /data/log.txt ./` |
| **日志收集** | `hdc hilog` | 实时收集日志 | `hdc hilog > log.txt` |
| | `hdc shell "hilog -r"` | 清理日志缓存 | `hdc shell "hilog -r"` |
| | `hdc shell "hilog -v color -T Ace"` | 过滤日志输出 | 按标签和级别过滤 |
| **Shell执行** | `hdc shell <command>` | 执行Shell命令 | `hdc shell "ls /data"` |
| | `hdc shell` | 进入交互Shell | `hdc shell` |
| **截图** | `hdc shell "snapshot_display -f <path>"` | 设备截图 | 获取当前屏幕截图 |

**MCP工具集成方案**：
```python
# hdc命令包装器示例
class HdcWrapper:
    def list_devices(self) -> List[str]:
        """列出所有设备"""
        result = subprocess.run(['hdc', 'list', 'targets'], 
                              capture_output=True, text=True)
        return result.stdout.strip().split('\n')
    
    def install_app(self, device_id: str, hap_path: str) -> bool:
        """安装应用"""
        cmd = ['hdc', '-t', device_id, 'install', hap_path]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    
    def execute_shell(self, device_id: str, command: str) -> str:
        """执行Shell命令"""
        cmd = ['hdc', '-t', device_id, 'shell', command]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    
    def get_logs(self, device_id: str, lines: int = 100) -> str:
        """获取应用日志"""
        cmd = ['hdc', '-t', device_id, 'hilog']
        result = subprocess.run(cmd, capture_output=True, text=True)
        return '\n'.join(result.stdout.split('\n')[-lines:])
```

### 1.2 hvigor构建系统

**基本特性**：
- 基于任务的构建系统
- 支持命令行构建（hvigorw）
- 支持自定义构建任务
- 支持多产品、多模块构建

**核心构建命令**：

| 命令 | 功能 | 参数 | 示例 |
|------|------|------|------|
| `hvigorw clean` | 清理构建产物 | `--no-daemon` | `hvigorw clean --no-daemon` |
| `hvigorw assembleHap` | 构建HAP包 | `-p product=default -p buildMode=debug` | `hvigorw assembleHap --mode module -p product=default -p buildMode=debug --no-daemon` |
| `hvigorw assembleApp` | 构建APP包 | `-p product=default -p buildMode=debug` | `hvigorw assembleApp --mode project -p product=default -p buildMode=debug --no-daemon` |
| `hvigorw assembleHar` | 构建HAR库 | `-p product=default` | `hvigorw assembleHar --mode module -p product=default --no-daemon` |
| `hvigorw assembleHsp` | 构建HSP库 | `-p product=default` | `hvigorw assembleHsp --mode module -p product=default --no-daemon` |

**构建模式**：
- **debug**：调试模式，包含调试信息，文件较大
- **release**：发布模式，优化代码，文件较小

**MCP工具集成方案**：
```python
# hvigor命令包装器示例
class HvigorWrapper:
    def __init__(self, project_path: str):
        self.project_path = project_path
    
    def build_hap(self, build_mode: str = "debug", 
                  product: str = "default") -> dict:
        """构建HAP包"""
        cmd = [
            'hvigorw', 'assembleHap',
            '--mode', 'module',
            '-p', f'product={product}',
            '-p', f'buildMode={build_mode}',
            '--no-daemon'
        ]
        result = subprocess.run(cmd, cwd=self.project_path,
                              capture_output=True, text=True)
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr
        }
    
    def clean(self) -> bool:
        """清理构建产物"""
        cmd = ['hvigorw', 'clean', '--no-daemon']
        result = subprocess.run(cmd, cwd=self.project_path,
                              capture_output=True)
        return result.returncode == 0
```

**自动签名集成**：
- 通过`build-profile.json5`配置签名信息
- 支持自定义签名文件路径
- 支持多环境签名配置

### 1.3 UITest框架

**基本功能**：
- UI界面查找和定位
- UI交互操作（点击、滑动、输入等）
- 外设行为模拟（键盘、鼠标等）
- 控件属性获取

**核心API类**：

| 类 | 功能 | 说明 |
|----|------|------|
| **Driver** | 入口类 | 提供控件查找、截图、按键注入等能力 |
| **Component** | 控件对象 | 代表UI界面上的指定控件 |
| **On** | 匹配器 | 用于描述目标控件特征（文本、ID、类型等） |

**控件查找方式**：

```typescript
// 导入测试依赖
import { Driver, Component, ON, On } from '@kit.TestKit';

// 创建Driver实例
let driver: Driver = Driver.create();

// 方式1：按类型查找
let button: Component = await driver.findComponent(ON.type('Button'));

// 方式2：按文本查找
let component: Component = await driver.findComponent(ON.text('提交'));

// 方式3：按ID查找
let input: Component = await driver.findComponent(ON.id('input_name'));

// 方式4：多属性组合查找
let on: On = ON.text('123').within(ON.type('Scroll'));
let items: Array<Component> = await driver.findComponents(on);

// 方式5：相对位置查找
let within: On = ON.type('Button').isBefore(ON.type('Text'));
let comp: Component = await driver.findComponent(within);
```

**控件操作**：

| 操作 | 方法 | 说明 |
|------|------|------|
| **点击** | `click()` | 单击控件 |
| **长按** | `longClick()` | 长按控件 |
| **输入文本** | `inputText(text)` | 在输入框输入文本 |
| **滑动** | `scroll(direction)` | 在控件内滑动 |
| **双指操作** | `pinchOut(scale)` | 双指放大 |
| **获取属性** | `getAttr(attr)` | 获取控件属性 |
| **截图** | `screenshot()` | 对控件截图 |

**DOM树拉取的可行性分析**：

| 方法 | 可行性 | 实现难度 | 说明 |
|------|--------|---------|------|
| **UITest API遍历** | ✅ 高 | 中 | 通过Driver和Component API遍历控件树 |
| **hdc dump窗口** | ✅ 中 | 中 | 通过hdc shell执行dump命令获取窗口信息 |
| **ArkUI Inspector** | ⚠️ 低 | 高 | 需要解析DevEco Studio的输出格式 |
| **直接导出API** | ❌ 无 | - | HarmonyOS未提供直接的DOM导出API |

**推荐方案**：UITest API + hdc dump结合

---

## 2. DOM树拉取的详细技术方案

### 2.1 实现流程

**步骤1：连接设备并获取应用信息**
```python
# 连接设备
hdc_wrapper.connect_device(device_id)

# 获取应用Bundle Name
bundle_name = "com.example.app"

# 启动应用（如果未运行）
hdc_wrapper.execute_shell(device_id, f"am start -n {bundle_name}/.MainActivity")
```

**步骤2：通过UITest API遍历控件树**
```typescript
// HarmonyOS应用端代码（需要在应用中集成）
import { Driver, Component, ON } from '@kit.TestKit';

export async function getUITree(): Promise<any> {
  let driver: Driver = Driver.create();
  
  // 获取根控件
  let root: Component = await driver.findComponent(ON.type('Page'));
  
  // 递归遍历控件树
  return await traverseComponent(root, driver);
}

async function traverseComponent(component: Component, 
                                driver: Driver): Promise<any> {
  const tree = {
    type: await component.getAttr('type'),
    id: await component.getAttr('id'),
    text: await component.getAttr('text'),
    bounds: await component.getAttr('bounds'),
    enabled: await component.getAttr('enabled'),
    visible: await component.getAttr('visible'),
    children: []
  };
  
  // 获取子控件
  try {
    const children = await component.getChildren();
    for (const child of children) {
      tree.children.push(await traverseComponent(child, driver));
    }
  } catch (e) {
    // 没有子控件
  }
  
  return tree;
}
```

**步骤3：通过hdc dump获取窗口信息（备选方案）**
```bash
# 获取窗口信息
hdc shell "dumpsys window windows"

# 获取应用进程信息
hdc shell "ps -ef | grep com.example.app"

# 获取应用的Activity栈
hdc shell "dumpsys activity activities"
```

**步骤4：在MCP工具中集成DOM树拉取**
```python
@server.tool()
def get_ui_tree(bundle_name: str, device_id: str = None) -> dict:
    """
    获取应用的UI树结构
    
    Args:
        bundle_name: 应用包名
        device_id: 设备ID（可选）
    
    Returns:
        DOM树的JSON表示
    """
    try:
        # 连接设备
        if device_id is None:
            device_id = hdc_wrapper.list_devices()[0]
        
        # 启动应用（如果未运行）
        hdc_wrapper.execute_shell(device_id, 
            f"am start -n {bundle_name}/.MainActivity")
        
        # 等待应用启动
        time.sleep(2)
        
        # 调用应用端的getUITree方法（需要通过RPC或其他方式）
        # 这里需要在应用中集成UITest API并暴露接口
        
        # 备选：通过hdc dump获取窗口信息
        dump_output = hdc_wrapper.execute_shell(device_id, 
            "dumpsys window windows")
        
        # 解析dump输出并构建DOM树
        dom_tree = parse_window_dump(dump_output)
        
        return {
            'success': True,
            'tree': dom_tree,
            'timestamp': time.time()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

### 2.2 DOM树数据结构

**标准JSON格式**：
```json
{
  "type": "Page",
  "id": "root",
  "text": "",
  "bounds": {
    "x": 0,
    "y": 0,
    "width": 1080,
    "height": 2340
  },
  "enabled": true,
  "visible": true,
  "attributes": {
    "accessibilityId": "page_root",
    "className": "com.example.app.MainActivity"
  },
  "children": [
    {
      "type": "Stack",
      "id": "stack_1",
      "text": "",
      "bounds": {
        "x": 0,
        "y": 0,
        "width": 1080,
        "height": 2340
      },
      "children": [
        {
          "type": "Button",
          "id": "btn_submit",
          "text": "提交",
          "bounds": {
            "x": 100,
            "y": 200,
            "width": 200,
            "height": 50
          },
          "enabled": true,
          "visible": true,
          "attributes": {
            "clickable": true,
            "focusable": true
          },
          "children": []
        },
        {
          "type": "TextInput",
          "id": "input_name",
          "text": "",
          "bounds": {
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 40
          },
          "enabled": true,
          "visible": true,
          "attributes": {
            "inputType": "text",
            "hint": "请输入名字"
          },
          "children": []
        }
      ]
    }
  ]
}
```

### 2.3 可行性评估

**优势**：
- ✅ UITest框架是官方标准API，可靠性高
- ✅ 支持完整的控件属性获取
- ✅ 支持控件查找和定位
- ✅ 可以实时获取当前页面的UI状态

**限制**：
- ⚠️ 需要在应用中集成UITest测试框架
- ⚠️ 某些私有属性可能无法获取
- ⚠️ 需要应用暴露接口或通过RPC通信
- ⚠️ 无法获取应用外的系统UI信息

**改进方案**：
1. 在应用中集成UITest框架，并暴露HTTP接口
2. MCP工具通过HTTP调用应用接口获取DOM树
3. 结合hdc dump补充获取窗口级别的信息

---

## 3. HarmonyOS开发者账号和签名自动化

### 3.1 签名流程

**手动签名流程**：
1. 在DevEco Studio中登录华为账号
2. 关联AppGallery Connect应用
3. 自动生成签名证书
4. 配置到build-profile.json5

**自动化签名方案**：

| 方案 | 实现难度 | 安全性 | 可维护性 |
|------|---------|--------|---------|
| **OAuth流程** | 高 | 高 | 高 |
| **存储凭证** | 低 | 低 | 中 |
| **DevEco CLI** | 中 | 中 | 中 |
| **手动登录一次** | 低 | 高 | 高 |

**推荐方案**：手动登录一次 + 缓存签名证书

```python
class SigningManager:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.build_profile = os.path.join(project_path, 'build-profile.json5')
    
    def configure_signing(self, cert_path: str, 
                         cert_password: str = None) -> bool:
        """
        配置应用签名
        
        Args:
            cert_path: 签名证书路径
            cert_password: 证书密码（可选）
        
        Returns:
            是否配置成功
        """
        try:
            # 读取build-profile.json5
            with open(self.build_profile, 'r') as f:
                config = json5.load(f)
            
            # 配置签名信息
            if 'signingConfigs' not in config:
                config['signingConfigs'] = {}
            
            config['signingConfigs']['default'] = {
                'storeFile': cert_path,
                'storePassword': cert_password or '',
                'keyAlias': 'key0',
                'keyPassword': cert_password or ''
            }
            
            # 写回配置
            with open(self.build_profile, 'w') as f:
                json5.dump(config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"签名配置失败: {e}")
            return False
    
    def get_signing_status(self) -> dict:
        """获取当前签名配置状态"""
        try:
            with open(self.build_profile, 'r') as f:
                config = json5.load(f)
            
            signing_config = config.get('signingConfigs', {}).get('default', {})
            return {
                'configured': bool(signing_config),
                'cert_path': signing_config.get('storeFile', ''),
                'key_alias': signing_config.get('keyAlias', '')
            }
        except Exception as e:
            return {'configured': False, 'error': str(e)}
```

### 3.2 AGC API集成

**AppGallery Connect API**：
- 应用信息查询
- 证书管理
- 应用发布

**MCP工具集成**：
```python
class AGCClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
    
    def get_access_token(self) -> str:
        """获取AGC访问令牌"""
        # 实现OAuth流程
        pass
    
    def get_app_info(self, app_id: str) -> dict:
        """获取应用信息"""
        # 调用AGC API
        pass
    
    def get_certificates(self, app_id: str) -> list:
        """获取应用的签名证书列表"""
        # 调用AGC API
        pass
```

---

## 4. 与DevEco Studio的集成

### 4.1 DevEco CLI工具

**可用命令**：
- `deveco build`：编译应用
- `deveco run`：运行应用
- `deveco sign`：签名应用
- `deveco install`：安装应用

**集成方式**：
```python
class DevEcoWrapper:
    def build(self, project_path: str, build_mode: str = "debug") -> dict:
        """通过DevEco CLI构建应用"""
        cmd = ['deveco', 'build', '-m', build_mode]
        result = subprocess.run(cmd, cwd=project_path,
                              capture_output=True, text=True)
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr
        }
```

### 4.2 IDE插件集成

**可能的集成方式**：
1. 通过DevEco Studio的扩展API
2. 通过命令行工具调用
3. 通过文件系统监听

**当前限制**：
- DevEco Studio不支持Cursor、Cline等第三方AI插件
- 官方CodeGenie功能有限
- 需要通过MCP工具间接集成

---

## 5. 完整的MCP工具架构

### 5.1 工具清单

**必需工具（优先级高）**：
1. `get_ui_tree` - 获取应用UI树
2. `find_element` - 查找UI元素
3. `click_element` - 点击UI元素
4. `input_text` - 输入文本
5. `build_app` - 构建应用
6. `install_app` - 安装应用
7. `run_app` - 运行应用
8. `get_logs` - 获取应用日志

**高级工具（优先级中）**：
1. `list_devices` - 列出设备
2. `get_device_info` - 获取设备信息
3. `configure_signing` - 配置签名
4. `get_signing_status` - 获取签名状态
5. `screenshot` - 设备截图
6. `execute_shell` - 执行Shell命令

**扩展工具（优先级低）**：
1. `analyze_performance` - 性能分析
2. `get_app_info` - 获取应用信息
3. `manage_agc` - AGC应用管理

### 5.2 MCP工具的Tool定义示例

```python
from fastmcp import FastMCP

server = FastMCP("harmonyos-tools")

@server.tool()
def get_ui_tree(bundle_name: str, device_id: str = None) -> dict:
    """获取HarmonyOS应用的UI树结构"""
    # 实现逻辑
    pass

@server.tool()
def find_element(bundle_name: str, selector: dict, 
                device_id: str = None) -> list:
    """查找UI元素"""
    # selector格式: {"type": "Button", "text": "提交"}
    pass

@server.tool()
def click_element(bundle_name: str, element_id: str, 
                 device_id: str = None) -> bool:
    """点击UI元素"""
    pass

@server.tool()
def input_text(bundle_name: str, element_id: str, 
              text: str, device_id: str = None) -> bool:
    """在输入框输入文本"""
    pass

@server.tool()
def build_app(project_path: str, build_mode: str = "debug") -> dict:
    """构建HarmonyOS应用"""
    pass

@server.tool()
def install_app(device_id: str, hap_path: str) -> bool:
    """安装应用到设备"""
    pass

@server.tool()
def run_app(device_id: str, bundle_name: str) -> bool:
    """运行应用"""
    pass

@server.tool()
def get_logs(device_id: str, bundle_name: str, 
            lines: int = 100) -> str:
    """获取应用日志"""
    pass
```

---

## 6. 技术可行性总结

### 6.1 DOM树拉取

**可行性**：✅ 高

**实现方案**：
- 通过UITest框架API遍历控件树
- 结合hdc dump获取窗口信息
- 在应用中暴露HTTP接口

**预期效果**：
- 可以获取完整的UI树结构
- 支持控件属性查询
- 支持实时更新

**时间估算**：1-2周

### 6.2 自动化构建和签名

**可行性**：✅ 高

**实现方案**：
- 使用hvigor命令行工具
- 配置build-profile.json5
- 缓存签名证书

**预期效果**：
- 完全自动化构建流程
- 支持多环境签名
- 支持CI/CD集成

**时间估算**：1周

### 6.3 应用安装和运行

**可行性**：✅ 高

**实现方案**：
- 使用hdc install命令
- 使用am start启动应用
- 监听应用进程

**预期效果**：
- 自动化应用部署
- 支持多设备管理
- 支持应用生命周期管理

**时间估算**：3-5天

### 6.4 日志收集

**可行性**：✅ 高

**实现方案**：
- 使用hdc hilog命令
- 支持日志过滤和搜索
- 实时日志流

**预期效果**：
- 完整的应用日志收集
- 支持日志分析
- 支持错误诊断

**时间估算**：3-5天

---

## 7. 关键技术决策

### 7.1 DOM树获取方案选择

**方案对比**：

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **UITest API** | 官方标准、可靠性高 | 需要应用集成 | ⭐⭐⭐⭐⭐ |
| **hdc dump** | 无需应用修改 | 信息不完整 | ⭐⭐⭐ |
| **ArkUI Inspector** | 可视化工具 | 难以自动化 | ⭐⭐ |

**最终选择**：UITest API + hdc dump结合

### 7.2 MCP工具实现语言

**选择**：Python + FastMCP

**理由**：
- FastMCP是官方推荐框架
- 易于集成系统命令
- 开发效率高
- 社区支持好

### 7.3 传输方式

**选择**：STDIO（本地）+ HTTP（远程）

**理由**：
- STDIO用于本地开发，无需额外配置
- HTTP支持远程部署和团队协作
- 支持OAuth认证

---

## 8. 后续调研需求

### 8.1 需要进一步调研的内容

1. **UITest框架的完整API**
   - 控件属性获取的完整列表
   - 支持的匹配器类型
   - 性能和限制

2. **hdc工具的高级用法**
   - 远程调试功能
   - 性能分析工具集成
   - 多设备管理

3. **hvigor插件开发**
   - 自定义构建任务
   - 构建流程定制
   - 性能优化

4. **AGC API文档**
   - 完整的API列表
   - 认证方式
   - 错误处理

5. **DevEco Studio扩展**
   - 插件开发API
   - 扩展点
   - 集成方式

### 8.2 需要进行的实验

1. **DOM树拉取实验**
   - 创建测试应用
   - 集成UITest框架
   - 验证DOM树完整性

2. **自动化构建实验**
   - 测试hvigor命令行构建
   - 验证签名配置
   - 测试多环境构建

3. **MCP工具原型开发**
   - 实现基础工具集
   - 测试与Cursor集成
   - 性能测试

