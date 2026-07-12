$ErrorActionPreference = 'Continue'
try {
    Unregister-ScheduledTask -TaskName 'AionChatAutoStart' -Confirm:$false -ErrorAction Stop
    Write-Host "[OK] Task AionChatAutoStart removed" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Task not found or already removed" -ForegroundColor Yellow
}
