# 12. iOS 支援

> iOS 限制 SMS 監聽權限，無法像 Android 一樣實時廣播。此文檔探討可行的替代方案。

---

## 核心限制

Apple 不允許第三方 App 監聽 `iMessage` / `SMS` 的系統廣播。即使越獄也無法可靠實現。

## 替代方案

### 方案 A：iCloud 同步（不可靠）

1. iPhone 和 Mac 登錄同一 iCloud 帳號
2. Mac 端 iMessage 同步短信
3. Mac 端運行 SMSBridge 監聽 iMessage 數據庫

**問題**：
- macOS 限制第三方讀取 iMessage 數據庫（沙箱）
- 需用戶手動授予「完全磁盤訪問權限」
- Apple 可能隨時修改數據庫格式

### 方案 B：Telegram Bot 直接接收（推薦）

如果用戶有 iPhone 和 Android 兩臺手機：

1. Android 端繼續用 SMSBridge 轉發
2. iPhone 用戶通過 Telegram 客戶端接收通知
3. 同一 Bot，無需額外開發

### 方案 C：eSIM / 虛擬號碼

1. 使用 Google Voice / 其他虛擬號碼服務
2. 虛擬號碼收到短信 → Webhook 通知 → 轉發到 Telegram
3. 缺點：國內不可用

### 方案 D：SMS 轉 iMessage 轉發（iOS 內置）

1. iOS 設置 > 信息 > 短信轉發 → 勾選已連接的 Mac
2. Mac 端運行腳本監聽 Messages.app 數據庫

**同方案 A 的限制**。

## 結論

**不建議實作 iOS 支援**。投入產出比過低：
- 無可靠技術方案
- 需要 macOS 生態綁定
- 用戶量極小

**推薦策略**：
- 專注 Android 端
- 多通道推送（#10）讓 iOS 用戶通過 Bark / Telegram 接收

## 檔案變更

無。僅保留此文檔作為設計決策記錄。

## 驗收標準

N/A — 不實作。
