#!/usr/bin/env python3
"""测试构建时间"""

import time
from src.utils.hvigor_wrapper import HvigorWrapper

if __name__ == "__main__":
    print(f"=== 开始构建 ===")
    start_time = time.time()
    
    wrapper = HvigorWrapper('D:\\lxl\\ho_dev_app_mcp\\MyApplication2')
    result = wrapper.build_hap()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n=== 构建完成 ===")
    print(f"成功: {result['success']}")
    print(f"HAP路径: {result.get('hap_path', 'N/A')}")
    print(f"总耗时: {duration:.2f} 秒")
    print(f"\nstdout长度: {len(result['stdout'])} 字符")
    print(f"stderr长度: {len(result['stderr'])} 字符")

