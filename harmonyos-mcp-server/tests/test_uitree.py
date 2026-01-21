"""
UI树获取功能测试
直接测试核心功能，不依赖MCP服务器的配置和日志系统
"""
import subprocess
import json
from pathlib import Path


class SimpleHdcWrapper:
    """简化的hdc包装器，用于测试"""

    def __init__(self):
        self.hdc_path = "hdc"

    def list_devices(self):
        """列出设备"""
        result = subprocess.run(
            [self.hdc_path, 'list', 'targets'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            devices = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
            return devices
        return []

    def execute_shell(self, device_id, command):
        """执行shell命令"""
        result = subprocess.run(
            [self.hdc_path, '-t', device_id, 'shell', command],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip()
        }

    def get_window_list(self, device_id):
        """获取窗口列表"""
        command = "hidumper -s WindowManagerService -a '-a'"
        result = self.execute_shell(device_id, command)

        if not result['success']:
            return {'success': False, 'error': result['stderr'], 'windows': []}

        windows = []
        lines = result['stdout'].split('\n')

        # 查找表头
        header_idx = -1
        for i, line in enumerate(lines):
            if 'WindowName' in line and 'WinId' in line:
                header_idx = i
                break

        if header_idx == -1:
            return {'success': True, 'windows': [], 'raw_output': result['stdout']}

        # 解析窗口数据
        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 10:
                try:
                    window_info = {
                        'window_name': parts[0],
                        'display_id': int(parts[1]),
                        'pid': int(parts[2]),
                        'window_id': int(parts[3]),
                        'is_visible': parts[9].lower() == 'true'
                    }
                    windows.append(window_info)
                except (ValueError, IndexError):
                    continue

        return {'success': True, 'windows': windows, 'count': len(windows)}

    def get_ui_tree_raw(self, device_id, window_id):
        """获取UI树原始数据"""
        command = f"hidumper -s WindowManagerService -a '-w {window_id} -default -c'"
        result = self.execute_shell(device_id, command)

        if not result['success']:
            return {'success': False, 'error': result['stderr'], 'ui_tree': ''}

        return {'success': True, 'window_id': window_id, 'ui_tree': result['stdout']}


# 简化的UI树解析器
import re

class SimpleUITreeParser:
    """简化的UI树解析器"""

    def parse(self, raw_tree):
        """解析UI树"""
        if not raw_tree:
            return {'nodes': [], 'count': 0}

        lines = raw_tree.split('\n')
        root_nodes = []
        node_stack = []
        current_node = None

        for line in lines:
            # 检测组件节点
            component_match = re.match(r'^(\s*)\|->\s*(\w+)\s+childSize:(\d+)', line)
            if component_match:
                indent = len(component_match.group(1))
                component_type = component_match.group(2)
                child_size = int(component_match.group(3))

                depth = indent // 2

                new_node = {
                    'type': component_type,
                    'childSize': child_size,
                    'properties': {},
                    'children': []
                }

                while node_stack and node_stack[-1][0] >= depth:
                    node_stack.pop()

                if node_stack:
                    parent_node = node_stack[-1][1]
                    parent_node['children'].append(new_node)
                else:
                    root_nodes.append(new_node)

                node_stack.append((depth, new_node))
                current_node = new_node

            elif current_node is not None:
                prop_match = re.match(r'^\s*\|\s+([^:]+):\s*(.+)$', line)
                if prop_match:
                    prop_name = prop_match.group(1).strip()
                    prop_value = prop_match.group(2).strip()
                    current_node['properties'][prop_name] = prop_value

        count = self._count_nodes(root_nodes)
        return {'nodes': root_nodes, 'count': count}

    def _count_nodes(self, nodes):
        """计算节点总数"""
        count = len(nodes)
        for node in nodes:
            if 'children' in node:
                count += self._count_nodes(node['children'])
        return count


def test_get_window_list():
    """测试获取窗口列表"""
    print("=" * 60)
    print("测试: 获取窗口列表")
    print("=" * 60)

    hdc = SimpleHdcWrapper()
    devices = hdc.list_devices()

    if not devices:
        print("❌ 没有找到连接的设备")
        return False

    device_id = devices[0]
    print(f"✅ 使用设备: {device_id}")
    
    result = hdc.get_window_list(device_id)
    
    if result['success']:
        print(f"✅ 成功获取窗口列表，共 {result['count']} 个窗口")
        for i, window in enumerate(result['windows'], 1):
            print(f"\n窗口 {i}:")
            print(f"  - 名称: {window['window_name']}")
            print(f"  - ID: {window['window_id']}")
            print(f"  - PID: {window['pid']}")
            print(f"  - 可见: {window['is_visible']}")
        return True
    else:
        print(f"❌ 获取窗口列表失败: {result.get('error')}")
        return False


def test_get_ui_tree():
    """测试获取UI组件树"""
    print("\n" + "=" * 60)
    print("测试: 获取UI组件树")
    print("=" * 60)

    hdc = SimpleHdcWrapper()
    devices = hdc.list_devices()

    if not devices:
        print("❌ 没有找到连接的设备")
        return False

    device_id = devices[0]
    print(f"✅ 使用设备: {device_id}")
    
    # 获取窗口列表
    window_list = hdc.get_window_list(device_id)
    if not window_list['success'] or not window_list['windows']:
        print("❌ 没有找到窗口")
        return False
    
    # 使用第一个可见窗口
    window_id = None
    for window in window_list['windows']:
        if window['is_visible']:
            window_id = window['window_id']
            print(f"✅ 使用窗口: {window['window_name']} (ID: {window_id})")
            break
    
    if not window_id:
        window_id = window_list['windows'][0]['window_id']
        print(f"✅ 使用第一个窗口 (ID: {window_id})")
    
    # 获取UI树原始数据
    result = hdc.get_ui_tree_raw(device_id, window_id)
    
    if not result['success']:
        print(f"❌ 获取UI树失败: {result.get('error')}")
        return False
    
    print(f"✅ 成功获取UI树原始数据，长度: {len(result['ui_tree'])} 字符")

    # 解析UI树
    parser = SimpleUITreeParser()
    parsed_tree = parser.parse(result['ui_tree'])

    print(f"✅ 成功解析UI树，共 {parsed_tree['count']} 个节点")

    # 保存到文件
    output_file = Path(__file__).parent / 'uitree_output.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(parsed_tree, f, ensure_ascii=False, indent=2)

    print(f"✅ UI树已保存到: {output_file}")
    
    # 显示前几个节点
    if parsed_tree['nodes']:
        print("\n前3个根节点:")
        for i, node in enumerate(parsed_tree['nodes'][:3], 1):
            print(f"\n节点 {i}:")
            print(f"  - 类型: {node['type']}")
            print(f"  - 子节点数: {node['childSize']}")
            if node['properties']:
                print(f"  - 属性数: {len(node['properties'])}")
                # 显示部分属性
                for key in list(node['properties'].keys())[:5]:
                    print(f"    - {key}: {node['properties'][key]}")
    
    return True


def test_find_window_by_bundle():
    """测试根据包名查找窗口"""
    print("\n" + "=" * 60)
    print("测试: 根据包名查找窗口")
    print("=" * 60)

    hdc = SimpleHdcWrapper()
    devices = hdc.list_devices()

    if not devices:
        print("❌ 没有找到连接的设备")
        return False

    device_id = devices[0]

    # 尝试查找一个应用（使用测试应用的包名）
    bundle_name = "myapplication"
    print(f"查找应用: {bundle_name}")

    # 获取窗口列表
    window_list = hdc.get_window_list(device_id)
    if not window_list['success']:
        print(f"❌ 获取窗口列表失败")
        return False

    # 查找匹配的窗口
    found = False
    for window in window_list['windows']:
        if bundle_name.lower() in window['window_name'].lower():
            print(f"✅ 找到窗口: {window['window_name']} (ID: {window['window_id']})")
            found = True
            break

    if not found:
        print(f"⚠️ 未找到应用窗口（这是正常的，如果应用未运行）")

    return True


if __name__ == "__main__":
    print("HarmonyOS UI树获取功能测试\n")
    
    results = []
    
    # 运行测试
    results.append(("获取窗口列表", test_get_window_list()))
    results.append(("获取UI组件树", test_get_ui_tree()))
    results.append(("根据包名查找窗口", test_find_window_by_bundle()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\n总计: {passed}/{total} 通过")

