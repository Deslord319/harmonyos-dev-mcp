/**
 * UITree Provider HAR模块导出
 * 
 * 使用示例:
 * ```typescript
 * import { UITreeService, UITreeServiceConfig } from 'uitree_provider';
 * 
 * // 创建服务
 * const config: UITreeServiceConfig = {
 *   port: 8080,
 *   enabled: true,
 *   localOnly: true
 * };
 * 
 * const service = new UITreeService(config);
 * await service.start();
 * 
 * // 获取UI树
 * const response = await service.handleGetUITree();
 * console.log(JSON.stringify(response));
 * 
 * // 停止服务
 * await service.stop();
 * ```
 */

// 导出服务类
export { UITreeService } from './UITreeService';

// 导出收集器类(用于高级用法)
export { UITreeCollector } from './UITreeCollector';

// 导出数据类型
export {
  UITreeNode,
  UITreeResponse,
  UITreeServiceConfig,
  DEFAULT_CONFIG
} from './UITreeNode';

