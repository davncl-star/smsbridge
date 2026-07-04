# SMSBridge · 功能構思與路線

> 基於 Phase 1–3 完成後的延伸方向。分爲**短線**（可單獨快速落地）、**中線**（1–2 併發模塊）和**長線**（需較多基礎設施）。
>
> 📄 每個功能的詳細實現方式見 [`docs/features/`](features/index.md) 目錄。

---

## 短線（Low-hanging fruit）

### 1. WiFi ADB 模式（告別 USB）

**動機**：當前必須插 USB + `adb reverse`，WiFi 下可直接運行，方便日常定點使用。

📄 [實現方式](features/01-wifi-adb.md)

**做法**：
- 手機端與電腦端處於同一局域網即可
- 電腦端啟動 mDNS 服務（`zeroconf` 庫），手機端自動發現
- 或手機端掃碼（QR Code）獲取電腦端 IP:Port

**難度**：★☆☆  
**依賴**：Python `zeroconf` 庫，Android `nsd` API  
**備註**：可選保留 ADB 做 fallback

---

### 2. Telegram Bot 雙向控制

**動機**：不需要開電腦終端也能管理 SMSBridge——查狀態、調配置、重啟服務。

**做法**：
- 處理 Telegram Bot 的 `/status`、`/stats`、`/restart` 命令
- 利用 `getUpdates` long polling（或 webhook）接收指令
- 回應：當前的轉發統計（今日/累計）、過濾命中數、服務器運行時間

**難度**：★☆☆  
**依賴**：`server/telegram.py` 增加 `receive_update()` 處理  
**備註**：與 `openclaw` agent 共用同一個 Bot 時需要小心 offset 管理

---

### 3. 系統托盤（System Tray）圖標

**動機**：Windows 用戶不想一直開着終端窗口，托盤圖標可以一鍵啓停 + 查看狀態。

**做法**：
- 用 `pystray` 或 `rumps` 加入系統托盤
- 右鍵菜單：啟動/停止、打開 Web 面板、退出
- 托盤圖標顯示連接狀態（綠/紅）

**難度**：★★☆  
**依賴**：`pystray`（Windows + macOS）  
**備註**：僅 Windows/macOS 有用，Linux 用戶可用 systemd

---

### 4. 主叫提醒（來電通知）

**動機**：除了短信，來電也是重要信息，特別是雙卡用戶想知道哪個號碼來電。

**做法**：
- Android 端監聽 `PHONE_STATE` 廣播（權限已申請 `READ_PHONE_STATE`）
- 來電時 POST 到電腦端，格式類似 IncomingSMS 但 `body` 置為 `[來電]`
- 服務器端轉發到 Telegram，標題改為 📞

**難度**：★☆☆  
**依賴**：Phase 2 Android 代碼擴展  
**備註**：可選開關（`forward_calls`）

---

### 5. Docker 部署

**動機**：服務器端一鍵部署，適合 NAS / 服務器常駐運行。

**做法**：
- 撰寫 `Dockerfile` + `docker-compose.yml`
- `.env` 掛載爲 volume
- 可選集成 Watchtower 自動更新

**難度**：★☆☆  
**依賴**：無  
**備註**：Windows 用戶也可用 Docker Desktop

---

## 中線（Medium-term）

### 6. 短信歷史記錄 + Web 面板

**動機**：當前短信轉發後無痕跡，想看歷史轉發或搜索某條短信需要翻 Telegram。

**做法**：
- 服務器端集成 SQLite（`aiosqlite` 或 `sqlalchemy` + `aiosqlite`）
- 記錄每條轉發短信：時間、發件人、號碼、正文、過濾結果、轉發狀態
- 嵌入一個小型 FastAPI 靜態文件 + HTMX 或 Jinja2 的 Web 面板
- 功能：搜索、按日期過濾、查看被攔截的短信

**難度**：★★★  
**依賴**：`aiosqlite`、前端（純 HTML/JS 或 HTMX）  
**備註**：Web 面板可複用於管理配置、查看統計

---

### 7. 加密傳輸（TLS）

**動機**：短信內容在本地網絡明文傳輸，部分場景（咖啡廳 WiFi、宿舍 LAN）有隱私風險。

**做法**：
- 電腦端生成自簽名證書（或 Let's Encrypt）
- FastAPI 啓用 HTTPS
- Android 端 OkHttp 信任自簽名證書 / CA

**難度**：★★☆  
**依賴**：`cryptography` 庫  
**備註**：默認關閉，可選開啓

---

### 8. 發送者白名單 / 黑名單（Telegram 管理）

**動機**：不用改 `.env` 重啓服務器即可動態管理過濾規則。

**做法**：
- 過濾規則從內存移至 SQLite
- Bot 命令 `/block +86138xxxx`、`/unblock`、`/whitelist`
- 也可以實現 `/allow 關鍵詞` 等
- 重啓時從數據庫加載

**難度**：★★☆  
**依賴**：短線 #2（Telegram Bot 控制）+ 中線 #6（SQLite）  
**備註**：先有 SQLite 存儲後自然可以加上

---

### 9. 統計與健康監控端點

**動機**：想知道 SMSBridge 跑了多久、轉發了多少短信、過濾了多少垃圾。

**做法**：
- `server/metrics.py` —— 簡單的計數器（轉發成功/失敗/過濾/聚合）
- 暴露 `GET /metrics` 端點
- 可被 Prometheus 抓取（`prometheus_client` 庫）或簡單 JSON

**難度**：★☆☆  
**依賴**：無  
**備註**：可選 `prometheus_client` 或自定義 Counter

---

### 10. 多 Bot / 多通道推送

**動機**：同時推送多個 Telegram Bot 或其他通道（ServerChan、PushDeer、Bark）。

**做法**：
- 抽象 `forwarder` 接口，每個通道實現 `async def send(text, settings): ...`
- 配置支持 `channels: [telegram, serverchan]`
- 現有 `send_sms` / `send_text` 改爲遍歷所有已配置通道

**難度**：★★☆  
**依賴**：無  
**備註**：push 類服務依賴外網，ADB reverse + USB 不影響

---

## 長線（Longer-term / Stretch）

### 11. 桌面 GUI 客戶端

**動機**：對非技術用户更友好的體驗，替代終端 + 瀏覽器。

**做法**：
- Tauri（Rust + WebView）或 Electron
- 一體化：內置 FastAPI 服務器、ADB 管理、系統托盤
- macOS / Windows 原生安裝包

**難度**：★★★★  
**備註**：重投入，建議 Phase 4 後再做

---

### 12. iOS / iPhone 支持

**動機**：iOS 限制 SMS 監聽權限，無法像 Android 一樣實時廣播。但有替代方案。

**替代方案**：
- iCloud 同步方案：讀取 iMessage 數據庫（需越獄 / 不可靠）
- 或反向：用 Telegram Bot 作爲中轉，iOS 用戶直接用 Bot 接收
- 或僅提供「發送短信」功能（通過運營商 API / IoT SIM）

**難度**：★★★★★  
**備註**：iOS 上不可能做實時 SMS 監聽；建議聚焦 Android + 多通道推送

---

### 13. 短信自動回覆引擎

**動機**：收到特定短信（如「驗證碼」）時自動回覆或轉發給指定人。

**做法**：
- 配置回覆規則：當正文匹配關鍵詞 / 正則時，調用第三方 API 或發送短信
- 回覆短信需 Android 端發送（`SmsManager.sendTextMessage`），權限敏感
- 也可僅做 Telegram 按鈕回覆（Inline Keyboard）

**難度**：★★★☆  
**備註**：發送短信權限在 Android 上敏感，需 `SEND_SMS` 權限

---

### 14. Home Assistant 集成

**動機**：短信觸發智能家居動作（「門禁來訪」→ 開門）。

**做法**：
- 電腦端支持 Webhook 轉發
- 收到特定短信（如關鍵詞匹配）時 POST 到 Home Assistant Webhook
- 或輸出到 MQTT

**難度**：★★☆  
**備註**：需要 Home Assistant 環境

---

## 優先級建議

```
立即有價值 ────────→ 長期投入
    │
 WiFi ADB (#1)        Telegram 控制 (#2)     系統托盤 (#3)
    來電提醒 (#4)        Docker (#5)
    │                       │
    ▼                       ▼
 歷史 + Web (#6)         Bot 管理規則 (#8)
   監控 (#9)              多通道 (#10)
    │                       │
    ▼                       ▼
  加密 (#7)             桌面 GUI (#11)
                        HomeAssistant (#14)
```

**我的推薦**（最短投入產出比）：

1. **來電提醒**（半小時改 Android 代碼）
2. **系統托盤**（Python `pystray` 配置）
3. **WiFi ADB**（不用插線的體驗質變）
4. **Web 面板 + 歷史**（日後調試/回溯有用）

要不要先選一個實作？
