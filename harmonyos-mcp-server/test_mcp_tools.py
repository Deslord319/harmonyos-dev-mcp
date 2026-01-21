"""
测试MCP服务器的工具列表功能
"""
import subprocess
import json
import sys
import time

def send_request(process, method, params=None):
    """发送MCP请求"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    request_str = json.dumps(request) + "\n"
    print(f"\n发送请求: {method}")
    print(f"  {request_str.strip()}")
    
    process.stdin.write(request_str)
    process.stdin.flush()
    
    # 读取响应
    response_line = process.stdout.readline()
    if response_line:
        print(f"\n收到响应:")
        response = json.loads(response_line)
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return response
    else:
        print("❌ 没有收到响应")
        return None

def test_tools_list():
    """测试工具列表"""
    print("=" * 60)
    print("测试MCP工具列表功能")
    print("=" * 60)
    
    # 启动MCP服务器
    print("\n1. 启动MCP服务器...")
    process = subprocess.Popen(
        [sys.executable, "src/main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print(f"✅ MCP服务器已启动 (PID: {process.pid})")
    time.sleep(2)
    
    try:
        # 初始化
        print("\n2. 发送初始化请求...")
        response = send_request(process, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        
        if not response or "result" not in response:
            print("❌ 初始化失败")
            return False
        
        print("✅ 初始化成功")
        
        # 获取工具列表
        print("\n3. 获取工具列表...")
        response = send_request(process, "tools/list", {})
        
        if not response or "result" not in response:
            print("❌ 获取工具列表失败")
            return False
        
        tools = response["result"].get("tools", [])
        print(f"\n✅ 找到 {len(tools)} 个工具:")
        print("=" * 60)
        
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool['name']}")
            print(f"   描述: {tool.get('description', 'N/A')}")
            
            # 显示参数
            if 'inputSchema' in tool:
                schema = tool['inputSchema']
                if 'properties' in schema:
                    print(f"   参数:")
                    for param_name, param_info in schema['properties'].items():
                        param_type = param_info.get('type', 'unknown')
                        param_desc = param_info.get('description', '')
                        required = param_name in schema.get('required', [])
                        req_mark = " (必需)" if required else " (可选)"
                        print(f"     - {param_name}: {param_type}{req_mark}")
                        if param_desc:
                            print(f"       {param_desc}")
        
        print("\n" + "=" * 60)
        return len(tools) > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理
        print("\n4. 清理...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ MCP服务器已终止")
        except:
            process.kill()
            print("⚠️  强制终止MCP服务器")

if __name__ == "__main__":
    print("\n🚀 MCP工具列表测试\n")
    
    success = test_tools_list()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过！工具列表可以正常查询")
    else:
        print("❌ 测试失败！工具列表查询有问题")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

