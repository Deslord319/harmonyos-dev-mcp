@echo off
REM HarmonyOS MCP Server 调试启动脚本

echo ========================================
echo HarmonyOS MCP Server 调试启动
echo ========================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

echo 当前目录: %CD%
echo.

echo 检查Python版本...
python --version
echo.

echo 检查依赖...
python -c "import fastmcp; print('✅ fastmcp:', fastmcp.__version__)"
python -c "import loguru; print('✅ loguru 已安装')"
echo.

echo 检查配置...
python -c "import sys; sys.path.insert(0, 'src'); from config import Config; Config.init(); print('✅ SDK路径:', Config.HARMONYOS_SDK_PATH); print('✅ hdc路径:', Config.HDC_PATH)"
echo.

echo 尝试启动MCP服务器...
echo ========================================
python src/main.py
echo.

echo ========================================
echo MCP服务器已退出
echo ========================================
pause

