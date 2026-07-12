# Watchdog：每 5 分钟检查一次，HKCU ProxyOverride 或 WinHTTP bypass 丢了就补回去
# 由任务计划程序以 SYSTEM 身份运行

$ErrorActionPreference = 'SilentlyContinue'

$required = @('100.64.*', '100.100.100.100', '*.tailscale.com')
$svcPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tailscale'

# === 1) 检查/恢复 Tailscale 服务级 NO_PROXY ===
$noProxyLine = 'NO_PROXY=localhost,127.0.0.1,100.64.0.0/10,.tailscale.com,*.tailscale.com,controlplane.tailscale.com,login.tailscale.com'
$existing = (Get-ItemProperty -Path $svcPath -Name 'Environment' -ErrorAction SilentlyContinue).Environment
$hasNoProxy = $false
if ($existing) {
  foreach ($line in $existing) {
    if ($line -match '^NO_PROXY=') { $hasNoProxy = $true; break }
  }
}
if (-not $hasNoProxy) {
  $list = if ($existing) { @($existing) } else { @() }
  $list += $noProxyLine
  Set-ItemProperty -Path $svcPath -Name 'Environment' -Type MultiString -Value $list
  # 重新读取并启动服务让 Environment 生效
  Restart-Service Tailscale -Force
  Write-Host "[watchdog] Tailscale service Environment restored, service restarted"
}

# === 2) 检查/恢复 HKCU ProxyOverride (64 位视图) ===
$hkcu = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
$cur = (Get-ItemProperty -Path $hkcu -Name 'ProxyOverride' -ErrorAction SilentlyContinue).ProxyOverride
if ($cur) {
  $items = $cur -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique
  $changed = $false
  foreach ($r in $required) {
    if ($items -notcontains $r) { $items += $r; $changed = $true }
  }
  if ($changed) {
    $new = ($items -join ';')
    Set-ItemProperty -Path $hkcu -Name 'ProxyOverride' -Value $new -Type String
    Write-Host "[watchdog] HKCU ProxyOverride restored"
  }
}

# === 3) 检查/恢复 WinHTTP bypass-list ===
$winBypass = (netsh winhttp show proxy) -join "`n"
$needsBypass = $false
foreach ($r in $required) {
  if ($winBypass -notlike "*$r*") { $needsBypass = $true; break }
}
if ($needsBypass) {
  $proxyLine = (netsh winhttp show proxy | Select-String 'Proxy Server' | Select-Object -First 1)
  $proxyServer = if ($proxyLine) { ($proxyLine -replace '.*Proxy Server\(s\)\s*:\s*', '').Trim() } else { '' }
  $bypass = 'localhost;127.*;192.168.*;<local>;100.64.*;100.100.100.100;*.tailscale.com'
  if ($proxyServer) {
    netsh winhttp set proxy "proxy-server=`"$proxyServer`" bypass-list=`"$bypass`"" | Out-Null
  } else {
    netsh winhttp set proxy proxy-server="127.0.0.1:10808" bypass-list="$bypass" | Out-Null
  }
  Write-Host "[watchdog] WinHTTP bypass-list restored"
}