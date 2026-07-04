# SMSBridge · 功能實現指南

> 14 個提案的詳細實現方式。每個文檔包含：動機、架構、實作步驟、檔案變更、依賴與風險。

## 快速索引

| # | 功能 | 難度 | 主要影響域 | 文檔 |
|---|------|------|-----------|------|
| 1 | WiFi ADB 模式 | ★☆☆ | server + scripts | [→](01-wifi-adb.md) |
| 2 | Telegram Bot 雙向控制 | ★☆☆ | server/telegram.py | [→](02-telegram-bot-control.md) |
| 3 | 系統托盤圖標 | ★★☆ | server/tray.py (新) | [→](03-system-tray.md) |
| 4 | 來電提醒 | ★☆☆ | android/ | [→](04-call-alert.md) |
| 5 | Docker 部署 | ★☆☆ | infra | [→](05-docker.md) |
| 6 | 短信歷史 + Web 面板 | ★★★ | server/db.py + web/ (新) | [→](06-web-panel.md) |
| 7 | TLS 加密傳輸 | ★★☆ | server + android | [→](07-tls-encryption.md) |
| 8 | Telegram 管理過濾規則 | ★★☆ | server + 依賴 #2+#6 | [→](08-telegram-filter-mgmt.md) |
| 9 | 監控端點 | ★☆☆ | server/metrics.py (新) | [→](09-metrics.md) |
| 10 | 多通道推送 | ★★☆ | server/channels/ (新) | [→](10-multi-channel.md) |
| 11 | 桌面 GUI 客戶端 | ★★★★ | 跨平台新項目 | [→](11-desktop-gui.md) |
| 12 | iOS 支援 | ★★★★★ | 探討替代方案 | [→](12-ios-support.md) |
| 13 | 短信自動回覆引擎 | ★★★☆ | server + android | [→](13-auto-reply.md) |
| 14 | Home Assistant 集成 | ★★☆ | server/webhook.py (新) | [→](14-home-assistant.md) |

## 優先級矩陣

```
高價值 ────┬── WiFi ADB ── Bot 控制 ── 系統托盤 ── 來電提醒
           │     (1)         (2)          (3)         (4)
低投入 ────┼── Docker ── 監控 ── HA 集成
           │     (5)      (9)     (14)
           │
           ├── 加密 ── 多通道 ── Bot 管理規則
           │    (7)     (10)        (8)
高投入 ────┼── Web 面板 ── 自動回覆
           │     (6)        (13)
           │
           └── 桌面 GUI ── iOS
                (11)       (12)
```

> 推薦先從左上角（高價值 + 低投入）開始。
