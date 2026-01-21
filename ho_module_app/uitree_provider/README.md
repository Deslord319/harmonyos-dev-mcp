# UITree Provider HAR模块

这是一个HarmonyOS HAR库,用于提供应用UI树结构的查询服务。它使用UITest框架遍历UI控件树,并通过编程接口暴露UI树数据。

## 功能特性

- ✅ 使用UITest框架遍历UI控件树
- ✅ 提取控件的详细属性(类型、ID、文本、边界、状态等)
- ✅ 递归遍历所有子控件
- ✅ 返回JSON格式的UI树结构
- ✅ 可配置的服务选项
- ✅ 完整的TypeScript类型定义

## 安装

### 作为HAR模块集成

1. 在你的HarmonyOS项目的`oh-package.json5`中添加依赖:

```json5
{
  "dependencies": {
    "uitree_provider": "file:../uitree_provider"
  }
}
```

2. 运行依赖安装:

```bash
ohpm install
```

## 使用方法

### 基础用法

```typescript
import { UITreeService, UITreeServiceConfig } from 'uitree_provider';

// 1. 创建服务配置
const config: UITreeServiceConfig = {
  port: 8080,
  enabled: true,
  localOnly: true,
  token: undefined  // 可选的访问令牌
};

// 2. 创建服务实例
const service = new UITreeService(config);

// 3. 启动服务
await service.start();

// 4. 获取UI树
const response = await service.handleGetUITree();

if (response.success && response.tree) {
  console.log('UI Tree:', JSON.stringify(response.tree, null, 2));
} else {
  console.error('Failed to get UI tree:', response.error);
}

// 5. 停止服务
await service.stop();
```

### 在EntryAbility中集成

```typescript
import { UITreeService } from 'uitree_provider';
import { UIAbility } from '@kit.AbilityKit';

export default class EntryAbility extends UIAbility {
  private uiTreeService?: UITreeService;

  onCreate(want, launchParam) {
    // 创建并启动UI树服务
    this.uiTreeService = new UITreeService({
      port: 8080,
      enabled: true,
      localOnly: true
    });
    
    this.uiTreeService.start().catch(err => {
      console.error('Failed to start UITreeService:', err);
    });
  }

  onDestroy() {
    // 停止服务
    this.uiTreeService?.stop();
  }
}
```

### 高级用法 - 直接使用Collector

```typescript
import { UITreeCollector } from 'uitree_provider';

const collector = new UITreeCollector();

// 初始化
await collector.init();

// 收集UI树
const tree = await collector.collectUITree();

// 使用完毕后销毁
collector.destroy();
```

## API参考

### UITreeService

主服务类,提供UI树查询服务。

#### 构造函数

```typescript
constructor(config?: Partial<UITreeServiceConfig>)
```

#### 方法

- `start(): Promise<void>` - 启动服务
- `stop(): Promise<void>` - 停止服务
- `handleGetUITree(): Promise<UITreeResponse>` - 获取UI树
- `getStatus()` - 获取服务状态
- `updateConfig(config)` - 更新配置

### UITreeNode

UI树节点数据结构。

```typescript
interface UITreeNode {
  type: string;           // 控件类型
  id: string;             // 控件ID
  text: string;           // 控件文本
  bounds: {               // 控件边界
    x: number;
    y: number;
    width: number;
    height: number;
  };
  enabled: boolean;       // 是否可用
  visible: boolean;       // 是否可见
  clickable: boolean;     // 是否可点击
  focusable: boolean;     // 是否可聚焦
  checked: boolean;       // 是否已选中
  scrollable: boolean;    // 是否可滚动
  attributes: Record<string, string>;  // 其他属性
  children: UITreeNode[]; // 子节点
}
```

## 测试

### 单元测试

```typescript
import { UITreeCollector } from 'uitree_provider';
import { describe, it, expect } from '@ohos/hypium';

describe('UITreeCollector', () => {
  it('should initialize successfully', async () => {
    const collector = new UITreeCollector();
    await collector.init();
    expect(collector).not.toBeNull();
    collector.destroy();
  });
});
```

## 注意事项

1. **权限要求**: 使用UITest框架需要应用具有测试权限
2. **性能考虑**: UI树遍历可能耗时,建议在后台线程执行
3. **安全性**: 如果通过网络暴露,务必配置token验证
4. **兼容性**: 需要HarmonyOS SDK 6.0.2+

## 许可证

MIT

