# 1. WiFi ADB 模式

> 手機與電腦處於同一個局域網時，無需 USB 數據線即可建立 ADB 橋接。

---

## 動機

當前必須插 USB + `adb reverse`。WiFi ADB 讓手機放在口袋裏也能轉發短信，適合居家/辦公固定網絡環境。

## 做法

### 方案 A：ADB over TCP/IP（最簡單）

Android 內置 WiFi ADB 支援（無需 Root）：

```
adb tcpip 5555
adb connect 192.168.x.x:5555
adb reverse tcp:8580 tcp:8580
```

**腳本化** — 擴展現有 `bridge.ps1` / `bridge.sh`：

```
smsbridge bridge --wifi         # 自動切換到 WiFi 模式
smsbridge bridge --wifi-disconnect  # 斷開 WiFi ADB
```

### 方案 B：mDNS 自動發現（零配置）

電腦端運行 mDNS 服務器，手機端自動發現 IP：

1. **電腦端**：`pip install zeroconf`，註冊 `_smsbridge._tcp` 服務
2. **Android 端**：使用 `NsdManager` API 發現服務
3. 發現後自動建立 HTTP 連線，手機端直接 POST 到電腦 IP

### 方案 C：QR Code 配對

手機 App 顯示掃碼界面，掃描電腦端 terminal 打印的二維碼：

1. **電腦端**：`pip install qrcode`，啓動時打印 QR（含 IP:Port）
2. **Android 端**：ZXing / ML Kit 掃碼，自動配置服務器 URL

## 檔案變更

| 文件 | 變更 |
|------|------|
| `scripts/bridge.sh` | 新增 `--wifi` 參數，調用 `adb tcpip` + `adb connect` |
| `scripts/bridge.ps1` | 同上 PowerShell 版本 |
| `android/.../HttpClient.kt` | 支援可配置 base URL（從 SharedPreferences 讀取） |
| `android/.../ForwardService.kt` | 監聽 URL 變化，重啓心跳 |
| `server/main.py` | 可選打印 QR Code 或 mDNS 通告 |

## 依賴

- `zeroconf`（Python，方案 B）
- `qrcode`（Python，方案 C）
- Android `NsdManager` / `CameraX` + ML Kit

## 風險

- WiFi ADB 在部分小米/MIUI 上可能不穩定
- 同一網絡下防火牆需允許 tcp:8580
- mDNS 在複雜 VLAN 環境可能無法跨子網

## 驗收標準

- 手機 WiFi 連接 → `smsbridge bridge --wifi` → 成功 reverse → 狀態變綠
- `smsbridge bridge --wifi-disconnect` → 斷開 WiFi ADB
- 斷開後自動 fallback 到 USB ADB
