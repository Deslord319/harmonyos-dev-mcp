"""
测试MCP工具列表
"""
import subprocess
import json
import sys
import time

def test_tools():
    print("=" * 60)
    print("测试MCP工具列表")
    print("=" * 60)
    
    # 启动服务器
    print("\n启动MCP服务器...")
    proc = subprocess.Popen(
        [sys.executable, "src/main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        bufsize=1
    )
    
    time.sleep(2)
    
    try:
        # 1. 初始化
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }
        
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()
        
        resp = proc.stdout.readline()
        print("✅ 初始化响应:", resp.strip()[:100], "...")
        
        # 2. 获取工具列表
        tools_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        proc.stdin.write(json.dumps(tools_req) + "\n")
        proc.stdin.flush()
        
        resp = proc.stdout.readline()
        data = json.loads(resp)
        
        if "result" in data and "tools" in data["result"]:
            tools = data["result"]["tools"]
            print(f"\n✅ 找到 {len(tools)} 个工具:\n")
            
            for i, tool in enumerate(tools, 1):
                print(f"{i}. {tool['name']}")
                print(f"   {tool.get('description', '')[:80]}")
            
            return True
        else:
            print("❌ 没有找到工具列表")
            print("响应:", json.dumps(data, indent=2))
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    success = test_tools()
    sys.exit(0 if success else 1)

