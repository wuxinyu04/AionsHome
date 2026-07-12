@echo off
cd /d "%~dp0aion-chat"
if not exist "data\logs" mkdir "data\logs"
echo. >> "data\logs\autostart.log"
echo [%date% %time%] === Aion Chat starting === >> "data\logs\autostart.log"
"%~dp0.venv\Scripts\python.exe" -u main.py >> "data\logs\autostart.log" 2>&1
echo [%date% %time%] === Aion Chat exited (code %errorlevel%) === >> "data\logs\autostart.log"
