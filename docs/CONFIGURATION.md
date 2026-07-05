# SMSBridge · 配置參考

> 所有配置選項，依字母排序（忽略大小寫）。  
> 可透過 `.env` 檔案或環境變量設定。

---

## 基本規則

1. **優先順序**：環境變量 > `.env` 檔案
2. **`.env` 位置**：倉庫根目錄（`smsbridge/.env`），不入版本庫
3. **複用範本**：`cp .env.example .env` 開始
4. **數值類型**：`int`, `bool`, `list` 等由 pydantic 自動解析

---

## 配置項總覽

| 變量名 | 必要 | 預設值 | 類型 | 說明 |
|--------|------|--------|------|------|
| `TELEGRAM_BOT_TOKEN` | ✅ 是 | — | `str` | @BotFather 給的 Bot Token |
| `TELEGRAM_CHAT_IDS` | ✅ 是 | — | `list[int]` | 接收轉發的 Telegram Chat ID |
| `SERVER_HOST` | 否 | `127.0.0.1` | `str` | 服務器綁定地址 |
| `SERVER_PORT` | 否 | `8580` | `int` | 服務器綁定端口 |
| `FILTER_ENABLED` | 否 | `True` | `bool` | 啟用內容過濾 |
| `FILTER_KEYWORDS_BLOCK` | 否 | `[]` | `list[str]` | 關鍵詞黑名單 |
| `FILTER_REGEX_BLOCK` | 否 | `[]` | `list[str]` | 正則黑名單 |
| `AGGREGATE_WINDOW` | 否 | `0` | `int` | 消息聚合窗口（秒），0=關閉 |
| `HEARTBEAT_TIMEOUT` | 否 | `120` | `int` | 心跳逾時（秒），≥30 |
| `LOG_LEVEL` | 否 | `INFO` | `str` | 日誌等級 |
| `LOG_FILE` | 否 | `logs/smsbridge.log` | `str` | 日誌檔案路徑 |
| `TELEGRAM_PARSE_MODE` | 否 | `HTML` | `str` | 消息解析模式 |
| `TELEGRAM_DISABLE_PREVIEW` | 否 | `True` | `bool` | 關閉鏈接預覽 |

---

## 配置項詳解

### `TELEGRAM_BOT_TOKEN`

- **格式**：`<數字>:<字串>`（標準 Telegram Bot Token）
- **獲取方式**：[@BotFather](https://t.me/botfather) → `/newbot`
- **驗證**：

```bash
curl https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getMe
# {"ok":true,"result":{"id":12345,"first_name":"..."}}
```

---

### `TELEGRAM_CHAT_IDS`

- **是發送目標的 Telegram 聊天 ID**，支援三種格式：

```ini
# 格式 1：逗號分隔
TELEGRAM_CHAT_IDS=123456789,987654321

# 格式 2：JSON 數組
TELEGRAM_CHAT_IDS=[123456789, 987654321]

# 格式 3：單個數字
TELEGRAM_CHAT_IDS=123456789
```

- **個人 Chat ID**：發送消息給 Bot 後呼叫 getUpdates 取得
- **群組 Chat ID**：以 `-100` 開頭的負數，將 Bot 加入群組後取得

**取得 Chat ID 方法：**

```bash
# 1. 發任意消息給你的 Bot
# 2. 執行：
curl https://api.telegram.org/bot<TOKEN>/getUpdates
# 3. 在回應中找 "chat": {"id": 123456789}
```

---

### `SERVER_HOST` / `SERVER_PORT`

- **注意**：ADB reverse 場景下 host 必須是 `127.0.0.1`（手機透過 USB 反向代理連到電腦的 localhost）
- 若改用 WiFi 模式（進階），host 改為電腦的區域網 IP
- 手機端 `ForwardService.kt` 預設寫死 `http://127.0.0.1:8580`，若變更端口需同步修改 App 端

---

### `FILTER_ENABLED`

- `True`（預設）：啟用過濾引擎
- `False`：跳過所有過濾規則，每條短信都轉發
- 即使啟用，若關鍵詞和正則列表皆為空，等同於關閉

---

### `FILTER_KEYWORDS_BLOCK`

- **功能**：正文包含任一關鍵詞則不轉發（大小寫不敏感）
- **格式**：同上支援逗號分隔、JSON 數組
- **CLI 管理**：

```bash
smsbridge filter list                    # 列出所有關鍵詞
smsbridge filter add 驗證碼              # 添加（即時寫入 .env）
smsbridge filter remove 驗證碼           # 移除（即時寫入 .env）
```

- **範例**：

```ini
FILTER_KEYWORDS_BLOCK=驗證碼,廣告,推銷,spam
```

---

### `FILTER_REGEX_BLOCK`

- **功能**：正文匹配任一一條正則則不轉發
- **CLI 管理**：

```bash
smsbridge filter regex-add "^\d{6}"      # 添加正則
smsbridge filter regex-remove "^\d{6}"   # 移除正則
```

- **範例**：

```ini
FILTER_REGEX_BLOCK=["^\\d{6}$", "驗證碼.*\\d{4}"]
```

> ⚠️ `.env` 中使用 JSON 格式時注意 `\` 轉義。JSON 中 `\d` → 寫成 `\\d`

---

### `AGGREGATE_WINDOW`

- **功能**：同一手機號碼在 N 秒內的多條短信合併為一條 Telegram 消息
- **`0`**（預設）：關閉聚合，每條短信單獨發送
- **`>0`**：聚合窗口秒數

**行為細節：**
- 該號碼的第一條短信立即發送（完整格式）
- 後續 N 秒內的短信入緩衝，僅記錄時間 + 正文
- 窗口結束後緩衝區內若有多條 > 1，發送合併消息
- 若窗口結束時僅累積 1 條（未超額），不重複發送
- 服務器關閉時自動沖刷殘留 buffer

**啟用示例（60 秒窗口）：**

```bash
smsbridge agg set 60
# 或手動編輯 .env：
AGGREGATE_WINDOW=60
```

---

### `HEARTBEAT_TIMEOUT`

- **功能**：手機心跳逾時閾值。手機透過 `GET /health` 每 15 秒發送心跳，Server 端每 30 秒檢查
- **預設**：`120` 秒（2 分鐘無心跳觸發告警）
- **最小值**：`30`
- **逾時行為**：向所有 Chat ID 發送「🚨 SMSBridge 設備離線告警」，含可能原因提示
- **恢復行為**：心跳恢復後自動清除告警狀態，不會重複發送

---

### `LOG_LEVEL`

- 接受標準 Python logging 等級：
  - `DEBUG` — 開發除錯用
  - `INFO`（預設）— 一般運行日誌
  - `WARNING` — 僅記錄警告
  - `ERROR` — 僅記錄錯誤

---

### `LOG_FILE`

- 日誌檔案路徑（支援相對路徑，相對於工作目錄）
- 預設：`logs/smsbridge.log`
- 自動建立目錄
- 採用 `RotatingFileHandler`：每檔 5MB，保留最近 3 份備份
- systemd 模式下日誌同時寫入 `logs/server.systemd.log`

---

### `TELEGRAM_PARSE_MODE`

- `HTML`（預設）— 支援 `<b>`, `<i>`, `<code>`, `<pre>` 等標籤
- `MarkdownV2` — Telegram 擴展 Markdown
- `空字串` — 純文字

---

### `TLS_CERTFILE` / `TLS_KEYFILE`

- **功能**：啟用 HTTPS 支援，用於 WiFi 直連或非本地部署場景
- **預設**：無（HTTP 模式）
- **格式**：PEM 編碼的憑證與私鑰檔案路徑

**產生自簽憑證：**

```bash
bash scripts/gen-certs.sh --host 192.168.1.100
# 產出: server/certs/server.crt + server/certs/server.key
```

**啟動方式：**

```bash
# CLI 參數（優先）
uv run smsbridge start --tls-cert server/certs/server.crt --tls-key server/certs/server.key

# 或在 .env 設定
TLS_CERTFILE=server/certs/server.crt
TLS_KEYFILE=server/certs/server.key
```

> ⚠️ 自簽憑證不被 Android 原生信任。手機端需先安裝憑證至信任 CA。

---

### `TELEGRAM_DISABLE_PREVIEW`

- `True`（預設）— 關閉連結預覽
- `False` — 顯示連結預覽

---

## 完整 .env 範本

```ini
# ── 必要欄位 ──
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_IDS=123456789

# ── 服務器設定（可選） ──
# SERVER_HOST=127.0.0.1
# SERVER_PORT=8580

# ── 內容過濾（可選） ──
# FILTER_ENABLED=True
# FILTER_KEYWORDS_BLOCK=驗證碼,廣告
# FILTER_REGEX_BLOCK=["^\\d{6}$"]

# ── 消息聚合（可選） ──
# AGGREGATE_WINDOW=60

# ── 心跳告警（可選） ──
# HEARTBEAT_TIMEOUT=120

# ── 日誌（可選） ──
# LOG_LEVEL=INFO
# LOG_FILE=logs/smsbridge.log
```

---

## 相關工具

- 查看當前生效配置：`uv run smsbridge config`
- 查看運行時狀態：`uv run smsbridge status`
- 管理過濾規則：`uv run smsbridge filter list/add/remove/regex-add/regex-remove`
- 管理消息聚合：`uv run smsbridge agg status/set`
- 完整安裝指引：參見 [`INSTALL.md`](./INSTALL.md)
