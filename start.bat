@echo off
chcp 65001 >nul
title LFBot Launcher

echo ========================================
echo       LFBot AI Chatbot Launcher
echo ========================================
echo.

if not exist "venv\" (
    echo Virtual environment not found, setting up...
    echo.
    call setup.bat
    if errorlevel 1 (
        echo Setup failed, please check manually
        pause
        exit /b 1
    )
)

echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated

echo.
echo [2/3] Starting backend service...
start "LFBot Backend" cmd /k "call venv\Scripts\activate.bat && python run.py"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] Starting frontend service...
cd frontend
start "LFBot Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo          Startup Complete!
echo ========================================
echo.
echo Services:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000
echo - API Docs: http://localhost:8000/docs
echo.
echo Tips:
echo - First startup may take time for dependencies
echo - Check service windows for error messages
echo - Close all windows to stop all services
echo.
echo Open browser now? (Y/n)
set /p open_browser=
if /i not "%open_browser%"=="n" (
    start http://localhost:3000
)

echo.
echo Press any key to close this window...
pause >nul