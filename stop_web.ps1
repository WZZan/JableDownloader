# stop_web.ps1
# 停止由 start_web.ps1 啟動的背景網頁服務（連同子行程一起結束）。

$ErrorActionPreference = 'Stop'
$root    = $PSScriptRoot
$pidFile = Join-Path $root 'web.pid'

if (-not (Test-Path $pidFile)) {
    Write-Host "找不到 web.pid，服務可能尚未啟動。" -ForegroundColor Yellow
    exit 0
}

$pidVal = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $pidVal) {
    Write-Host "web.pid 是空的，已清除。" -ForegroundColor Yellow
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    exit 0
}

# /T 連同子行程(python)整棵結束，/F 強制
taskkill /PID $pidVal /T /F 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "已停止服務 (PID $pidVal)" -ForegroundColor Green
} else {
    Write-Host "行程 (PID $pidVal) 可能已不存在。" -ForegroundColor Yellow
}

Remove-Item $pidFile -ErrorAction SilentlyContinue
