# Scripts (Phase 3 · 待實現)

> ADB 橋接輔助腳本目錄。

## 計劃內容

| 文件 | 平台 |
|------|------|
| `bridge.bat` | Windows |
| `bridge.sh` | Linux / macOS |

## 職責

- 檢測 USB 設備是否連接
- 執行 `adb reverse tcp:8580 tcp:8580`
- 監聽 USB 拔出/插入事件，自動重連
- 啟動/關閉電腦端服務（可選）

## 用法（佔位，待 Phase 3 實現）

```bash
# Windows
scripts\bridge.bat

# Linux
./scripts/bridge.sh
```

## 何時開工

Phase 2（Android 端）跑通後再開工，這樣才能聯調。