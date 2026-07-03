# SMSBridge · 執行計劃

> 四階段迭代路線圖。Phase 1（電腦端）已完成骨架搭建，Phase 2–4 依次推進。

---

## 狀態總覽

```
Phase 1 ─── 電腦端 Telegram 轉發 🌟 已就位（可啟動、可測試）
Phase 2 ─── 手機端 SMS 監聽   🟢 已就位（Mi8 驗證通過）
Phase 3 ─── ADB 橋接與連接管理 🟢 已就位（三平台脚本齊全）
Phase 4 ─── 集成測試與發布    🔲 待開工
```

---

## Phase 1 · 電腦端 Telegram 轉發

**狀態**：🟢 **已就位** — 骨架可運行，11 項測試通過。

### 已交付

| 組件 | 文件 | 說明 |
|------|------|------|
| FastAPI 入口 | `server/main.py` | GET `/health`, POST `/api/sms`，lifespan 延遲加載配置 |
| Telegram 轉發 | `server/telegram.py` | 直接 HTTP，無 python-telegram-bot 依賴；HTML 模式格式化 |
| 配置加載 | `server/config.py` | pydantic-settings 讀取 `.env`；chat_ids 支持逗號分隔/JSON/單值 |
| 數據模型 | `server/models.py` | IncomingSMS、ForwardResult、HealthResponse |
| CLI 子命令 | `server/cli.py` | `smsbridge start/status/config` |
| 配置模板 | `.env.example` | Telegram Bot Token + Chat ID + 監聽地址 |
| 煙霧測試 | `tests/` | 11 用例，覆蓋健康檢查、轉發成功/失敗、配置解析、無 token 降級 |

### 可選增強（Phase 1.5 — 若有餘力）

- [ ] 補 `INSTALL.md`（pip / uv / PyInstaller 安裝說明）
- [ ] 補 `CONFIGURATION.md`（配置項詳解）
- [ ] 消息格式化支持自定義模板
- [ ] 短信內容過濾（關鍵詞/正則黑名單）
- [ ] 消息分組聚合（1 分鐘窗口內同一號碼合併）
- [ ] 多用戶推送（多個 Chat ID 已完成，需 CLI 管理）

---

## Phase 2 · 手機端 SMS 監聽（Android · Kotlin）

**狀態**：🟢 **代碼骨架已完成**，待真機聯調

### 前置條件

- Phase 1 服務器 + Telegram 通路已跑通（用 curl 模擬驗證）
- 開發者有一台 Android 真機（或模擬器）+ USB 數據線
- Android Studio 已安裝

### 任務分解

| 序號 | 任務 | 預計工期 | 狀態 |
|------|------|----------|------|
| 2.1 | Android Studio scaffold：Gradle KTS + Version Catalog + Compose | 0.5 天 | ✅ 完成 |
| 2.2 | `AndroidManifest.xml`：權限 + Receiver + Service 聲明 | 0.5 天 | ✅ 完成 |
| 2.3 | `SmsData.kt`：數據模型，與 Phase 1 的 `IncomingSMS` 對齊 | 1 天 | ✅ 完成 |
| 2.4 | `HttpClient.kt`：OkHttp 封裝，POST + GET /health + 回調 | 1 天 | ✅ 完成 |
| 2.5 | `SmsReceiver.kt`：廣播監聽，解析 `pdus`，`subscriptionId` 判 SIM | 1 天 | ✅ 完成 |
| 2.6 | `ForwardService.kt`：前台服務 + 心跳 + 重試隊列（3 次 / 10 條） | 1 天 | ✅ 完成 |
| 2.7 | `MainActivity.kt`：Compose UI + 權限申請 + 連接狀態指示燈 | 1 天 | ✅ 完成 |
| 2.8 | 真機 USB 聯調：ADB install → 發送真實短信 → 驗證 Telegram 收到 | 0.5 天 | 🔲 需真機 |
| 2.9 | 邊界測試：USB 斷開重連、手機重啟、SIM 卡切換、Android 13+ 通知權限 | 0.5 天 | 🔲 需真機 |

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

- 手機收到短信後 **< 5 秒** 內 Telegram 收到格式化推送
- 雙卡手機正確標註 SIM 槽
- 無 WiFi / 無 Internet（僅 USB+ADB）場景下正常工作
- App 退出後系統重啟可恢復廣播監聽

---

## Phase 3 · ADB 橋接與連接管理

**狀態**：🟢 **已就位** — 三平台脚本齊全，CLI 集成完成

### 已交付

| 文件 | 平台 | 功能 |
|------|------|------|
| `scripts/bridge.bat` | Windows batch | 一鍵 reverse；含錯誤提示 |
| `scripts/bridge.sh` | Linux/macOS | 一鍵 reverse；含 --watch 模式 |
| `scripts/bridge.ps1` | Windows PowerShell | 一鍵 reverse + --watch 熱插拔模式 |
| `smsbridge bridge` CLI | 跨平台 | 調用平台對應脚本，轉發剩餘參數 |
| `conftest.py` | pytest | 隔離 .env 避免測試依賴用戶本地配置 |

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
# 或
scripts/bridge.ps1 -Watch
```

### 驗收標準

- 插 USB → 執行脚本 → `adb reverse` 成功 → 手機端 App 狀態變綠
- 拔 USB → 手機端心跳失敗 → 狀態變紅，本地排隊重試
- 重新插 USB → --watch 模式自動重連

---

## Phase 4 · 集成測試與發布

**狀態**：🔲 待開工（Phase 3 完成後）

### 任務分解

| 序號 | 任務 | 預計工期 |
|------|------|----------|
| 4.1 | 端到端測試腳本：手機發短信 → ADB → 服務器 → Telegram 全鏈路驗證 | 0.5 天 |
| 4.2 | Android signed APK 打包 | 0.5 天 |
| 4.3 | Python 打包：`uv build` → PyInstaller 打包 Windows exe（可選） | 0.5 天 |
| 4.4 | 撰寫 `INSTALL.md`：環境依賴 + 安裝步驟 + 排錯 FAQ | 0.5 天 |
| 4.5 | 撰寫 `CONFIGURATION.md`：配置項完整參考 | 0.5 天 |
| 4.6 | GitHub release 發佈（CHANGES + tag） | 0.5 天 |

### 發布清單

- [ ] 服務器端：`uv build` + PyPI 發布 (optional) / PyInstaller exe
- [ ] Android 端：signed APK（分發至用戶設備）
- [ ] 文檔：README / INSTALL / CONFIGURATION 齊全
- [ ] CHANGES：記錄每個 Phase 的變更日誌
- [ ] git tag：`v0.1.0`（Phase 1）、`v0.2.0`（Phase 2）、依此類推

---

## 依賴關係圖

```
Phase 1 ──────────────────────┐
       │                       │
       ▼                       ▼
Phase 2 ──→ 真機聯調 ──→ Phase 3
                               │
                               ▼
                          Phase 4
```

- Phase 1 → Phase 2：不需要 Phase 1 完全成熟，只要 `/api/sms` 端點可接收請求即可開工
- Phase 2 → Phase 3：App 需在真機上跑通基本收發
- Phase 1 + 2 + 3 → Phase 4：所有組件 ready 後再做集成測試與打包

---

## 風險追蹤

| 風險 | 影響階段 | 觸發條件 | 緩解措施 |
|------|----------|----------|----------|
| 手機端殺後台 | Phase 2 | 廠商 ROM 強殺 ForegroundService | 引導用戶加入白名單 + 鎖住後台 |
| Android 14+ 權限收緊 | Phase 2 | 新 SDK 限制 RECEIVE_SMS | 最低 SDK 26；對應調整 target SDK 行為 |
| ADB reverse 被安全策略阻擋 | Phase 3 | 企業設備 USB 調試禁用 | 提示用戶啟用開發者選項+USB 調試 |
| 多手機衝突 | Phase 3 | 同時插兩臺手機 | device_id 區分；每臺獨立 reverse 端口 |

---

## 變更日誌

| 版本 | 日期 | 摘要 |
|------|------|------|
| v0.1.0 | 2026-06-30 | Phase 1 骨架就位 |
| v0.2.0 | 2026-07-01 | Phase 2 Android 端代碼骨架完成 |
| v0.3.0 | 2026-07-03 | Phase 3 ADB 橋接脚本交付 |

---

*本文檔隨項目推進持續更新。*
