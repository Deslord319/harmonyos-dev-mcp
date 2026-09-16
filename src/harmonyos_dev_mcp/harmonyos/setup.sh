#!/bin/bash
# ============================================================
# setup.sh — HarmonyOS 适配版一键配置
#
# 用法: bash setup.sh
#
# 输出:
#   1. 环境检测结果（stderr）
#   2. OpenDesk 可导入的 MCP JSON 配置（stdout）
#
# 使用方式:
#   bash setup.sh > mcp_config.json
#   然后在 OpenDesk 中导入该 JSON
#
# 或直接让 OpenDesk agent 运行:
#   "帮我运行 setup.sh 并导入 MCP 配置"
# ============================================================

set -e
exec 2>&1  # stderr 合并到 stdout 方便查看

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"  # src/

echo "=========================================="
echo " harmonyos-dev-mcp HarmonyOS 适配"
echo "=========================================="

# --- 1. 检测 Python ---
echo ""
echo "[1/4] 检测 Python..."

# 尝试多个候选路径
PY=""
for candidate in \
    "/data/app/python.org/python_3.12.9/bin/python3" \
    "$(which python3 2>/dev/null)"; do
    if [ -x "$candidate" ] 2>/dev/null; then
        version=$("$candidate" --version 2>/dev/null)
        if echo "$version" | grep -q "Python 3"; then
            PY="$candidate"
            echo "  ✅ $PY ($version)"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "  ❌ 未找到 Python 3.12+"
    exit 1
fi

# 检测 LD_LIBRARY_PATH
PY_HOME="$(dirname "$(dirname "$PY")")"
PY_LIB="$PY_HOME/lib"
LD_LIB=""
if [ -f "$PY_LIB/libpython3.12.so.1.0" ]; then
    LD_LIB="$PY_LIB"
    echo "  LD_LIBRARY_PATH: $PY_LIB"
fi

# --- 2. 检测 hdc server ---
echo ""
echo "[2/4] 检测 hdc server..."

HDC_OK="false"
"$PY" -c "
import socket
s = socket.socket()
s.settimeout(3)
try:
    s.connect(('127.0.0.1', 8710))
    print('  ✅ hdc server 已连接 (TCP 8710)')
    s.close()
except:
    print('  ❌ hdc server 未连接')
    print('  请在 HiShell 执行:')
    print('    hdc -s 0.0.0.0:8710 start -r')
    print('    hdc tconn 127.0.0.1:$(param get persist.hdc.port)')
" 2>/dev/null && HDC_OK="true" || echo "  ⚠️  hdc server 检测失败（请确认 HiShell 已启动）"

# --- 3. 检测 SDK ---
echo ""
echo "[3/4] 检测 SDK..."
SDK_PATH="${HARMONYOS_SDK_PATH:-/data/service/hnp/sdk.org/sdk_1.0.0/default}"
if [ -f "$SDK_PATH/sdk-pkg.json" ]; then
    echo "  ✅ $SDK_PATH"
else
    echo "  ⚠️  $SDK_PATH (可能不存在，尝试自动搜索)"
    FOUND_SDK=$(find /data/service/hnp/sdk.org -name "sdk-pkg.json" 2>/dev/null | head -1)
    if [ -n "$FOUND_SDK" ]; then
        SDK_PATH="$(dirname "$FOUND_SDK")"
        echo "  ✅ 找到: $SDK_PATH"
    fi
fi

# --- 4. 输出可导入的 JSON ---
echo ""
echo "[4/4] 生成 MCP 配置..."
echo ""

STUBS_DIR="$SRC_DIR/harmonyos_dev_mcp/harmonyos/stubs"

# 构建 env 字典
ENV_ENTRIES=""
if [ -n "$LD_LIB" ]; then
    ENV_ENTRIES="$ENV_ENTRIES    \"LD_LIBRARY_PATH\": \"$LD_LIB:\${LD_LIBRARY_PATH}\","
fi
ENV_ENTRIES="$ENV_ENTRIES
    \"PYTHONPATH\": \"$STUBS_DIR:$SRC_DIR\",
    \"HDC_USE_TCP\": \"1\",
    \"HARMONYOS_HDC_SERVER\": \"127.0.0.1:8710\",
    \"HARMONYOS_SDK_PATH\": \"$SDK_PATH\",
    \"DEVECO_STUDIO_PATH\": \"$SDK_PATH\",
    \"NODE_TLS_REJECT_UNAUTHORIZED\": \"0\",
    \"PATH\": \"/data/service/hnp/node.org/node_v24.18.1/bin:/data/service/hnp/bin:/data/app/bin:/system/bin\""

# 输出 OpenDesk 可导入的 JSON（Claude Desktop 格式）
cat << JSONEOF
{
  "mcpServers": {
    "harmonyos-dev-mcp": {
      "command": "$PY",
      "args": ["-c", "from harmonyos_dev_mcp.harmonyos.mcp_server import main; main()"],
      "env": {
$ENV_ENTRIES
      }
    }
  }
}
JSONEOF

echo ""
echo "=========================================="
echo " 配置已生成"
echo "=========================================="
echo ""
echo "导入方式:"
echo "  1. 将上面的 JSON 保存到文件"
echo "  2. 在 OpenDesk 中使用 MCP 导入功能"
echo "  3. 或直接告诉 OpenDesk agent:"
echo '     "帮我导入这段 MCP 配置: <粘贴 JSON>"'
echo ""
echo "导入后新开会话即可使用 18 个工具。"
echo "=========================================="
