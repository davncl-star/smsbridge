# SMSBridge · Windows PowerShell ADB 橋接腳本
# 用法：.\bridge.ps1              一鍵建立 reverse 端口
#       .\bridge.ps1 -Watch      監聽 USB 熱插拔，自動重連
#
# 可放在 PowerShell $PROFILE 中加 alias 方便日常使用：
#   function Start-SmsBridge { & "C:\path\to\bridge.ps1" -Watch }

[CmdletBinding()]
param(
    [switch]$Watch,
    [int]$Interval = 3
)

$ErrorActionPreference = "Stop"

# ---- 定位 adb -----------------------------------------------------------
function Find-Adb {
    if (Get-Command adb -ErrorAction SilentlyContinue) {
        return "adb"
    }
    foreach ($env_var in @("ANDROID_HOME", "ANDROID_SDK_ROOT")) {
        $sdk = [Environment]::GetEnvironmentVariable($env_var)
        if ($sdk -and (Test-Path (Join-Path $sdk "platform-tools\adb.exe"))) {
            return (Join-Path $sdk "platform-tools\adb.exe")
        }
    }
    return $null
}

$adb = Find-Adb
if (-not $adb) {
    Write-Host "[ERROR] adb not found. Set ANDROID_HOME or add adb to PATH." -ForegroundColor Red
    exit 1
}

# ---- 啟動 server + 取得設備 --------------------------------------------
& $adb start-server | Out-Null
$raw = & $adb devices

# 解析授權設備 (state == "device"，過濾 "unauthorized" 等)
$devices = @($raw | Where-Object { $_ -match "^\S+\s+device\s*$" } | ForEach-Object {
    ($_ -split "\s+")[0]
})

if ($devices.Count -eq 0) {
    Write-Host "[ERROR] No authorized device connected" -ForegroundColor Red
    Write-Host "         Check: USB debugging enabled? Authorize the device?" -ForegroundColor Red
    exit 2
}

if ($devices.Count -gt 1) {
    Write-Host "[WARN] Multiple devices detected, will reverse on all" -ForegroundColor Yellow
}

# ---- 一次性 reverse -----------------------------------------------------
$result = & $adb reverse tcp:8580 tcp:8580
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] adb reverse failed" -ForegroundColor Red
    exit 4
}
Write-Host "[OK] Bridge established: tcp:8580 -> tcp:8580" -ForegroundColor Green
Write-Host "     Device(s): $($devices -join ', ')"

# ---- 監聽模式 -----------------------------------------------------------
if (-not $Watch) {
    exit 0
}

Write-Host "[INFO] Watch mode active. Polling every ${Interval}s, Ctrl+C to stop." -ForegroundColor Cyan
Write-Host ""

while ($true) {
    Start-Sleep -Seconds $Interval

    $raw = & $adb devices
    $current = @($raw | Where-Object { $_ -match "^\S+\s+device\s*$" } | ForEach-Object {
        ($_ -split "\s+")[0]
    })

    if ($current.Count -eq 0) {
        Write-Host "[!] Device disconnected" -ForegroundColor Yellow
        continue
    }

    # 重新建立 reverse（防止電腦端 adb server 重啟後丟失）
    & $adb reverse tcp:8580 tcp:8580 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] re-reverse failed" -ForegroundColor Yellow
    }
}
