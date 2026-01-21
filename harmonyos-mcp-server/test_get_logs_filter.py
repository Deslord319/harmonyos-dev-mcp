#!/usr/bin/env python3
"""
测试get_logs工具的过滤功能
"""

import sys
import os

# 添加src目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

from utils.hdc_wrapper import HdcWrapper
from utils.logger import logger

def test_get_logs_basic():
    """测试基本日志获取"""
    print("\n" + "="*60)
    print("测试1: 基本日志获取（最后10行）")
    print("="*60)
    
    hdc = HdcWrapper()
    devices = hdc.list_devices()
    
    if not devices:
        print("❌ 没有找到连接的设备")
        return False
    
    device_id = devices[0]
    print(f"✅ 使用设备: {device_id}")
    
    logs = hdc.get_logs(device_id, lines=10)
    print(f"\n获取到 {len(logs.split(chr(10)))} 行日志")
    print("\n日志内容:")
    print("-" * 60)
    print(logs)
    print("-" * 60)
    
    return True

def test_get_logs_with_bundle():
    """测试按包名过滤日志"""
    print("\n" + "="*60)
    print("测试2: 按包名过滤日志")
    print("="*60)
    
    hdc = HdcWrapper()
    devices = hdc.list_devices()
    
    if not devices:
        print("❌ 没有找到连接的设备")
        return False
    
    device_id = devices[0]
    
    # 测试过滤系统应用日志
    bundle_name = "com.huawei"  # 华为系统应用
    print(f"✅ 过滤包名: {bundle_name}")
    
    logs = hdc.get_logs(device_id, lines=20, bundle_name=bundle_name)
    print(f"\n获取到 {len(logs.split(chr(10)))} 行日志")
    print("\n日志内容:")
    print("-" * 60)
    print(logs)
    print("-" * 60)
    
    return True

def test_get_logs_with_tag():
    """测试按标签过滤日志"""
    print("\n" + "="*60)
    print("测试3: 按标签过滤日志")
    print("="*60)
    
    hdc = HdcWrapper()
    devices = hdc.list_devices()
    
    if not devices:
        print("❌ 没有找到连接的设备")
        return False
    
    device_id = devices[0]
    
    # 测试过滤特定标签
    tag = "Ace"  # ArkUI框架标签
    print(f"✅ 过滤标签: {tag}")
    
    logs = hdc.get_logs(device_id, lines=20, tag=tag)
    print(f"\n获取到 {len(logs.split(chr(10)))} 行日志")
    print("\n日志内容:")
    print("-" * 60)
    print(logs)
    print("-" * 60)
    
    return True

def test_get_logs_combined():
    """测试组合过滤"""
    print("\n" + "="*60)
    print("测试4: 组合过滤（标签 + 包名）")
    print("="*60)
    
    hdc = HdcWrapper()
    devices = hdc.list_devices()
    
    if not devices:
        print("❌ 没有找到连接的设备")
        return False
    
    device_id = devices[0]
    
    tag = "Ace"
    bundle_name = "com.huawei"
    print(f"✅ 过滤标签: {tag}")
    print(f"✅ 过滤包名: {bundle_name}")
    
    logs = hdc.get_logs(device_id, lines=20, tag=tag, bundle_name=bundle_name)
    print(f"\n获取到 {len(logs.split(chr(10)))} 行日志")
    print("\n日志内容:")
    print("-" * 60)
    print(logs)
    print("-" * 60)
    
    return True

def main():
    """运行所有测试"""
    print("\n" + "🧪 " + "="*58)
    print("🧪  HarmonyOS MCP Server - get_logs过滤功能测试")
    print("🧪 " + "="*58)
    
    tests = [
        ("基本日志获取", test_get_logs_basic),
        ("按包名过滤", test_get_logs_with_bundle),
        ("按标签过滤", test_get_logs_with_tag),
        ("组合过滤", test_get_logs_combined),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())

