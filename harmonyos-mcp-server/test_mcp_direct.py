#!/usr/bin/env python3
"""
直接测试 MCP 工具函数
"""
import sys
import os

# 添加src目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from utils.hvigor_wrapper import HvigorWrapper
import time

if __name__ == "__main__":
    print("=== 测试 build_app 逻辑 ===")
    start_time = time.time()

    try:
        print("步骤1: 创建HvigorWrapper")
        hvigor = HvigorWrapper("D:\\lxl\\ho_dev_app_mcp\\MyApplication2")

        print("步骤2: 调用build_hap")
        result = hvigor.build_hap(build_mode="debug")

        print("步骤3: 构建完成，准备响应")
        response = {
            'success': result['success'],
            'hap_path': result.get('hap_path'),
            'output': result['stdout'],
            'error': result['stderr'] if not result['success'] else None
        }

        elapsed = time.time() - start_time
        print(f"步骤4: 返回响应，总耗时: {elapsed:.2f}秒")
        print(f"\n结果: {response['success']}")
        if response.get('hap_path'):
            print(f"HAP路径: {response['hap_path']}")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"构建失败: {e}, 耗时: {elapsed:.2f}秒")

