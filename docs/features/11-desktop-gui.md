# 11. 桌面 GUI 客戶端

> 一體化的桌面應用（Tauri），整合 FastAPI 服務器 + ADB 管理 + 系統托盤。

---

## 動機

對非技術用戶最友好的交付形式：一個安裝包，雙擊運行，手機插上 USB 就能用。

## 技術選型：Tauri

Tauri = Rust 後端 + 系統 WebView 前端，相比 Electron：
- 體積小（<10MB vs ~150MB）
- 內存低
- 安全性更高（Rust + 最小權限模型）

## 架構

```
┌─────────────────────────────────┐
│         Tauri Window            │
│  ┌───────────────────────────┐  │
│  │   React / Svelte 前端     │  │
│  │   ┌─── 連接狀態           │  │
│  │   ├── 最近轉發列表        │  │
│  │   ├── 設置面板            │  │
│  │   └── 日誌查看            │  │
│  └───────────────────────────┘  │
├─────────────────────────────────┤
│    Rust 後臺                     │
│    ├── 啓動/停止 Python 服務器  │
│    ├── 調用 ADB reverse         │
│    └── 系統托盤                 │
└─────────────────────────────────┘
```

## 實現步驟

### 11.1 Tauri 項目初始化

```bash
npm create tauri-app smsbridge-desktop
cd smsbridge-desktop
npm install
```

### 11.2 Rust 側：管理 Python 子進程

```rust
// src-tauri/src/main.rs
use std::process::{Command, Child};
use tauri::Manager;

struct AppState {
    server: Mutex<Option<Child>>,
}

#[tauri::command]
fn start_server(state: State<AppState>) -> Result<(), String> {
    let child = Command::new("uv")
        .args(["run", "smsbridge", "start"])
        .spawn().map_err(|e| e.to_string())?;
    *state.server.lock().unwrap() = Some(child);
    Ok(())
}

#[tauri::command]
fn stop_server(state: State<AppState>) -> Result<(), String> {
    if let Some(mut child) = state.server.lock().unwrap().take() {
        child.kill().map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

### 11.3 前端：React/Svelte 儀表板

簡潔的儀表板：
- 🟢/🔴 連接狀態指示
- 最近轉發列表（從 `GET /health` 和內部狀態獲取）
- 啟動/停止按鈕
- 「在瀏覽器打開 Web 面板」按鈕（跳轉到 `http://127.0.0.1:8580/`）

### 11.4 分發

- Windows：`.msi` / `.exe`（NSIS）
- macOS：`.dmg`
- Linux：`.AppImage` / `.deb`

## 與現有項目的關係

- Tauri 項目**不替代** server/ 目錄，而是將其打包嵌入
- 依然需要 Python + uv 運行環境（可選 PyInstaller 將 server 編譯為 exe）
- Android 端不變

## 依賴

- Node.js + npm（構建前端）
- Rust toolchain（構建 Tauri）
- `tauri` CLI

## 風險

- 第一個大型跨平臺項目，學習曲線較陡
- Python 環境依賴仍需用戶手動安裝（或捆綁 Python 嵌入式 dist）
- Tauri v2 API 仍在演進中

## 驗收標準

- 雙擊 exe → 窗口打開 → 顯示 SMSBridge 儀表板
- 點擊「啓動」→ 服務器啓動 → 狀態變 🟢
- 托盤圖標 → 右鍵可控制
- 插 USB → 自動 `adb reverse` → 手機連接
