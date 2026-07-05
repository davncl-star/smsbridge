# SMSBridge · 安裝指南

> SMS → Telegram forwarding over USB (ADB reverse).  
> 零雲端依賴，僅需一部 Android 手機 + 一台電腦 + USB 線。

---

## 目錄

1. [系統要求](#系統要求)
2. [快速開始（一鍵部署）](#快速開始一鍵部署)
3. [詳細安裝](#詳細安裝)
   - [3.1 電腦端（Server）](#31-電腦端server)
   - [3.2 手機端（Android App）](#32-手機端android-app)
4. [啟動與驗證](#啟動與驗證)
5. [排錯 FAQ](#排錯-faq)

---

## 系統要求

### 電腦端
- **OS**：Linux（推薦 Ubuntu 22.04+）、macOS、Windows（PowerShell 7+）
- **Python**：3.11+
- **套件管理器**：`uv`（推薦）或 `pip`
- **ADB**：Android SDK Platform-Tools（`$ANDROID_HOME/platform-tools/adb`）
- **systemd**（可選，Linux 自動重啟）：`systemctl --user`

### 手機端
- **Android**：API 26+（Android 8.0+）
- **權限**：USB 調試 / 接收短信 / 讀取手機狀態 / 通知
- **數據線**：支援 ADB 的 USB 線

---

## 快速開始（一鍵部署）

```bash
# 1. 複製倉庫
git clone https://github.com/davncl-star/smsbridge.git
cd smsbridge

# 2. 建立 .env 配置檔
cp .env.example .env
# 編輯 .env，填入 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_IDS

# 3. 安裝 Python 依賴
pip install uv   # 若未安裝 uv
uv sync

# 4. 啟用 systemd 服務（Linux 推薦）
systemctl --user enable --now smsbridge.service
systemctl --user enable --now smsbridge-bridge.service

# 5. （或者臨時跑）手動啟動
uv run smsbridge start                         # 一個終端
bash scripts/bridge.sh --watch                 # 另一個終端

# 6. 安裝 Android App
cd android && ./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## 詳細安裝

### 3.1 電腦端（Server）

#### 3.1.1 安裝 uv（套件管理器）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# 重啟 shell 或 source ~/.bashrc
```

#### 3.1.2 複製倉庫與安裝依賴

```bash
git clone https://github.com/davncl-star/smsbridge.git
cd smsbridge
uv sync              # 建立虛擬環境並安裝依賴
```

#### 3.1.3 配置 Telegram

1. 在 [@BotFather](https://t.me/botfather) 建立 Bot，取得 Token
2. 將 Token 發給 Bot，然後呼叫 `getUpdates` 取得你的 Chat ID：

```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
# 找到 "chat": {"id": 123456789, ...}
```

3. 複製配置範本並填入：

```bash
cp .env.example .env
nano .env
```

最低配置：

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_IDS=123456789
```

#### 3.1.4 配置 ADB

確認 `adb` 在 PATH 中，或設定 `ANDROID_HOME`：

```bash
export ANDROID_HOME=/home/user/Android/Sdk
# 加入 ~/.bashrc 持久化
```

測試 USB 連線：

```bash
adb devices
# 應顯示：<device_serial>  device
```

#### 3.1.5 （可選）啟用 systemd 自動啟動

Linux 下用 systemd user unit 保持服務開機啟動、崩潰自動重啟：

```bash
# 啟動並啟用
systemctl --user enable --now smsbridge.service
systemctl --user enable --now smsbridge-bridge.service

# 查看狀態
systemctl --user status smsbridge.service
systemctl --user status smsbridge-bridge.service

# 查看日誌
journalctl --user -u smsbridge.service -f
journalctl --user -u smsbridge-bridge.service -f
```

---

### 3.2 手機端（Android App）

#### 3.2.1 建置 APK

```bash
cd android
# 確保 gradle-wrapper.jar 存在（若首次 clone 需重新生成）
# gradle wrapper --gradle-version 8.9

# 確認 local.properties 存在
echo "sdk.dir=/home/$(whoami)/Android/Sdk" > local.properties

# 建置 debug APK
./gradlew assembleDebug
```

APK 產出路徑：`android/app/build/outputs/apk/debug/app-debug.apk`

#### 3.2.2 安裝到手機

```bash
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

#### 3.2.3 手機端設定

1. **啟用 USB 調試**：設定 → 關於手機 → 版本號連點 7 次 → 返回設定 → 開發者選項 → USB 調試
2. **授權 ADB**：插 USB → 手機上點「允許 USB 調試」
3. **鎖定後台**：（MIUI / EMUI 等）長按 SMSBridge App → 鎖定圖示 / 加入白名單，避免被殺後台
4. **開啟所有權限**：設定 → 應用 → SMSBridge → 權限 → 允許「通知」「接收短信」「讀取手機狀態」

---

## 啟動與驗證

### 完整啟動順序（建議）

```bash
# 終端 A：啟動 Server
cd ~/Documents/program/smsbridge
uv run smsbridge start

# 終端 B：建立 ADB 橋接（--watch: 自動監聽 USB 插拔）
bash scripts/bridge.sh --watch

# 手機上：打開 SMSBridge App → 點「啟動服務」
# 狀態指示燈應變為綠色「已連接」
```

### 驗證管道

```bash
# 檢查 server 健康狀態
curl http://127.0.0.1:8580/health
# 預期回應：{"version":"0.6.0","uptime_seconds":123}

# 檢查過濾器與聚合狀態
uv run smsbridge status

# 檢查系統日誌
journalctl --user -u smsbridge.service -n 20
```

### 驗收測試

1. 向手機發送一條簡訊 → Telegram 應在 5 秒內收到格式化推送 ✅
2. 拔掉 USB → 通知欄變為「未連接」→ 手機端 Log Panel 記錄斷線事件 ✅
3. 重新插回 USB → 自動重連（systemd） → 通知欄變回「已連接」 ✅
4. 拔掉 USB 超過 2 分鐘 → Telegram 收到「設備離線告警」 ✅

---

## 排錯 FAQ

### Q: `adb` 找不到手機

```bash
adb devices
# 若輸出空，檢查：
# 1. 手機上 USB 調試已啟用？
# 2. 手機上已授權此電腦？
# 3. 換一根 USB 線（部分充電線不支援數據傳輸）
```

### Q: `adb reverse` 失敗

```
error: more than one device
```
一次只能插一部手機，或指定序列號：
```bash
adb -s <serial> reverse tcp:8580 tcp:8580
```

### Q: 手機重啟後 App 不自動啟動

- Android 沒有標準的開機廣播恢復前台服務。需要 SMS 發送時，系統會喚醒 `SmsReceiver`，`ForwardService` 會自動重啟
- 若 App 被系統殺掉，手動點開 SMSBridge 即可恢復

### Q: MIUI / EMUI 頻繁殺後台

- 長按 SMSBridge App icon → 彈出選單 → 鎖定圖示（🔒）
- 設定 → 應用 → SMSBridge → 省電策略 → 設為「無限制」
- 設定 → 應用 → 授權管理 → 自動啟動 → 開啟 SMSBridge

### Q: Telegram 沒有收到短信

```bash
# 檢查 server 日誌
cat logs/smsbridge.log | tail -20

# 確認 Token 是否有效
curl https://api.telegram.org/bot<TOKEN>/getMe

# 確認 Chat ID 是否正確
uv run smsbridge config
```

### Q: `gradle-wrapper.jar` 缺失

```bash
cd android
gradle wrapper --gradle-version 8.9
```
（jar 檔不入 git，首次 clone 後需重新生成）

### Q: 如何更新到最新版本？

```bash
cd ~/Documents/program/smsbridge
git pull origin main        # 拉取最新程式碼
uv sync                      # 更新 Python 依賴
cd android && ./gradlew assembleDebug  # 重建 Android App
adb install -r app/build/outputs/apk/debug/app-debug.apk  # 安裝到手機
```

### Q: systemd 服務無法啟動？

```bash
systemctl --user status smsbridge.service
journalctl --user -u smsbridge.service -n 50 --no-pager
```

常見原因：
- `.env` 檔案格式錯誤（檢查 Token 和 Chat ID）
- Python 虛擬環境路徑不正確
- ADB 未安裝或路徑不正確

---

## 相關文件

- [`CONFIGURATION.md`](./CONFIGURATION.md) — 所有配置項完整參考
- [`EXECUTION_PLAN.md`](./EXECUTION_PLAN.md) — 開發路線圖與狀態
- [`CHANGES.md`](./CHANGES.md) — 版本變更日誌
