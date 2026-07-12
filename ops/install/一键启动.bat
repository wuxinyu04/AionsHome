@echo off
chcp 65001 >nul
title Aion Chat
:: ROOT = 项目根目录 (此 .bat 在 ops/install/, 跳两层)
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

if exist "%ROOT%\.venv\Scripts\activate.bat" (
    call "%ROOT%\.venv\Scripts\activate.bat"
)

echo ========================================
echo   Aion Chat  正在启动...
echo   http://localhost:8080
echo   关闭此窗口即停止服务
echo ========================================

cd /d "%ROOT%\aion-chat"
python -u main.py
pause
