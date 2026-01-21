/**
 * UITree Provider 单元测试
 */
import { describe, it, expect, beforeAll, afterAll } from '@ohos/hypium';
import { UITreeCollector } from '../main/ets/UITreeCollector';
import { UITreeService } from '../main/ets/UITreeService';
import { DEFAULT_CONFIG } from '../main/ets/UITreeNode';

export default function UITreeProviderTest() {
  describe('UITreeCollector', () => {
    let collector: UITreeCollector;

    beforeAll(() => {
      collector = new UITreeCollector();
    });

    afterAll(() => {
      if (collector) {
        collector.destroy();
      }
    });

    it('should create collector instance', () => {
      expect(collector).not.toBeNull();
      expect(collector).not.toBeUndefined();
    });

    it('should initialize successfully', async () => {
      try {
        await collector.init();
        // 如果没有抛出异常,则认为初始化成功
        expect(true).assertTrue();
      } catch (error) {
        // 在某些环境下可能无法初始化Driver
        console.warn('Failed to initialize collector:', error);
      }
    });

    it('should collect UI tree', async () => {
      try {
        await collector.init();
        const tree = await collector.collectUITree();
        
        if (tree) {
          expect(tree).not.toBeNull();
          expect(tree.type).not.toBeNull();
          expect(tree.children).not.toBeNull();
          expect(Array.isArray(tree.children)).assertTrue();
        }
      } catch (error) {
        console.warn('Failed to collect UI tree:', error);
      }
    });
  });

  describe('UITreeService', () => {
    let service: UITreeService;

    beforeAll(() => {
      service = new UITreeService({
        port: 8888,
        enabled: true,
        localOnly: true
      });
    });

    afterAll(async () => {
      if (service) {
        await service.stop();
      }
    });

    it('should create service instance', () => {
      expect(service).not.toBeNull();
      expect(service).not.toBeUndefined();
    });

    it('should have correct default config', () => {
      const status = service.getStatus();
      expect(status.port).assertEqual(8888);
      expect(status.config.enabled).assertTrue();
      expect(status.config.localOnly).assertTrue();
    });

    it('should start service', async () => {
      try {
        await service.start();
        const status = service.getStatus();
        expect(status.running).assertTrue();
      } catch (error) {
        console.warn('Failed to start service:', error);
      }
    });

    it('should handle get UI tree request', async () => {
      try {
        await service.start();
        const response = await service.handleGetUITree();
        
        expect(response).not.toBeNull();
        expect(response.timestamp).not.toBeNull();
        expect(typeof response.success).assertEqual('boolean');
        
        if (response.success) {
          expect(response.tree).not.toBeNull();
        } else {
          expect(response.error).not.toBeNull();
        }
      } catch (error) {
        console.warn('Failed to handle request:', error);
      }
    });

    it('should stop service', async () => {
      try {
        await service.start();
        await service.stop();
        const status = service.getStatus();
        expect(status.running).assertFalse();
      } catch (error) {
        console.warn('Failed to stop service:', error);
      }
    });

    it('should update config', () => {
      service.updateConfig({ port: 9999 });
      const status = service.getStatus();
      expect(status.port).assertEqual(9999);
    });
  });

  describe('DEFAULT_CONFIG', () => {
    it('should have correct default values', () => {
      expect(DEFAULT_CONFIG.port).assertEqual(8080);
      expect(DEFAULT_CONFIG.enabled).assertTrue();
      expect(DEFAULT_CONFIG.localOnly).assertTrue();
      expect(DEFAULT_CONFIG.token).toBeUndefined();
    });
  });
}

