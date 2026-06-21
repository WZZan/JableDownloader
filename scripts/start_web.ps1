# start_web.ps1
# 在背景常駐啟動 Jable Downloader 網頁服務（透過 uv run）。
# 透過 WMI(Win32_Process)建立行程，使其「完全脫離 SSH session」，
# 這樣 SSH/網路斷線時，PC 上的下載不會被一起殺掉。
# stdout/stderr 合併寫入 web.log，PID 記錄到 web.pid（皆放專案根目錄）。

$ErrorActionPreference = 'Stop'
$root    = Split-Path $PSScriptRoot -Parent      # 專案根目錄（scripts/ 的上一層）
$log     = Join-Path $root 'web.log'
$pidFile = Join-Path $root 'web.pid'

# 1. 已在執行就不重複啟動
if (Test-Path $pidFile) {
    $oldPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($oldPid -and (Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue)) {
        Write-Host "已在執行中 (PID $oldPid)。要重啟請先執行 .\scripts\stop_web.ps1" -ForegroundColor Yellow
        exit 0
    }
}

# 2. 找到 uv
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $env:USERPROFILE '.local\bin\uv.exe' }
if (-not (Test-Path $uv)) {
    Write-Host "找不到 uv，請先安裝 uv 或確認其在 PATH。" -ForegroundColor Red
    exit 1
}

# 3. 透過 WMI 建立脫離 session 的行程；uv run 會自動同步依賴並啟動入口點
$cmdLine = 'cmd.exe /c " "{0}" run jable-web > "{1}" 2>&1 "' -f $uv, $log
$res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine      = $cmdLine
    CurrentDirectory = $root
}

if ($res.ReturnValue -ne 0) {
    Write-Host "啟動失敗 (Win32_Process ReturnValue = $($res.ReturnValue))" -ForegroundColor Red
    exit 1
}

$res.ProcessId | Out-File -FilePath $pidFile -Encoding ascii

Write-Host "已在背景啟動 Jable Downloader (PID $($res.ProcessId))" -ForegroundColor Green
Write-Host "  PC 本機開啟 : http://localhost:8000"
Write-Host "  即時看 log  : Get-Content `"$log`" -Wait -Tail 50"
Write-Host "  停止服務    : .\scripts\stop_web.ps1"
Write-Host "此行程已脫離 SSH，現在可以安心關掉 SSH 連線，下載會繼續。" -ForegroundColor Cyan
