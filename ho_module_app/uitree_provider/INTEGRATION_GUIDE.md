# UITree Provider 集成指南

本指南说明如何在现有的HarmonyOS应用中集成UITree Provider HAR模块。

## 步骤1: 添加依赖

在你的应用模块(如`entry`)的`oh-package.json5`中添加依赖:

```json5
{
  "dependencies": {
    "uitree_provider": "file:../uitree_provider"
  }
}
```

然后运行:

```bash
ohpm install
```

## 步骤2: 在EntryAbility中集成

编辑 `entry/src/main/ets/entryability/EntryAbility.ets`:

```typescript
import { UIAbility, Want } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { window } from '@kit.ArkUI';
import { UITreeService } from 'uitree_provider';

export default class EntryAbility extends UIAbility {
  private uiTreeService?: UITreeService;

  onCreate(want: Want, launchParam) {
    hilog.info(0x0000, 'testTag', '%{public}s', 'Ability onCreate');
    
    // 创建并启动UI树服务
    this.uiTreeService = new UITreeService({
      port: 8080,
      enabled: true,
      localOnly: true,
      token: undefined  // 可选: 设置访问令牌以增强安全性
    });
    
    // 启动服务
    this.uiTreeService.start()
      .then(() => {
        hilog.info(0x0000, 'testTag', 'UITreeService started successfully');
      })
      .catch((err) => {
        hilog.error(0x0000, 'testTag', 'Failed to start UITreeService: %{public}s', JSON.stringify(err));
      });
  }

  onDestroy() {
    hilog.info(0x0000, 'testTag', '%{public}s', 'Ability onDestroy');
    
    // 停止UI树服务
    if (this.uiTreeService) {
      this.uiTreeService.stop()
        .then(() => {
          hilog.info(0x0000, 'testTag', 'UITreeService stopped');
        })
        .catch((err) => {
          hilog.error(0x0000, 'testTag', 'Failed to stop UITreeService: %{public}s', JSON.stringify(err));
        });
    }
  }

  onWindowStageCreate(windowStage: window.WindowStage) {
    hilog.info(0x0000, 'testTag', '%{public}s', 'Ability onWindowStageCreate');

    windowStage.loadContent('pages/Index', (err) => {
      if (err.code) {
        hilog.error(0x0000, 'testTag', 'Failed to load the content. Cause: %{public}s', JSON.stringify(err) ?? '');
        return;
      }
      hilog.info(0x0000, 'testTag', 'Succeeded in loading the content.');
    });
  }
}
```

## 步骤3: 配置权限(如需要)

在 `entry/src/main/module.json5` 中添加必要的权限:

```json5
{
  "module": {
    "requestPermissions": [
      {
        "name": "ohos.permission.INTERNET"
      }
    ]
  }
}
```

## 步骤4: 构建HAR模块

在项目根目录运行:

```bash
# 构建HAR模块
hvigorw assembleHar --mode module -p module=uitree_provider

# 或者构建整个项目
hvigorw assembleHap
```

## 步骤5: 测试集成

### 方法1: 通过MCP Server测试

1. 确保应用已安装并运行在设备上
2. 使用MCP Server的`get_ui_tree`工具:

```python
# 在harmonyos-mcp-server中
python src/main.py
```

然后在Cursor中:

```
@harmonyos-tools 获取UI树
```

### 方法2: 直接调用测试

在你的页面代码中添加测试按钮:

```typescript
import { UITreeService } from 'uitree_provider';

@Entry
@Component
struct Index {
  private uiTreeService: UITreeService = new UITreeService();

  async testGetUITree() {
    await this.uiTreeService.start();
    const response = await this.uiTreeService.handleGetUITree();
    
    console.log('UI Tree Response:', JSON.stringify(response, null, 2));
    
    await this.uiTreeService.stop();
  }

  build() {
    Column() {
      Button('测试获取UI树')
        .onClick(() => {
          this.testGetUITree();
        })
    }
  }
}
```

## 步骤6: 通过hdc端口转发访问

如果你想从外部访问UI树服务:

```bash
# 设置端口转发
hdc fport tcp:8080 tcp:8080

# 使用curl测试
curl http://localhost:8080/get-ui-tree
```

## 故障排查

### 问题1: HAR模块找不到

**解决方案**:
- 确保`oh-package.json5`中的路径正确
- 运行`ohpm install`重新安装依赖
- 检查`build-profile.json5`中是否包含了uitree_provider模块

### 问题2: UITest Driver初始化失败

**解决方案**:
- 确保应用具有测试权限
- 检查设备是否支持UITest框架
- 查看日志输出获取详细错误信息

### 问题3: 无法获取UI树

**解决方案**:
- 确保服务已启动(`service.start()`)
- 检查是否有UI页面正在显示
- 查看hilog日志: `hdc hilog | grep UITree`

## 下一步

- 查看[README.md](README.md)了解详细API文档
- 查看[测试文件](src/test/UITreeProvider.test.ets)了解使用示例
- 集成到MCP Server实现AI辅助开发

