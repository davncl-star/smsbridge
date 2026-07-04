# 3. 系統托盤圖標

> Windows / macOS 系統托盤圖標，一鍵啓停 SMSBridge，無需終端窗口。

---

## 動機

當前必須開着終端窗口跑 `uv run smsbridge start`。托盤圖標讓 SMSBridge 像後臺服務一樣隱藏在托盤中，右鍵即可控制。

## 架構

```
┌─────────────────────┐
│  系統托盤（pystray） │
│  ┌───┐              │
│  │ 📩 │ 右鍵菜單：    │
│  └───┘  啟動/停止     │
│          打開面板     │
│          退出         │
└─────────┬───────────┘
          │ subprocess
          ▼
┌─────────────────────┐
│  uvicorn server     │
│  (子進程)           │
└─────────────────────┘
```

## 實現步驟

### 3.1 創建 `server/tray.py`

```python
import pystray
from PIL import Image

def create_tray(start_fn, stop_fn, status_fn):
    icon = pystray.Icon("smsbridge")

    def on_start():
        start_fn()
        update_menu()

    def on_stop():
        stop_fn()
        update_menu()

    menu = pystray.Menu(
        pystray.MenuItem("啟動", on_start, enabled=lambda: not running),
        pystray.MenuItem("停止", on_stop, enabled=lambda: running),
        pystray.MenuItem("狀態", lambda: status_fn()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", lambda: icon.stop()),
    )

    icon.menu = menu
    icon.icon = create_image()  # 16x16 圖標
    icon.run()
```

### 3.2 集成到 CLI

```python
# server/cli.py
def cmd_tray(args):
    from .tray import create_tray
    import uvicorn
    import threading

    proc = None
    def start():
        nonlocal proc
        proc = subprocess.Popen(["uv", "run", "smsbridge", "start"])

    def stop():
        nonlocal proc
        if proc: proc.terminate()

    create_tray(start, stop, lambda: print("running" if running else "stopped"))
```

### 3.3 Windows 一鍵啓動

`scripts/smsbridge-tray.vbs` 或 `.bat`：

```bash
start /B uv run smsbridge tray
```

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/tray.py` | **新檔** — pystray icon + 菜單 |
| `server/cli.py` | 新增 `tray` 子命令 |
| `scripts/smsbridge-tray.vbs` | **新檔** — 無窗口啓動 |
| `pyproject.toml` | 新增依賴 `pystray` + `pillow` |

## 依賴

- `pystray`（跨平臺托盤）
- `pillow`（生成圖標圖像）

## 風險

- macOS 需要 `pyobjc`，安裝較重
- Linux 需要系統托盤（GTK / Qt），部分 WM 不支持
- 托盤圖標在 HiDPI 顯示器上可能模糊（需準備多尺寸）

## 替代方案

若 `pystray` 太重，可用：
- Windows：`infi.systray` 或 Win32 API via `ctypes`
- macOS：`rumps`
- 全平台：在 `--watch` 模式基礎上新增托盤（不必求全）

## 驗收標準

- 運行 `uv run smsbridge tray` → 系統托盤出現 SMSBridge 圖標
- 右鍵可啟動/停止服務器
- 右鍵可查看運行狀態
