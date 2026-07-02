# SMSBridge

> 手機短信 → 本地服務器 → Telegram Bot。USB 連線 + ADB reverse，零雲依賴。

![Phase](https://img.shields.io/badge/phase-2%20%2F%204-green)
![Version](https://img.shields.io/badge/version-0.2.0-lightgrey)
![tests](https://img.shields.io/badge/tests-11%2F11-green)

---

## 架構

```
┌──────────────┐  POST /api/sms   ┌──────────────────┐  HTTPS  ┌──────────────┐
│ Android 手機 │ ───────────────→ │  電腦端本地服務器  │ ──────→ │ Telegram API │
│  (SMS 監聽)  │  (adb reverse)   │  (FastAPI)       │         │   (Bot)      │
└──────────────┘                 └──────────────────┘         └──────────────┘
```

完整計劃見 [`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md)。

---

## Phase 狀態

| Phase | 內容 | 狀態 |
|-------|------|------|
| **1** | 電腦端 Telegram 轉發（FastAPI） | 🟢 **已就位** |
| **2** | Android 端 SMS 監聽（Kotlin） | 🟢 **已就位**（真機驗證通過） |
| 3 | ADB 橋接與連接管理 | ⚪ 待開工 |
| 4 | 集成測試與發布 | ⚪ 待開工 |

---

## 快速開始

### Phase 1 — 電腦端

```bash
cd smsbridge
uv sync                         # 安裝依賴
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS
```

編輯 `.env`，填入 Telegram Bot Token 和 Chat ID：

```dotenv
TELEGRAM_BOT_TOKEN=<@BotFather 給的 Token>
TELEGRAM_CHAT_IDS=<你的 Chat ID>
```

啟動：

```bash
uv run smsbridge start
```

驗證：訪問 `http://127.0.0.1:8580/health` 應返回 200。

### Phase 2 — Android 端

```bash
cd smsbridge/android
gradlew assembleDebug               # 構建 APK
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb reverse tcp:8580 tcp:8580       # 端口橋接
```

在手機上：
1. 打開 SMSBridge App → 授予簡訊 / 電話 / 通知權限
2. 點 **「啟動服務」** → 等待約 15 秒 → 狀態變 🟢 已連接
3. 發送一條真實手機短信 → Telegram 收到推送

---

## 目錄結構

```
smsbridge/
├── server/                        # Phase 1 · 電腦端 FastAPI
│   ├── main.py                    # 入口：POST /api/sms、GET /health
│   ├── config.py                  # .env 加載（pydantic-settings）
│   ├── telegram.py                # Bot API 封裝（直接 HTTP）
│   ├── models.py                  # Pydantic 數據模型
│   └── cli.py                     # smsbridge start/status/config
│
├── android/                       # Phase 2 · 手機端 Kotlin
│   ├── app/src/main/java/com/example/smsbridge/
│   │   ├── MainActivity.kt        # Compose UI + 權限申請 + 連接狀態
│   │   ├── SmsReceiver.kt         # SMS_RECEIVED 廣播監聽
│   │   ├── ForwardService.kt      # 前台服務 + 心跳(15s) + 重試隊列
│   │   ├── SmsData.kt             # 數據模型（對齊 server/models.py）
│   │   └── HttpClient.kt          # OkHttp 封裝
│   ├── gradle/libs.versions.toml  # Version Catalog
│   └── ...                        # 完整 Gradle 構建配置
│
├── docs/
│   ├── EXECUTION_PLAN.md          # 四階段執行路線圖
│   └── index.md                   # 文檔索引
│
├── scripts/                       # Phase 3 預留
├── tests/                         # Python 測試（11 項通過）
├── pyproject.toml                 # uv 包管理
├── .env.example                   # 環境變量範本
├── CHANGES.md                     # 變更日誌
└── README.md
```

---

## CLI 子命令

```bash
uv run smsbridge start      # 啟動服務器
uv run smsbridge status     # 查看配置/日志狀態
uv run smsbridge config     # 打印當前生效配置
```

---

## 測試

```bash
cd smsbridge
uv run pytest               # 11 項測試，覆蓋核心端點 + 配置解析 + 降級策略
```

---

## 變更日誌

[CHANGES.md](CHANGES.md) — v0.1.0（Phase 1）→ v0.2.0（Phase 2）

---

## 後續路線

- **Phase 3**：`scripts/bridge.bat` + `bridge.sh`，自動 `adb reverse` + USB 熱插拔監聽
- **Phase 4**：打包（APK / PyInstaller exe）、補 `INSTALL.md` / `CONFIGURATION.md`、GitHub release

可選增強（V2）：內容過濾、消息聚合、多用戶推送、TLS 加密、WiFi 直連、Web 面板。

---

## 風險提示

- **手機端殺後台**：部分廠商 ROM 會強殺 Foreground Service，需引導用戶加入白名單
- **Android 13+ 通知權限**：必須動態申請 `POST_NOTIFICATIONS`
- **Bot Token 保密**：`.env` 已入 `.gitignore`，勿提交

---

<sub>v0.2.0 · 2026-07-02 · 全鏈路測試通過 ✅</sub>
