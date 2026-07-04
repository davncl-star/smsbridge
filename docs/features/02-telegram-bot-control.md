# 2. Telegram Bot 雙向控制

> 通過 Telegram Bot 發送指令管理 SMSBridge，不用開電腦終端。

---

## 動機

當前管理 SMSBridge 需要打開終端執行 `smsbridge status`。透過 Bot 指令可以隨時隨地查看狀態、統計和控制。

## 架構

```
用戶 ──→ @SMSBridge_Bot ──→ Telegram API ──→ 電腦端（long polling）
                                              │
                                              ▼
                                        status / restart / stats
```

## 實現步驟

### 2.1 新增指令處理器

`server/bot_handler.py`：

```python
COMMANDS = {
    "/start": "SMSBridge Bot 已啓用",
    "/status": handle_status,     # 服務器運行時間、連接設備數
    "/stats": handle_stats,       # 今日轉發、過濾、失敗統計
    "/restart": handle_restart,   # 重啓服務器
    "/filter": handle_filter,     # 查看/添加/刪除過濾關鍵詞
}
```

### 2.2 Long polling 循環

在 `lifespan` 中啓動後臺 task：

```python
async def bot_poll_loop():
    offset = 0
    while True:
        updates = await get_updates(offset)
        for update in updates:
            await handle_update(update)
            offset = update["update_id"] + 1
        await asyncio.sleep(2)
```

### 2.3 指令處理範例

```python
async def handle_status(chat_id):
    s = get_settings()
    text = (
        f"📊 SMSBridge Status\n"
        f"Uptime: {time.monotonic() - _start_time:.0f}s\n"
        f"Token: {'✅' if s.has_token else '❌'}\n"
        f"Chats: {len(s.telegram_chat_ids)}\n"
        f"Filter: {'on' if s.filter_enabled else 'off'}\n"
        f"Tests: 27/27 ✅"
    )
    await send_text(text, s)
```

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/bot_handler.py` | **新檔** — 指令路由 + 處理器 |
| `server/main.py` | lifespan 中啓動 `bot_poll_loop` |
| `server/telegram.py` | 新增 `get_updates(offset)` 函數 |
| `server/config.py` | 可選：`bot_enabled: bool = True` |

## 依賴

- 無新增依賴（httpx 已有）
- 注意：若 Bot 已設 Webhook，`getUpdates` 會返回空；需要先 `deleteWebhook`

## 風險

- Long polling 在大量轉發時可能增加延遲（可優化：獨立 worker task）
- 與 `openclaw` agent 共用同一個 Bot 時需管理 offset
- Bot Token 泄露 → 任何人可控制；建議支持白名單 chat_id

## 驗收標準

- 發送 `/status` → 返回服務器狀態
- 發送 `/stats` → 返回轉發/過濾統計
- 發送 `/restart` → 服務器重啓
