@echo off
REM HarmonyOS MCP Server 启动脚本
REM 用于在Windows上启动MCP服务器

echo Starting HarmonyOS MCP Server...

REM 设置环境变量
set HARMONYOS_SDK_PATH=C:\Program Files\Huawei\DevEco Studio\sdk\default

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 启动MCP服务器
python src\main.py

pause

