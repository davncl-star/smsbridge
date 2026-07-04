# Changelog

All notable changes to SMSBridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.5.0] — 2026-07-04

### Added — Phase 3 · 真機整合驗證通過

- **systemd user units 部署**：
  - `smsbridge.service` — FastAPI 服務器（自動重啟 + 日誌重定向）
  - `smsbridge-bridge.service` — ADB reverse 熱插拔守護（PartOf 關聯）
  - 兩者皆已 `systemctl --user enable`，開機自動啟動

- **MI 8（Xiaomi）真機端到端測試通過**：ADB reverse 橋接 → 簡訊即時轉發 → Telegram 推送
- **實測記錄**：2026-07-04 15:57 首批兩通「立創商城驗證碼」短信成功送達 @Dav_Reporter_claw_bot
- **ADB 橋接工作流驗證**：`adb reverse tcp:8580 tcp:8580` 一次建立、USB 斷連後需重建
- **手工構建流程確認**：gradle wrapper jar 需重新生成（非 git tracked）+ `local.properties` 指定 SDK 路徑

### Fixed

- **`gradle-wrapper.jar` 缺失**：非 git tracked 文件，首次 clone 需 `gradle wrapper --gradle-version 8.9` 重新生成
- **bridge.sh 無法直接作為 systemd ExecStart**：需透過 `/usr/bin/bash` 間接執行（ExecStart=/usr/bin/bash .../bridge.sh --watch）
- **SDK 路徑未配置**：添加 `local.properties`（`sdk.dir=/home/davnclai/Android/Sdk`），已入 `.gitignore`

---

## [0.4.0] — 2026-07-03

### Added — Phase 1 增強：內容過濾 + 消息聚合

- **`server/filter_engine.py`** — 短信過濾引擎
  - 關鍵詞黑名單（大小寫不敏感）
  - 正則黑名單
  - 可開關（`filter_enabled`）
- **`server/aggregator.py`** — 消息分組聚合
  - 同一 (號碼, SIM) 第一條即時發送，後續 N 秒內合併
  - 合併消息格式：第一條完整信息 + 後續僅列時間+正文
  - 服務器關閉時自動沖刷殘留 buffer
  - `aggregate_window=0` 關閉
- **`server/telegram.py`** — 新增 `send_text()` 函數，支援發送預格式化文本
- **`server/main.py`** — POST /api/sms 流程集成：過濾 → 聚合 → 轉發
- **`server/config.py`** — 新增 `filter_*` 和 `aggregate_window` 配置字段
- **測試** — 新增 `test_filter.py`（7 項） + `test_aggregator.py`（9 項），合計 **27 項通過**

---

## [0.3.0] — 2026-07-03

### Added — Phase 3 · ADB 橋接與連接管理

- **`scripts/bridge.bat`** (Windows batch)：一鍵 `adb reverse`；含錯誤提示
- **`scripts/bridge.sh`** (Linux/macOS)：一鍵 `adb reverse` + `--watch` 熱插拔模式
- **`scripts/bridge.ps1`** (Windows PowerShell)：一鍵 `adb reverse` + `-Watch` 熱插拔模式
- **`smsbridge bridge` CLI 子命令**：跨平台調用 bridge 脚本，轉發剩餘參數
- **`conftest.py`**：測試會話開始時臨時移走 `.env`、結束時還原，確保測試不依賴用戶本地配置

### Improved — 全平台 adb 自動定位

- 三個 bridge 脚本均按 `PATH` → `$ANDROID_HOME` → `$ANDROID_SDK_ROOT` 順序查找 adb
- 錯誤碼語意化：1 (adb 不可用) / 2 (未授權設備) / 4 (reverse 失敗)

### Fixed

- **測試在 `.env` 存在時失敗**：`conftest.py` 隔離 .env 避免污染測試

---

## [0.2.0] — 2026-07-02

### Added — Phase 2 · Android 手機端 SMS 監聽

- **Android 項目 scaffold**：Gradle KTS + Version Catalog + Compose BOM
- **`SmsData.kt`**：數據模型，與 Phase 1 `IncomingSMS` 對齊；支援長短信合併；`subscriptionId` 判別雙 SIM
- **`HttpClient.kt`**：OkHttp 非阻塞封裝，支援 POST `/api/sms` 與 GET `/health` 心跳
- **`SmsReceiver.kt`**：`SMS_RECEIVED` 廣播監聽，解析 `pdus`，注入設備 ID
- **`ForwardService.kt`**：前臺服務；15 秒心跳檢測；重試隊列（最多 3 次，保留 10 條）；UUID 設備 ID 持久化
- **`MainActivity.kt`**：Material3 Compose UI；動態權限申請（SMS / 電話 / 通知）；🟢🟡🔴 連接狀態指示
- **`AndroidManifest.xml`**：權限（RECEIVE_SMS / INTERNET / POST_NOTIFICATIONS）+ 組件聲明 + 明文流量允許

### Fixed

- **Android 10+ HTTP 明文封鎖**：Manifest 添加 `usesCleartextTraffic="true"` 允許本地 `http://127.0.0.1` 通訊
- **`server/cli.py`**：移除未使用 import

---

## [0.1.0] — 2026-06-30

### Added — Phase 1 · 電腦端 Telegram 轉發

- **FastAPI 服務器**：`POST /api/sms` 接收手機端推送；`GET /health` 心跳端點
- **Telegram Bot API 封裝**：直接 HTTP（無需 `python-telegram-bot`）；HTML 模式格式化（含發件人、時間、SIM 槽、設備 ID）
- **配置管理**：`pydantic-settings` 讀取 `.env`；`chat_ids` 支援逗號分隔 / JSON 數組 / 單值
- **CLI 子命令**：`smsbridge start` / `status` / `config`
- **配置模板**：`.env.example`、`config.yaml.example`
- **測試套件**：11 項 pytest，含健康檢查、轉發成功/失敗模擬、無 token 降級、配置解析

---

## 發布追蹤

- 首次正式發布目標：Phase 4 完成後 `v1.0.0`
- 中途里程碑：`v0.1.0`（Phase 1）、`v0.2.0`（Phase 2）
