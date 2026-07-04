# SMSBridge · 文檔索引

| 文檔 | 說明 |
|------|------|
| `EXECUTION_PLAN.md` | 四階段執行路線圖：任務、依賴、驗收標準、發布清單 |
| `ROADMAP.md` | 功能構思總覽 |
| `features/` | 各功能實現方式詳解（14 篇） |
| `../README.md` | 項目根 README：快速開始、目錄結構、架構 |
| `../.env.example` | 環境變量範本 |
| `../config.yaml.example` | YAML 配置範本（V2） |

## 功能實現指南

| # | 功能 | 難度 | 依賴 |
|---|------|------|------|
| [1](features/01-wifi-adb.md) | WiFi ADB 模式 | ★☆☆ | — |
| [2](features/02-telegram-bot-control.md) | Telegram Bot 雙向控制 | ★☆☆ | — |
| [3](features/03-system-tray.md) | 系統托盤圖標 | ★★☆ | pystray |
| [4](features/04-call-alert.md) | 來電提醒 | ★☆☆ | Android |
| [5](features/05-docker.md) | Docker 部署 | ★☆☆ | Docker |
| [6](features/06-web-panel.md) | 短信歷史 + Web 面板 | ★★★ | aiosqlite |
| [7](features/07-tls-encryption.md) | TLS 加密傳輸 | ★★☆ | openssl |
| [8](features/08-telegram-filter-mgmt.md) | Telegram 管理過濾規則 | ★★☆ | #2 + #6 |
| [9](features/09-metrics.md) | 監控端點 | ★☆☆ | — |
| [10](features/10-multi-channel.md) | 多通道推送 | ★★☆ | — |
| [11](features/11-desktop-gui.md) | 桌面 GUI 客戶端 | ★★★★ | Tauri |
| [12](features/12-ios-support.md) | iOS 支援 | ★★★★★ | 不可行 |
| [13](features/13-auto-reply.md) | 短信自動回覆引擎 | ★★★☆ | #13 |
| [14](features/14-home-assistant.md) | Home Assistant 集成 | ★★☆ | #13 可選 |

## 外部文檔

| 文檔 | 說明 |
|------|------|
| `SMSBridge_计划书.md` | 原始項目計劃書（附件） |

## 文檔約定

- 所有文檔以 Markdown 書寫，兼容 GitHub 渲染
- 文檔與代碼保持同步 —— 每次 Phase 交付後更新本文件夾
