@echo off
:: ROOT = 项目根目录 (此 .bat 在 ops/autostart/, 跳两层)
set "ROOT=%~dp0..\.."
cd /d "%ROOT%\aion-chat"
if not exist "data\logs" mkdir "data\logs"
echo. >> "data\logs\autostart.log"
echo [%date% %time%] === Aion Chat starting === >> "data\logs\autostart.log"
"%ROOT%\.venv\Scripts\python.exe" -u main.py >> "data\logs\autostart.log" 2>&1
echo [%date% %time%] === Aion Chat exited (code %errorlevel%) === >> "data\logs\autostart.log"
