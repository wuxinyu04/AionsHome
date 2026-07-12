@echo off
cd /d "%~dp0"
set "ROOT=%CD%"

echo ========================================
echo   Aion Chat - 注册开机自启任务
echo ========================================
echo.

powershell -ExecutionPolicy Bypass -NoProfile -File "%ROOT%\autostart_install.ps1" -Root "%ROOT%"
if not errorlevel 1 goto :reg_ok

echo.
echo [FAILED] 注册失败,请查看上方报错
pause
exit /b 1

:reg_ok
echo.
echo 检查 8080 端口...
netstat -ano | findstr "LISTENING" | findstr ":8080" >nul 2>&1
if errorlevel 1 goto :port_free

echo   8080 已有服务在跑,可能是 一键启动.bat 手动启动的
echo   跳过立即启动以避免端口冲突,任务已注册,下次登录或重启后自动接管
goto :show_summary

:port_free
echo   8080 空闲,立即启动一次,无需重新登录...
schtasks /Run /TN "AionChatAutoStart" >nul 2>&1
ping -n 5 127.0.0.1 >nul
netstat -ano | findstr "LISTENING" | findstr ":8080" >nul 2>&1
if errorlevel 1 goto :warn
echo   [OK] 服务已通过任务启动
goto :show_summary

:warn
echo   [WARN] 启动后 8080 仍未监听
echo          查看日志: aion-chat\data\logs\autostart.log

:show_summary
echo.
echo ========================================
echo   [OK] 安装完成
echo ========================================
echo   触发: 当前用户登录时自动启动
echo   形态: 隐藏后台运行,无窗口
echo   日志: aion-chat\data\logs\autostart.log
echo   崩溃: 1 分钟后自动重启,最多 3 次
echo   验证: 浏览器打开 http://localhost:8080
echo.
echo   注意: 你当前开机停在锁屏,需登录一次服务才会起。
echo         若要真·开机即起,需配置 Windows 自动登录:
echo           1. Win+R 运行 netplwiz
echo           2. 取消勾选「要使用本计算机,用户必须输入用户名和密码」
echo           3. 确定后输入你的 Windows 登录密码
echo         Win11 若看不到该勾选框,需先改注册表:
echo         HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon
echo         新建或修改 DevicePasswordLessBuildVersion=0 后重启
echo ========================================
echo.
pause
