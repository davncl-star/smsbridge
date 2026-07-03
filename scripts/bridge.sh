#!/usr/bin/env bash
# SMSBridge · Linux/macOS ADB 橋接腳本
# 用法：./bridge.sh              一鍵建立 reverse 端口
#       ./bridge.sh --watch      監聽 USB 熱插拔，自動重連

set -euo pipefail

# ---- 定位 adb -----------------------------------------------------------
ADB="${ADB:-adb}"
if ! command -v "$ADB" >/dev/null 2>&1; then
    if [[ -n "${ANDROID_HOME:-}" ]]; then
        ADB="$ANDROID_HOME/platform-tools/adb"
    elif [[ -n "${ANDROID_SDK_ROOT:-}" ]]; then
        ADB="$ANDROID_SDK_ROOT/platform-tools/adb"
    fi
fi

if ! command -v "$ADB" >/dev/null 2>&1; then
    echo "[ERROR] adb not found. Set ANDROID_HOME or add adb to PATH." >&2
    exit 1
fi

# ---- 解析參數 -----------------------------------------------------------
WATCH=0
for arg in "$@"; do
    case "$arg" in
        --watch|-w) WATCH=1 ;;
        --help|-h)
            cat <<EOF
SMSBridge · ADB bridge
Usage:
  $0              One-shot reverse port 8580
  $0 --watch      Hot-plug monitor (polls every 3s)

Env:
  ANDROID_HOME    Path to Android SDK (used to locate adb)
EOF
            exit 0
            ;;
    esac
done

# ---- 啟動 adb server + 檢查設備 ----------------------------------------
"$ADB" start-server >/dev/null 2>&1 || true

# 統計授權的設備
mapfile -t DEVICES < <("$ADB" devices | awk 'NR>1 && $2=="device" {print $1}')

if [[ ${#DEVICES[@]} -eq 0 ]]; then
    echo "[ERROR] No authorized device connected" >&2
    echo "         Check: USB debugging enabled? Authorize the device?" >&2
    exit 2
fi

if [[ ${#DEVICES[@]} -gt 1 ]]; then
    echo "[WARN] Multiple devices detected, will reverse on all" >&2
fi

# ---- 一次性 reverse -----------------------------------------------------
if ! "$ADB" reverse tcp:8580 tcp:8580; then
    echo "[ERROR] adb reverse failed" >&2
    exit 4
fi
echo "[OK] Bridge established: tcp:8580 -> tcp:8580"
echo "     Device(s): ${DEVICES[*]}"

# ---- 監聽模式 -----------------------------------------------------------
if [[ "$WATCH" -ne 1 ]]; then
    exit 0
fi

echo "[INFO] Watch mode active. Polling every 3s, Ctrl+C to stop."
echo

while true; do
    sleep 3

    mapfile -t CURRENT < <("$ADB" devices | awk 'NR>1 && $2=="device" {print $1}')

    if [[ ${#CURRENT[@]} -eq 0 ]]; then
        echo "[!] Device disconnected"
        continue
    fi

    # 重新建立 reverse（防止電腦端重啟後丟失）
    if "$ADB" reverse tcp:8580 tcp:8580 >/dev/null 2>&1; then
        :
    else
        echo "[WARN] re-reverse failed"
    fi
done
