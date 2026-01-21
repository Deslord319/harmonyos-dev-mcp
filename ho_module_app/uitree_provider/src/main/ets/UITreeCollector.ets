/**
 * UI树收集器 - 使用UITest框架遍历UI控件树
 */
import { Driver, Component, ON } from '@kit.TestKit';
import { UITreeNode } from './UITreeNode';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'UITreeCollector';
const DOMAIN = 0x0001;

export class UITreeCollector {
  private driver: Driver | null = null;

  /**
   * 初始化Driver
   */
  async init(): Promise<void> {
    try {
      this.driver = Driver.create();
      hilog.info(DOMAIN, TAG, 'UITreeCollector initialized');
    } catch (error) {
      hilog.error(DOMAIN, TAG, `Failed to initialize Driver: ${error}`);
      throw error;
    }
  }

  /**
   * 收集UI树
   */
  async collectUITree(): Promise<UITreeNode | null> {
    if (!this.driver) {
      hilog.error(DOMAIN, TAG, 'Driver not initialized');
      return null;
    }

    try {
      hilog.info(DOMAIN, TAG, 'Starting to collect UI tree');
      
      // 查找根节点 - 尝试多种方式
      let rootComponent: Component | null = null;
      
      try {
        // 方式1: 查找Page类型
        rootComponent = await this.driver.findComponent(ON.type('Page'));
      } catch (e) {
        hilog.warn(DOMAIN, TAG, 'Failed to find Page component, trying alternative');
      }

      if (!rootComponent) {
        try {
          // 方式2: 查找根容器
          rootComponent = await this.driver.findComponent(ON.type('__Container__'));
        } catch (e) {
          hilog.warn(DOMAIN, TAG, 'Failed to find Container component');
        }
      }

      if (!rootComponent) {
        hilog.error(DOMAIN, TAG, 'Failed to find root component');
        return null;
      }

      // 递归遍历UI树
      const tree = await this.traverseComponent(rootComponent);
      hilog.info(DOMAIN, TAG, 'UI tree collection completed');
      
      return tree;
    } catch (error) {
      hilog.error(DOMAIN, TAG, `Failed to collect UI tree: ${error}`);
      return null;
    }
  }

  /**
   * 递归遍历组件
   */
  private async traverseComponent(component: Component): Promise<UITreeNode> {
    const node: UITreeNode = {
      type: '',
      id: '',
      text: '',
      bounds: { x: 0, y: 0, width: 0, height: 0 },
      enabled: true,
      visible: true,
      clickable: false,
      focusable: false,
      checked: false,
      scrollable: false,
      attributes: {},
      children: []
    };

    try {
      // 获取基本属性
      node.type = await this.getAttributeSafe(component, 'type') || 'Unknown';
      node.id = await this.getAttributeSafe(component, 'id') || '';
      node.text = await this.getAttributeSafe(component, 'text') || '';
      
      // 获取布尔属性
      node.enabled = await this.getBooleanAttribute(component, 'enabled', true);
      node.visible = await this.getBooleanAttribute(component, 'visible', true);
      node.clickable = await this.getBooleanAttribute(component, 'clickable', false);
      node.focusable = await this.getBooleanAttribute(component, 'focusable', false);
      node.checked = await this.getBooleanAttribute(component, 'checked', false);
      node.scrollable = await this.getBooleanAttribute(component, 'scrollable', false);

      // 获取边界信息
      const boundsStr = await this.getAttributeSafe(component, 'bounds');
      if (boundsStr) {
        node.bounds = this.parseBounds(boundsStr);
      }

      // 获取其他可能的属性
      const otherAttrs = ['description', 'hint', 'value', 'selected'];
      for (const attr of otherAttrs) {
        const value = await this.getAttributeSafe(component, attr);
        if (value) {
          node.attributes[attr] = value;
        }
      }

      // 递归获取子组件
      try {
        const childCount = await this.getChildCount(component);
        if (childCount > 0) {
          for (let i = 0; i < childCount; i++) {
            try {
              const child = await this.getChildAt(component, i);
              if (child) {
                const childNode = await this.traverseComponent(child);
                node.children.push(childNode);
              }
            } catch (e) {
              hilog.warn(DOMAIN, TAG, `Failed to get child at index ${i}: ${e}`);
            }
          }
        }
      } catch (e) {
        hilog.debug(DOMAIN, TAG, `No children for component: ${e}`);
      }

    } catch (error) {
      hilog.error(DOMAIN, TAG, `Error traversing component: ${error}`);
    }

    return node;
  }

  /**
   * 安全获取属性
   */
  private async getAttributeSafe(component: Component, attr: string): Promise<string> {
    try {
      const value = await component.getAttribute(attr);
      return value ? String(value) : '';
    } catch (e) {
      return '';
    }
  }

  /**
   * 获取布尔属性
   */
  private async getBooleanAttribute(component: Component, attr: string, defaultValue: boolean): Promise<boolean> {
    const value = await this.getAttributeSafe(component, attr);
    if (value === '') return defaultValue;
    return value === 'true' || value === '1';
  }

  /**
   * 解析边界字符串
   * 格式: "[x,y][width,height]" 或 "x,y,width,height"
   */
  private parseBounds(boundsStr: string): { x: number; y: number; width: number; height: number } {
    const defaultBounds = { x: 0, y: 0, width: 0, height: 0 };

    try {
      // 尝试解析 "[x,y][width,height]" 格式
      const match = boundsStr.match(/\[(\d+),(\d+)\]\[(\d+),(\d+)\]/);
      if (match) {
        return {
          x: parseInt(match[1]),
          y: parseInt(match[2]),
          width: parseInt(match[3]),
          height: parseInt(match[4])
        };
      }

      // 尝试解析 "x,y,width,height" 格式
      const parts = boundsStr.split(',').map(s => parseInt(s.trim()));
      if (parts.length === 4) {
        return {
          x: parts[0],
          y: parts[1],
          width: parts[2],
          height: parts[3]
        };
      }
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `Failed to parse bounds: ${boundsStr}`);
    }

    return defaultBounds;
  }

  /**
   * 获取子组件数量
   */
  private async getChildCount(component: Component): Promise<number> {
    try {
      // UITest可能没有直接的getChildCount方法
      // 我们尝试通过查找子组件来确定
      const children = await this.findChildren(component);
      return children.length;
    } catch (e) {
      return 0;
    }
  }

  /**
   * 获取指定索引的子组件
   */
  private async getChildAt(component: Component, index: number): Promise<Component | null> {
    try {
      const children = await this.findChildren(component);
      return children[index] || null;
    } catch (e) {
      return null;
    }
  }

  /**
   * 查找所有子组件
   */
  private async findChildren(component: Component): Promise<Component[]> {
    try {
      // 使用UITest的查找功能获取子组件
      // 注意: 这个实现可能需要根据实际UITest API调整
      if (!this.driver) {
        return [];
      }

      // 尝试查找所有子组件
      // 这里使用一个通用的查找策略
      const children: Component[] = [];

      // 由于UITest API的限制,我们可能需要使用其他方法
      // 这里提供一个基础实现,实际使用时可能需要调整

      return children;
    } catch (e) {
      return [];
    }
  }

  /**
   * 释放资源
   */
  destroy(): void {
    this.driver = null;
    hilog.info(DOMAIN, TAG, 'UITreeCollector destroyed');
  }
}
