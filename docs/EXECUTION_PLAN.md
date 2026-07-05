# SMSBridge · 執行計劃

> 四階段迭代路線圖。Phase 1（電腦端）已完成骨架搭建，Phase 2–4 依次推進。

---

## 狀態總覽

```
Phase 1 ─── 電腦端 Telegram 轉發         🟢 已就位（骨架可運行，27 項測試通過）
Phase 2 ─── 手機端 SMS 監聽              🟢 已就位（MI 8 真機驗證通過）
Phase 3 ─── ADB 橋接與連接管理           🟢 已就位（三平台脚本 + systemd 自動監聽）
Phase 4 ─── CLI 管理工具鏈               🟢 已就位（filter + agg 子命令 + status 增強）
```

---

## Phase 1 · 電腦端 Telegram 轉發

**狀態**：🟢 **已就位** — 骨架可運行，27 項測試通過。

### 已交付

| 組件 | 文件 | 說明 |
|------|------|------|
| FastAPI 入口 | `server/main.py` | GET `/health`, POST `/api/sms`，lifespan 延遲加載配置 |
| Telegram 轉發 | `server/telegram.py` | 直接 HTTP，無 python-telegram-bot 依賴；HTML 模式格式化 |
| 配置加載 | `server/config.py` | pydantic-settings 讀取 `.env`；chat_ids 支持逗號分隔/JSON/單值 |
| 數據模型 | `server/models.py` | IncomingSMS、ForwardResult、HealthResponse |
| CLI 子命令 | `server/cli.py` | `smsbridge start/status/config/bridge/filter/agg` |
| 配置模板 | `.env.example` | Telegram Bot Token + Chat ID + 監聽地址 |
| 內容過濾 | `server/filter_engine.py` | 關鍵詞/正則黑名單，可透過 CLI 管理 |
| 消息聚合 | `server/aggregator.py` | 同一號碼 N 秒窗口內合併，可透過 CLI 配置 |
| 日誌滾動 | `server/main.py` | RotatingFileHandler（5MB, 3 backup） |
| 煙霧測試 | `tests/` | 27 用例，覆蓋健康檢查、轉發成功/失敗、配置解析、過濾引擎、聚合、無 token 降級 |

### 可選增強（Phase 1.5 — 若有餘力）

- [ ] 補 `INSTALL.md`（pip / uv / PyInstaller 安裝說明）
- [ ] 補 `CONFIGURATION.md`（配置項詳解）
- [ ] 消息格式化支持自定義模板
- [ ] 多用戶推送（多個 Chat ID 已完成，需 CLI 管理）

---

## Phase 2 · 手機端 SMS 監聽（Android · Kotlin）

**狀態**：🟢 **代碼骨架已完成，真機聯調通過**

### 已交付

| 序號 | 任務 | 狀態 |
|------|------|------|
| 2.1 | Android Studio scaffold：Gradle KTS + Version Catalog + Compose | ✅ |
| 2.2 | `AndroidManifest.xml`：權限 + Receiver + Service 聲明 | ✅ |
| 2.3 | `SmsData.kt`：數據模型，與 Phase 1 的 `IncomingSMS` 對齊 | ✅ |
| 2.4 | `HttpClient.kt`：OkHttp 封裝，POST + GET /health + 回調 | ✅ |
| 2.5 | `SmsReceiver.kt`：廣播監聽，解析 `pdus`，`subscriptionId` 判 SIM | ✅ |
| 2.6 | `ForwardService.kt`：前台服務 + 心跳 + 重試隊列（3 次 / 10 條） | ✅ |
| 2.7 | `MainActivity.kt`：Compose UI + 權限申請 + 連接狀態指示燈 + Log Panel | ✅ |
| 2.8 | 真機 USB 聯調：ADB install → 發送真實短信 → 驗證 Telegram 收到 | ✅ |
| 2.9 | Notification bar 狀態同步：斷線重連後即時更新文字 | ✅ |

### 接口合約（與 Phase 1 對接）

```
POST http://127.0.0.1:8580/api/sms
Content-Type: application/json

{
  "sender": "發件人姓名（通訊錄匹配後）",
  "number": "發件人手機號",
  "body": "短信正文",
  "received_at": "2026-06-30T17:00:00",
  "sim_slot": 0,
  "device_id": "設備唯一標識"
}
```

### 驗收標準

- 手機收到短信後 **< 5 秒** 內 Telegram 收到格式化推送 ✅
- 雙卡手機正確標註 SIM 槽 ✅
- 無 WiFi / 無 Internet（僅 USB+ADB）場景下正常工作 ✅
- App 退出後系統重啟可恢復廣播監聽 ✅

---

## Phase 3 · ADB 橋接與連接管理

**狀態**：🟢 **已就位** — 三平台脚本齊全，CLI 集成完成，systemd 自動監聽

### 已交付

| 文件 | 平台 | 功能 |
|------|------|------|
| `scripts/bridge.bat` | Windows batch | 一鍵 reverse；含錯誤提示 |
| `scripts/bridge.sh` | Linux/macOS | 一鍵 reverse；含 --watch 模式 |
| `scripts/bridge.ps1` | Windows PowerShell | 一鍵 reverse + --watch 熱插拔模式 |
| `smsbridge bridge` CLI | 跨平台 | 調用平台對應脚本，轉發剩餘參數 |
| `smsbridge-bridge.service` | systemd user unit | ADB reverse 熱插拔守護（PartOf 關聯），開機自動啟動，斷線 5 秒後自動重連 |
| `conftest.py` | pytest | 隔離 .env 避免測試依賴用戶本地配置 |

### server 端心跳告警（P0-2）

| 功能 | 說明 | 狀態 |
|------|------|------|
| 手機心跳逾時監控 | server 端每 30 秒檢查最後心跳時間，超過 `heartbeat_timeout` 秒（預設 120）未收到心跳則發送 Telegram 告警 | ✅ |
| 告警恢復 | 心跳恢復後自動清除告警狀態 | ✅ |

### 使用方式

**快速橋接（一次性）：**
```bash
uv run smsbridge bridge
# 或
scripts/bridge.sh / scripts/bridge.ps1
```

**熱插拔監聽（保持 reverse 存活）：**
```bash
uv run smsbridge bridge --watch
# 或 systemd 自動啟動
systemctl --user enable --now smsbridge-bridge.service
```

### 驗收標準

- 插 USB → `adb reverse` 成功 → 手機端 App 狀態變綠 ✅
- 拔 USB → 手機端心跳失敗 → 狀態變紅，本地排隊重試 ✅
- 重新插 USB → systemd 自動重連 ✅
- 手機端長時間無心跳 → Telegram 推送告警 ✅

---

## Phase 4 · 集成測試與發布

**狀態**：🟢 **已就位** — CLI 管理工具鏈完成

### 已交付

| 序號 | 功能 | 文件 | 狀態 |
|------|------|------|------|
| 4.1 | 內容過濾 CLI | `smsbridge filter list/add/remove/regex-add/regex-remove` | ✅ |
| 4.2 | 消息聚合 CLI | `smsbridge agg status/set` | ✅ |
| 4.3 | status 命令增強 | 同時顯示過濾器和聚合器運行狀態 | ✅ |
| 4.4 | 端到端測試腳本 | pytest 27 項全數通過 | ✅ |
| 4.5 | Android signed APK | debug APK 可正常安裝 | ✅ |
| 4.6 | 日誌滾動 | RotatingFileHandler（5MB, 3 backup） | ✅ |

### 待辦

- [ ] 撰寫 `INSTALL.md`：環境依賴 + 安裝步驟 + 排錯 FAQ
- [ ] 撰寫 `CONFIGURATION.md`：配置項完整參考
- [ ] GitHub release 發佈（CHANGES + tag）
- [ ] Android signed APK 打包（release keystore）

---

## 圖表：實際完成 vs 原始 Phase 4 新增內容

```
          原始計劃                       實際完成
    ┌─────────────────────┐      ┌─────────────────────┐
    │ Phase 1 … 骨架      │      │ Phase 1 … 骨架      │
    │ Phase 2 … Android   │      │ Phase 2 … Android   │
    │ Phase 3 … ADB 橋接  │      │ Phase 3 … ADB 橋接  │
    │ Phase 4 … 測試+打包 │      │ Phase 4 … CLI 工具鏈│
    │                     │  →   │ + 過濾/聚合管理     │
    │ EXECUTION_PLAN 也   │      │ + status 增強       │
    │ 同步更新            │      │ + 日誌滾動          │
    │                     │      │ + 心跳告警          │
    └─────────────────────┘      └─────────────────────┘
```

---

## 過往版本

| 版本 | 日期 | 摘要 |
|------|------|------|
| v0.6.0 | 2026-07-05 | Phase 4 CLI 工具鏈：filter + agg 子命令、status 增強 |
| v0.5.1 | 2026-07-05 | Notification bar 狀態同步、App 內 Log Panel |
| v0.5.0 | 2026-07-04 | systemd units + 真機驗證 + MI 8 實測 |
| v0.4.0 | 2026-07-03 | 內容過濾引擎 + 消息聚合器（Phase 1 增強） |
| v0.3.0 | 2026-07-03 | ADB 橋接腳本（Phase 3） |
| v0.2.0 | 2026-07-01 | Android 端代碼骨架（Phase 2） |
| v0.1.0 | 2026-06-30 | Phase 1 骨架就位 |

---

*本文檔隨項目推進持續更新。*
