"""
基础功能测试
"""
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from utils.hdc_wrapper import HdcWrapper


def test_config():
    """测试配置"""
    print("=" * 60)
    print("测试配置")
    print("=" * 60)
    
    print(f"HarmonyOS SDK路径: {Config.HARMONYOS_SDK_PATH}")
    print(f"hdc路径: {Config.HDC_PATH}")
    print(f"配置有效: {Config.validate()}")
    print()


def test_hdc_list_devices():
    """测试列出设备"""
    print("=" * 60)
    print("测试列出设备")
    print("=" * 60)
    
    try:
        hdc = HdcWrapper()
        devices = hdc.list_devices()
        
        print(f"找到 {len(devices)} 个设备:")
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device}")
        
        return devices
    except Exception as e:
        print(f"错误: {e}")
        return []
    finally:
        print()


def test_hdc_get_logs():
    """测试获取日志"""
    print("=" * 60)
    print("测试获取日志")
    print("=" * 60)
    
    try:
        hdc = HdcWrapper()
        devices = hdc.list_devices()
        
        if not devices:
            print("没有找到设备")
            return
        
        device_id = devices[0]
        print(f"从设备 {device_id} 获取日志...")
        
        logs = hdc.get_logs(device_id, lines=10)
        print(f"最近10行日志:")
        print(logs)
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        print()


def test_hvigor():
    """测试hvigor构建"""
    print("=" * 60)
    print("测试hvigor构建工具")
    print("=" * 60)
    
    # 这里需要一个实际的HarmonyOS项目路径
    # 暂时跳过
    print("跳过(需要实际项目路径)")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("HarmonyOS MCP Server 基础功能测试")
    print("=" * 60 + "\n")
    
    # 运行测试
    test_config()
    
    devices = test_hdc_list_devices()
    
    if devices:
        test_hdc_get_logs()
    
    test_hvigor()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)

