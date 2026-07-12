@echo off
cd /d "%~dp0"

echo ========================================
echo   Aion Chat - 重启服务
echo ========================================
echo.

echo [1/3] 停止当前服务...
set "TARGET_PID="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8080"') do (
    set "TARGET_PID=%%a"
)
if defined TARGET_PID goto :kill
echo     未检测到 8080 监听进程,可能本就没在跑
goto :start

:kill
echo     发现进程 PID=%TARGET_PID%
taskkill /F /PID %TARGET_PID% >nul 2>&1
ping -n 3 127.0.0.1 >nul
echo     已停止

:start
echo [2/3] 启动服务...
schtasks /Run /TN "AionChatAutoStart" >nul 2>&1
if not errorlevel 1 goto :wait
echo     [ERROR] 计划任务 AionChatAutoStart 未找到
echo            请先双击「开机自启_安装.bat」注册任务
pause
exit /b 1

:wait
ping -n 5 127.0.0.1 >nul
echo [3/3] 验证端口...
set "NEW_PID="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8080"') do (
    set "NEW_PID=%%a"
)
if defined NEW_PID goto :ok
echo     [WARN] 8080 仍未监听,服务可能启动失败
echo            查看日志: aion-chat\data\logs\autostart.log
goto :done

:ok
echo     [OK] 服务已启动 PID=%NEW_PID%
echo     访问: http://localhost:8080

:done
echo.
echo ========================================
echo   完成  日志: aion-chat\data\logs\autostart.log
echo ========================================
pause
