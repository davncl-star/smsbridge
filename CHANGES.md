# Changelog

All notable changes to SMSBridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
