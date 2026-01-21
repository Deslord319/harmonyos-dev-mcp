"""
测试MCP服务器的stdio通信
模拟MCP客户端发送初始化请求
"""
import subprocess
import json
import sys
import time

def test_mcp_server():
    """测试MCP服务器的stdio通信"""
    print("=" * 60)
    print("测试MCP服务器stdio通信")
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
    
    print("✅ MCP服务器进程已启动")
    print(f"   PID: {process.pid}")
    
    # 等待服务器启动
    time.sleep(2)
    
    # 检查进程是否还在运行
    if process.poll() is not None:
        print("❌ MCP服务器进程已退出")
        stdout, stderr = process.communicate()
        print(f"\nSTDOUT:\n{stdout}")
        print(f"\nSTDERR:\n{stderr}")
        return False
    
    print("✅ MCP服务器进程正在运行")
    
    # 发送初始化请求
    print("\n2. 发送MCP初始化请求...")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        request_str = json.dumps(init_request) + "\n"
        print(f"   发送: {request_str.strip()}")
        process.stdin.write(request_str)
        process.stdin.flush()
        print("✅ 请求已发送")
    except Exception as e:
        print(f"❌ 发送请求失败: {e}")
        process.terminate()
        return False
    
    # 等待响应
    print("\n3. 等待响应...")
    try:
        # 设置超时
        import select
        import os
        
        # Windows不支持select，使用简单的readline
        response_line = process.stdout.readline()
        
        if response_line:
            print(f"✅ 收到响应: {response_line.strip()}")
            try:
                response = json.loads(response_line)
                print(f"\n响应内容:")
                print(json.dumps(response, indent=2, ensure_ascii=False))
                
                if "result" in response:
                    print("\n✅ MCP服务器初始化成功！")
                    print(f"   服务器名称: {response['result'].get('serverInfo', {}).get('name', 'N/A')}")
                    print(f"   协议版本: {response['result'].get('protocolVersion', 'N/A')}")
                    return True
                else:
                    print("\n⚠️  响应中没有result字段")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ 解析响应失败: {e}")
                return False
        else:
            print("❌ 没有收到响应")
            return False
            
    except Exception as e:
        print(f"❌ 读取响应失败: {e}")
        return False
    finally:
        # 清理
        print("\n4. 清理...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ MCP服务器进程已终止")
        except:
            process.kill()
            print("⚠️  强制终止MCP服务器进程")


if __name__ == "__main__":
    print("\n🚀 MCP服务器stdio通信测试\n")
    
    success = test_mcp_server()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过！MCP服务器可以正常通信")
    else:
        print("❌ 测试失败！请检查错误信息")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

