# 8. Telegram 管理過濾規則

> 通過 Telegram Bot 指令動態添加/刪除/查看過濾關鍵詞和正則規則，無需編輯 `.env` 重啓。

---

## 前置依賴

- **Feature #2**（Bot 雙向控制）— 提供指令基礎設施
- **Feature #6**（SQLite 存儲）— 規則持久化

## 指令設計

```
/filter                    — 查看當前過濾規則
/filter add 廣告           — 添加關鍵詞「廣告」
/filter add-regex \d{6}   — 添加正則規則
/filter del 廣告           — 刪除關鍵詞「廣告」
/filter enable             — 開啓過濾
/filter disable            — 關閉過濾
```

## 實現

### 8.1 規則持久化

擴展 `server/db.py`（在 #6 基礎上）：

```sql
CREATE TABLE filter_rules (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    type     TEXT NOT NULL,           -- 'keyword' | 'regex'
    pattern  TEXT NOT NULL,
    enabled  INTEGER DEFAULT 1,
    UNIQUE(type, pattern)
);
```

### 8.2 指令處理

```python
async def handle_filter(args: list[str], chat_id: int):
    if not args:
        return await list_filter()

    cmd, *rest = args
    match cmd:
        case "add":
            rule = " ".join(rest)
            await db.execute("INSERT INTO filter_rules (type, pattern) VALUES ('keyword', ?)", (rule,))
            engine.reload()   # 熱加載規則
            return f"✅ 已添加關鍵詞: {rule}"
        case "del":
            rule = " ".join(rest)
            await db.execute("DELETE FROM filter_rules WHERE pattern = ?", (rule,))
            engine.reload()
            return f"🗑️ 已刪除: {rule}"
        case "enable":
            await db.execute("UPDATE filter_rules SET enabled = 1")
            return "✅ 過濾已開啓"
        case "disable":
            await db.execute("UPDATE filter_rules SET enabled = 0")
            return "⏸️ 過濾已暫停"
```

### 8.3 過濾引擎熱加載

在 `filter_engine.py` 添加 `reload()` 方法：

```python
async def reload(self):
    rows = await db.fetchall("SELECT type, pattern FROM filter_rules WHERE enabled = 1")
    self._keywords = [r["pattern"].lower() for r in rows if r["type"] == "keyword"]
    self._patterns = [re.compile(r["pattern"]) for r in rows if r["type"] == "regex"]
```

### 8.4 啓動時規則合併

啟動時從 `.env` 加載的規則 + 數據庫規則 = 最終過濾列表。`.env` 規則優先級高於 DB。

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/db.py` | 新增 `filter_rules` 表 + CRUD |
| `server/bot_handler.py` | 新增 `/filter` 指令處理（依賴 #2） |
| `server/filter_engine.py` | 新增 `reload()` 方法 + `add_rule()` |
| `server/config.py` | 可選 `filter_db_priority: bool` |

## 依賴

- 無新增依賴（復用 #2 的 Bot 基礎設施 + #6 的 SQLite）
- 迭代順序建議：#2 → #6 → #8

## 風險

- 熱加載需線程安全（`_keywords` 和 `_patterns` 替換時加鎖）
- `.env` 規則和 DB 規則衝突時需要明確的優先級策略

## 驗收標準

- `/filter` → 列出當前規則
- `/filter add 廣告` → 添加到黑名單
- `/filter del 廣告` → 從黑名單移除
- 重啓後 DB 中的規則仍在
- `.env` 中的 `FILTER_KEYWORDS_BLOCK` 規則仍然生效
