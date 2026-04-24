@echo off
chcp 65001 >nul
echo ========================================
echo        LFBot 智能启动脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\python.exe" (
    echo ❌ 虚拟环境不存在，正在创建...
    call setup.bat
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
)

echo [1/3] 清理端口占用...
call clear_port.bat

echo.
echo [2/3] 激活虚拟环境并启动后端...
call venv\Scripts\activate.bat

echo.
echo [3/3] 启动LFBot后端服务...
echo.

python run.py

echo.
echo ========================================
echo 👋 LFBot 已停止运行
echo ========================================
pause