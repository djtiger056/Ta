@echo off
chcp 65001 >nul
title LFBot 一键启动器
echo ========================================
echo       LFBot AI 聊天机器人启动器
echo ========================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv\" (
    echo ❌ 虚拟环境未找到，正在设置环境...
    echo.
    call setup.bat
    if errorlevel 1 (
        echo ❌ 环境设置失败，请手动检查
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
echo [1/3] 激活虚拟环境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 激活虚拟环境失败
    pause
    exit /b 1
)
echo ✓ 虚拟环境已激活

REM 启动后端服务
echo.
echo [2/3] 启动后端服务...
start "LFBot 后端" cmd /k "call venv\Scripts\activate.bat && python run.py"

REM 等待后端启动
echo 等待后端服务启动...
timeout /t 5 /nobreak >nul

REM 启动前端服务
echo.
echo [3/3] 启动前端服务...
cd frontend
start "LFBot 前端" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo          ✅ 启动完成！
echo ========================================
echo.
echo 📋 服务状态：
echo - 后端服务：http://localhost:8000
echo - 前端界面：http://localhost:3000
echo - API文档：http://localhost:8000/docs
echo.
echo 💡 提示：
echo - 首次启动可能需要等待依赖安装
echo - 如遇到问题请查看各服务窗口的错误信息
echo - 关闭所有窗口可停止所有服务
echo.
echo 🌐 现在可以在浏览器中打开：
echo http://localhost:3000
echo.

REM 询问是否打开浏览器
set /p open_browser="是否立即打开浏览器？(Y/n): "
if /i not "%open_browser%"=="n" (
    start http://localhost:3000
)

echo.
echo 按任意键关闭此窗口（服务将继续运行）...
pause >nul