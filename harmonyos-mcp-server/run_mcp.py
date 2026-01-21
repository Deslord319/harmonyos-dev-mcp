#!/usr/bin/env python3
"""
HarmonyOS MCP Server 启动脚本
这个脚本可以直接被MCP客户端调用
"""
import sys
import os

# 添加src目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# 导入并运行主程序
from main import server, Config, logger

if __name__ == "__main__":
    # 验证配置
    if not Config.validate():
        logger.error("配置验证失败,请检查环境变量")
        sys.exit(1)
    
    logger.info("HarmonyOS MCP Server 启动")
    logger.info(f"hdc路径: {Config.HDC_PATH}")
    
    # 启动MCP服务器
    server.run()

