"""
MCP服务器启动测试脚本
用于验证MCP服务器是否能正常启动和运行
"""
import sys
import os

# 添加src目录到路径
sys.path.insert(0, 'src')

def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("测试1: 检查模块导入")
    print("=" * 60)
    
    try:
        from main import server
        print("✅ main.server 导入成功")
        
        from config import Config
        print("✅ config.Config 导入成功")
        
        from utils.hdc_wrapper import HdcWrapper
        print("✅ utils.hdc_wrapper.HdcWrapper 导入成功")
        
        from utils.hvigor_wrapper import HvigorWrapper
        print("✅ utils.hvigor_wrapper.HvigorWrapper 导入成功")
        
        from utils.uitree_parser import UITreeParser
        print("✅ utils.uitree_parser.UITreeParser 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_info():
    """测试服务器信息"""
    print("\n" + "=" * 60)
    print("测试2: 检查服务器信息")
    print("=" * 60)
    
    try:
        from main import server
        print(f"✅ 服务器名称: {server.name}")
        
        # 获取所有工具
        tools = []
        if hasattr(server, '_tools'):
            tools = list(server._tools.keys())
        elif hasattr(server, 'list_tools'):
            tools = [t.name for t in server.list_tools()]
        
        if tools:
            print(f"✅ 可用工具数量: {len(tools)}")
            print("\n可用的MCP工具:")
            for i, tool in enumerate(tools, 1):
                print(f"  {i}. {tool}")
        else:
            print("⚠️  无法获取工具列表")
        
        return True
    except Exception as e:
        print(f"❌ 获取服务器信息失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """测试配置"""
    print("\n" + "=" * 60)
    print("测试3: 检查配置")
    print("=" * 60)
    
    try:
        from config import Config
        
        print(f"✅ SDK路径: {Config.HARMONYOS_SDK_PATH}")
        print(f"✅ hdc路径: {Config.HDC_PATH}")
        print(f"✅ 日志级别: {Config.LOG_LEVEL}")
        
        return True
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hdc_connection():
    """测试hdc连接"""
    print("\n" + "=" * 60)
    print("测试4: 检查hdc设备连接")
    print("=" * 60)

    try:
        from utils.hdc_wrapper import HdcWrapper

        hdc = HdcWrapper()
        devices = hdc.list_devices()

        # list_devices返回的是列表，不是字典
        if isinstance(devices, list):
            print(f"✅ 找到 {len(devices)} 个设备")
            for device in devices:
                print(f"  - {device}")
        else:
            print(f"⚠️  未找到设备或返回格式错误")

        return True
    except Exception as e:
        print(f"❌ hdc连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "🚀" * 30)
    print("HarmonyOS MCP Server 启动测试")
    print("🚀" * 30 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("模块导入", test_imports()))
    results.append(("服务器信息", test_server_info()))
    results.append(("配置检查", test_config()))
    results.append(("hdc连接", test_hdc_connection()))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！MCP服务器可以正常启动。")
        print("\n下一步:")
        print("1. 重启VSCode以重新加载Augment配置")
        print("2. 在Augment中检查harmonyos-tools服务器状态")
        print("3. 尝试调用MCP工具: '列出所有HarmonyOS设备'")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

