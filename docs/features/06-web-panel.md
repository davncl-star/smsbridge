# 6. 短信歷史 + Web 面板

> SQLite 存儲轉發記錄，Web 頁面搜索、統計、查看被過濾的短信。

---

## 架構

```
手機 POST ──→ 過濾 → 聚合 → 發送 → 寫入 SQLite
                                      │
                                      ▼
                               FastAPI 靜態路由
                                      │
                                      ▼
                              Web 面板（HTMX）
                               ├── 最近轉發
                               ├── 按號碼搜索
                               ├── 過濾日誌
                               └── 統計圖表
```

## 數據庫設計

```sql
CREATE TABLE sms_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender      TEXT,
    number      TEXT,
    body        TEXT,
    sim_slot    INTEGER,
    device_id   TEXT,
    created_at  TEXT NOT NULL,          -- ISO 8601
    status      TEXT NOT NULL,          -- delivered / filtered / failed
    chat_ids    TEXT                    -- JSON 列表
);

CREATE INDEX idx_sms_number ON sms_log(number);
CREATE INDEX idx_sms_created ON sms_log(created_at);
```

## 實現步驟

### 6.1 初始化數據庫

`server/db.py`：

```python
import aiosqlite

_DB = "smsbridge.db"

async def init():
    async with aiosqlite.connect(_DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS sms_log (...)""")
        await db.commit()

async def insert(sms, status, chat_ids=None):
    async with aiosqlite.connect(_DB) as db:
        await db.execute("INSERT INTO sms_log VALUES (?, ?, ?, ...)", ...)
        await db.commit()
```

### 6.2 POST /api/sms 時記錄

在 `receive_sms` 中調用 `db.insert(...)`，在 filter 攔截/發送成功/失敗各分支記錄。

### 6.3 Web 面板路由

`server/web.py`：

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    async with aiosqlite.connect(_DB) as db:
        rows = await db.execute_fetchall("SELECT * FROM sms_log ORDER BY id DESC LIMIT 50")
    return render_template("dashboard.html", rows=rows)
```

### 6.4 前端

簡單方案：**HTMX**（基於 HTML，無需 JS 構建工具）：

```html
<table>
  <tr><th>時間</th><th>號碼</th><th>正文</th><th>狀態</th></tr>
  {% for row in rows %}
  <tr>
    <td>{{ row.created_at }}</td>
    <td>{{ row.number }}</td>
    <td>{{ row.body[:40] }}</td>
    <td>{{ row.status }}</td>
  </tr>
  {% endfor %}
</table>
<input type="search" name="q" hx-get="/search" hx-trigger="keyup changed delay:500ms">
```

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/db.py` | **新檔** — SQLite 初始化和 CRUD |
| `server/web.py` | **新檔** — 靜態面板路由 |
| `server/main.py` | lifespan 中調用 `db.init()` + 掛載 web router |
| `server/templates/` | **新目錄** — Jinja2 模板 |
| `server/templates/dashboard.html` | **新檔** |
| `server/telegram.py` | `send_sms` 和 `send_text` 回調中記錄結果 |
| `pyproject.toml` | 新增 `aiosqlite` + `jinja2` |

## 依賴

- `aiosqlite` — 異步 SQLite 驅動
- `jinja2` — 模板引擎（FastAPI 內置支援）

## 風險

- SQLite 不適合高併寫（SMSBridge 場景用戶級別，無此問題）
- `.db` 文件需加入 `.gitignore`
- Web 面板默認無認證——建議綁定 `127.0.0.1` 或加簡單密碼

## 驗收標準

- 轉發一條短信 → 訪問 `http://127.0.0.1:8580/` → 顯示在最近列表中
- 搜索號碼 → 返回匹配結果
- 過濾規則攔截的短信 → 在面板中以 `filtered` 狀態顯示
- 服務器重啓後數據不丟失
