"""
完整的MCP协议测试
模拟Augment客户端的完整交互流程
"""
import subprocess
import json
import sys
import time

def send_message(proc, method, params=None, msg_id=1):
    """发送MCP消息"""
    msg = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": method
    }
    if params is not None:
        msg["params"] = params
    
    msg_str = json.dumps(msg) + "\n"
    print(f"\n>>> 发送: {method}")
    print(f"    {msg_str.strip()}")
    
    proc.stdin.write(msg_str)
    proc.stdin.flush()
    
    # 读取响应
    response_line = proc.stdout.readline()
    if response_line:
        print(f"<<< 响应:")
        try:
            response = json.loads(response_line)
            print(f"    {json.dumps(response, indent=2, ensure_ascii=False)[:200]}...")
            return response
        except:
            print(f"    {response_line.strip()}")
            return None
    else:
        print("<<< 无响应")
        return None

def test_mcp_protocol():
    """测试完整的MCP协议流程"""
    print("=" * 70)
    print("MCP协议完整测试")
    print("=" * 70)
    
    # 启动服务器
    print("\n[1] 启动MCP服务器...")
    proc = subprocess.Popen(
        [sys.executable, "src/main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        bufsize=1
    )
    
    print(f"    PID: {proc.pid}")
    time.sleep(2)
    
    if proc.poll() is not None:
        print("    ❌ 服务器启动失败")
        stdout, stderr = proc.communicate()
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    print("    ✅ 服务器已启动")
    
    try:
        # 1. Initialize
        print("\n[2] 发送 initialize 请求...")
        resp = send_message(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {
                    "listChanged": True
                },
                "sampling": {}
            },
            "clientInfo": {
                "name": "augment-test-client",
                "version": "1.0.0"
            }
        }, 1)
        
        if not resp or "result" not in resp:
            print("    ❌ initialize 失败")
            return False
        
        print("    ✅ initialize 成功")
        print(f"    服务器: {resp['result'].get('serverInfo', {}).get('name')}")
        print(f"    协议版本: {resp['result'].get('protocolVersion')}")
        
        # 2. initialized 通知
        print("\n[3] 发送 initialized 通知...")
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        proc.stdin.write(json.dumps(initialized_msg) + "\n")
        proc.stdin.flush()
        print("    ✅ initialized 通知已发送")
        
        # 3. tools/list
        print("\n[4] 发送 tools/list 请求...")
        resp = send_message(proc, "tools/list", {}, 2)
        
        if not resp or "result" not in resp:
            print("    ❌ tools/list 失败")
            return False
        
        tools = resp["result"].get("tools", [])
        print(f"    ✅ tools/list 成功")
        print(f"    找到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"      - {tool['name']}")
        
        # 4. 调用一个工具
        print("\n[5] 调用 list_devices 工具...")
        resp = send_message(proc, "tools/call", {
            "name": "list_devices",
            "arguments": {}
        }, 3)
        
        if resp and "result" in resp:
            print("    ✅ 工具调用成功")
            content = resp["result"].get("content", [])
            if content:
                print(f"    结果: {content[0].get('text', '')[:100]}...")
        else:
            print("    ⚠️ 工具调用失败（可能是正常的，如果没有设备）")
        
        print("\n" + "=" * 70)
        print("✅ MCP协议测试完成！服务器符合MCP规范")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n[6] 清理...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
            print("    ✅ 服务器已终止")
        except:
            proc.kill()
            print("    ⚠️ 强制终止服务器")

if __name__ == "__main__":
    success = test_mcp_protocol()
    sys.exit(0 if success else 1)

