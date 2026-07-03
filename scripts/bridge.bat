@echo off
REM SMSBridge · Windows ADB 橋接腳本
REM 用法：bridge.bat              一鍵建立 reverse 端口
REM       bridge.bat --watch      監聽 USB 熱插拔，自動重連

setlocal enabledelayedexpansion

REM ---- 定位 adb -------------------------------------------------------
set ADB=adb
where adb >nul 2>nul
if %errorlevel% neq 0 (
    if defined ANDROID_HOME (
        set ADB=!ANDROID_HOME!\platform-tools\adb.exe
    ) else if defined ANDROID_SDK_ROOT (
        set ADB=!ANDROID_SDK_ROOT!\platform-tools\adb.exe
    )
)

if not exist "%ADB%" (
    echo [ERROR] adb not found. Set ANDROID_HOME or add adb to PATH.
    exit /b 1
)

REM ---- 解析參數 -------------------------------------------------------
set WATCH=0
if /i "%1"=="--watch" set WATCH=1
if /i "%1"=="-w" set WATCH=1

REM ---- 取得已連接設備 -------------------------------------------------
"%ADB%" start-server >nul 2>&1
"%ADB%" devices | findstr /R "\<device$" > devices.txt
set COUNT=0
for /f "tokens=1" %%d in (devices.txt) do set /a COUNT+=1
del devices.txt

if !COUNT! equ 0 (
    echo [ERROR] No authorized device connected
    echo         Check: USB debugging enabled? Authorize the device?
    exit /b 2
)

if !COUNT! gtr 1 (
    echo [WARN] Multiple devices detected, will reverse on all
)

REM ---- 一次性 reverse -------------------------------------------------
"%ADB%" reverse tcp:8580 tcp:8580
if %errorlevel% neq 0 (
    echo [ERROR] adb reverse failed
    exit /b 4
)
echo [OK] Bridge established: tcp:8580 -^> tcp:8580

REM ---- 監聽模式 --------------------------------------------------------
if !WATCH! neq 1 goto :eof
echo [INFO] Watch mode active. Polling every 3s, Ctrl+C to stop.
echo.

:loop
timeout /t 3 /nobreak >nul

"%ADB%" devices | findstr /R "\<device$" > devices.txt
set CUR=0
for /f "tokens=1" %%d in (devices.txt) do set /a CUR+=1
del devices.txt

if !CUR! equ 0 (
    echo [!] Device disconnected
    goto :loop
)

REM 重新建立 reverse（防止電腦端重啟後丟失）
"%ADB%" reverse tcp:8580 tcp:8580 >nul 2>&1
goto :loop
