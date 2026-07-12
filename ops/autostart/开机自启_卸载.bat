@echo off
cd /d "%~dp0"
echo 正在删除计划任务 AionChatAutoStart ...
powershell -ExecutionPolicy Bypass -NoProfile -File "%CD%\autostart_uninstall.ps1"
echo.
echo ========================================
echo   提示: 服务进程可能仍在后台运行
echo   如需立即停止:
echo     - 任务管理器 → 结束 python.exe 进程
echo     - 或命令: schtasks /End /TN "AionChatAutoStart"
echo     - 或重启电脑
echo ========================================
echo.
pause
