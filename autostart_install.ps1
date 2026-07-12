param([string]$Root)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
    Write-Host "[ERROR] .venv\Scripts\python.exe not found. Run 一键安装环境.bat first." -ForegroundColor Red
    exit 1
}

$vbs = Join-Path $Root 'autostart_launcher.vbs'
if (-not (Test-Path $vbs)) {
    Write-Host "[ERROR] $vbs not found" -ForegroundColor Red
    exit 1
}

# Run as the interactive logged-in user (NOT SYSTEM).
# System (Session 0) cannot reach the interactive desktop, so win32gui
# foreground-window capture, camera and mic would all break under SYSTEM.
$userId = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited

$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('"' + $vbs + '"') -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName 'AionChatAutoStart' `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Aion Chat autostart: login trigger, hidden, restart on fail. Logs at aion-chat\data\logs\autostart.log' `
    -Force | Out-Null

Write-Host "[OK] Task AionChatAutoStart registered (user: $userId, on logon)" -ForegroundColor Green
