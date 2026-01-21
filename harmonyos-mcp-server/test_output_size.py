#!/usr/bin/env python3
"""测试输出大小"""

from src.utils.hvigor_wrapper import HvigorWrapper

if __name__ == "__main__":
    wrapper = HvigorWrapper('D:\\lxl\\ho_dev_app_mcp\\MyApplication')
    result = wrapper.build_hap()
    
    print(f"stdout长度: {len(result['stdout'])} 字符")
    print(f"stderr长度: {len(result['stderr'])} 字符")
    print(f"\n前500字符:")
    print(result['stdout'][:500])

