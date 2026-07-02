# Android 端 · SMSBridge

> **Phase 2 已完成**。代碼骨架就位，可直接在 Android Studio 中打開構建。

## 目錄結構

```
android/
├── app/
│   ├── src/main/
│   │   ├── java/com/example/smsbridge/
│   │   │   ├── MainActivity.kt      # Compose UI + 權限申請 + 連接狀態
│   │   │   ├── SmsReceiver.kt       # SMS_RECEIVED 廣播接收
│   │   │   ├── ForwardService.kt    # ForegroundService + 心跳 + 重試隊列
│   │   │   ├── SmsData.kt           # 數據模型 (JSON/序列化)
│   │   │   └── HttpClient.kt        # OkHttp 封裝
│   │   ├── AndroidManifest.xml       # 權限 + 組件聲明
│   │   └── res/values/strings.xml
│   ├── build.gradle.kts              # 模塊構建
│   └── proguard-rules.pro
├── build.gradle.kts                  # 根構建
├── settings.gradle.kts               # 項目設定
├── gradle.properties
└── gradle/
    ├── libs.versions.toml            # Version Catalog
    └── wrapper/gradle-wrapper.properties
```

## Phase 2 已交付

| 文件 | 職責 | 要點 |
|------|------|------|
| `SmsData.kt` | 短信數據模型 | 匹配 Phase 1 `IncomingSMS`；`org.json` 序列化；`fromSmsMessages` 工廠 |
| `HttpClient.kt` | HTTP 客戶端 | OkHttp 非阻塞回調；`postSms` + `checkHealth` |
| `SmsReceiver.kt` | 廣播接收器 | 解析 `pdus`；`subscriptionId` 判 SIM 槽；啟動 ForwardService |
| `ForwardService.kt` | 後台服務 | 前台通知；設備 ID UUID 持久化；15s 心跳；重試隊列（3 次 / 10 條） |
| `MainActivity.kt` | 用戶界面 | Material3 Compose；權限申請；🟢/🔴 連接點 |

## 打開項目

1. **Android Studio** → File → Open → 選擇 `android/` 目錄
2. 等待 Gradle sync 完成（第一次會自動下載 Gradle wrapper + 依賴）
3. Run → 選擇真機或模擬器

> 注意：模擬器不支持 SMS 接收！必須使用 **Android 真機** 才能測試。

## 與電腦端的接口約定

- `POST http://127.0.0.1:8580/api/sms` — 推送短信（JSON body）
- `GET  http://127.0.0.1:8580/health` — 心跳檢測（15s 間隔）
- 數據線連接後執行 `adb reverse tcp:8580 tcp:8580`

## 下一步（待真機聯調）

- [ ] 真機安裝 APK → 授予權限 → 啟動服務
- [ ] USB 連接電腦 → `adb reverse tcp:8580 tcp:8580` → 啟動 Phase 1 服務器
- [ ] 發送真實短信 → 驗證 Telegram 收到
- [ ] 測試斷線重連、雙卡 SIM、Android 13+ 通知

## Min SDK

**API 26 (Android 8.0)** — 覆蓋絕大多數活躍設備。最低 SDK 保證 `Telephony.Sms.Intents` API 可用。
