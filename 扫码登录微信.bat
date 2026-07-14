@echo off
REM ============================================================
REM   AionsHome 微信扫码登录（OpenClaw 微信插件）
REM   用途：调起 openclaw channels login，在终端显示二维码。
REM   扫完确认后凭据会写入 %USERPROFILE%\.openclaw\openclaw-weixin\accounts\
REM   然后按 Ctrl+C 退出，Ctrl+C 不会删凭据，放心按。
REM
REM   用法：双击运行。终端会显示二维码。用手机微信扫码并确认。
REM         看到 "Login successful" 之类的提示后即可 Ctrl+C。
REM ============================================================

setlocal

REM 强制用 scoop 那份 Node 24.x，绕开 openclaw 强制 22.19+ 的检查
set "NODE_EXE=C:\Users\Lenovo\scoop\apps\nodejs-lts\current\node.exe"
set "OPENCLAW=C:\Users\Lenovo\.openclaw-tools\node_modules\openclaw\openclaw.mjs"

if not exist "%NODE_EXE%" (
    echo [错误] 找不到 %NODE_EXE%
    echo        确认 scoop nodejs-lts 已装。
    pause
    exit /b 1
)

if not exist "%OPENCLAW%" (
    echo [错误] 找不到 %OPENCLAW%
    echo        先跑一次部署脚本装 openclaw，或者检查路径。
    pause
    exit /b 1
)

echo ============================================================
echo   AionsHome 微信扫码登录
echo   即将显示二维码，请在 60 秒内用手机微信扫码确认
echo ============================================================
echo.

"%NODE_EXE%" "%OPENCLAW%" channels login --channel openclaw-weixin
set RC=%ERRORLEVEL%

echo.
if %RC% NEQ 0 (
    echo [退出码 %RC%] 扫码未完成。重新双击本脚本再试一次。
) else (
    echo [完成] 凭据已写入 %USERPROFILE%\.openclaw\openclaw-weixin\accounts\
    echo        Aion 后端会每 2 秒自动发现新账号，无需重启。
    echo        下一步：到 Aion 前端打开目标聊天窗口，然后在微信里发 "绑定 AionsHome"。
)
echo.
pause
