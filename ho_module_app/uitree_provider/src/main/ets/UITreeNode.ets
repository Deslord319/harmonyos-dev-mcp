/**
 * UI树节点数据结构
 */
export interface UITreeNode {
  // 控件类型
  type: string;
  // 控件ID
  id: string;
  // 控件文本
  text: string;
  // 控件边界
  bounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  // 是否可用
  enabled: boolean;
  // 是否可见
  visible: boolean;
  // 是否可点击
  clickable: boolean;
  // 是否可聚焦
  focusable: boolean;
  // 是否已选中
  checked: boolean;
  // 是否可滚动
  scrollable: boolean;
  // 其他属性
  attributes: Record<string, string>;
  // 子节点
  children: UITreeNode[];
}

/**
 * UI树响应数据结构
 */
export interface UITreeResponse {
  success: boolean;
  timestamp: number;
  tree?: UITreeNode;
  error?: string;
}

/**
 * HTTP服务配置
 */
export interface UITreeServiceConfig {
  // 服务端口
  port: number;
  // 是否启用
  enabled: boolean;
  // 访问令牌(可选,用于安全验证)
  token?: string;
  // 是否只允许本地访问
  localOnly: boolean;
}

/**
 * 默认配置
 */
export const DEFAULT_CONFIG: UITreeServiceConfig = {
  port: 8080,
  enabled: true,
  token: undefined,
  localOnly: true
};

