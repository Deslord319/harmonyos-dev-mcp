#!/usr/bin/env python3
"""
测试构建HarmonyOS应用
"""

import sys
import os

# 添加src目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from utils.hvigor_wrapper import HvigorWrapper
from utils.logger import logger

def main():
    project_path = r"D:\lxl\ho_dev_app_mcp\MyApplication"
    
    print("=" * 60)
    print("开始构建HarmonyOS应用")
    print("=" * 60)
    print(f"项目路径: {project_path}")
    print()
    
    try:
        # 初始化HvigorWrapper
        hvigor = HvigorWrapper(project_path)
        
        # 构建HAP包
        print("开始构建HAP包...")

        # 先尝试简单的clean命令看看环境是否正常
        print("测试hvigor环境...")
        test_result = hvigor._execute_command(['--version'])
        print(f"hvigor版本检查: {test_result['success']}")
        if test_result['stdout']:
            print(f"输出: {test_result['stdout']}")
        if test_result['stderr']:
            print(f"错误: {test_result['stderr']}")
        print()

        result = hvigor.build_hap(build_mode="debug")
        
        print()
        print("=" * 60)
        print("构建结果")
        print("=" * 60)
        print(f"成功: {result['success']}")
        
        if result['success']:
            print(f"HAP路径: {result.get('hap_path')}")
        
        print()
        print("标准输出:")
        print("-" * 60)
        print(result['stdout'])
        
        if result['stderr']:
            print()
            print("错误输出:")
            print("-" * 60)
            print(result['stderr'])
        
        return 0 if result['success'] else 1
        
    except Exception as e:
        print()
        print("=" * 60)
        print("构建失败")
        print("=" * 60)
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

