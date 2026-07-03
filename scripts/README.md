# Scripts · Phase 3 · ADB 橋接

> 已交付。覆蓋 Windows / Linux / macOS 三大平台，含熱插拔監聽模式。

## 文件清單

| 文件 | 平台 | 模式 |
|------|------|------|
| `bridge.bat` | Windows batch | 一次性 reverse |
| `bridge.ps1` | Windows PowerShell | 一次性 + `-Watch` 熱插拔 |
| `bridge.sh` | Linux / macOS | 一次性 + `--watch` 熱插拔 |

## 快速使用

### 方式 A · CLI 統一入口（推薦）

```bash
uv run smsbridge bridge              # 一次性
uv run smsbridge bridge --watch      # 熱插拔監聽
```

### 方式 B · 直接調用

**Windows batch：**
```bat
scripts\bridge.bat
```

**Windows PowerShell（支援熱插拔）：**
```powershell
.\scripts\bridge.ps1                  # 一次性
.\scripts\bridge.ps1 -Watch           # 熱插拔
```

**Linux / macOS：**
```bash
./scripts/bridge.sh                   # 一次性
./scripts/bridge.sh --watch           # 熱插拔
```

## 工作流程

```
┌─────────────┐  1.插入 USB     ┌─────────────┐
│   Android   │ ──────────────→ │  bridge 脚本 │
│   手機端    │                 │  （平台適配） │
└─────────────┘                 └──────┬──────┘
                                      │ 2. 檢查 adb
                                      │ 3. 確認設備已授權
                                      │ 4. adb reverse tcp:8580
                                      ▼
                              ┌─────────────┐
                              │  電腦端服務器│
                              │  127.0.0.1  │
                              │  :8580      │
                              └─────────────┘
```

## 熱插拔模式

`-Watch` / `--watch` 模式每 3 秒輪詢一次 `adb devices`：
- 設備**連接** → 自動執行 `adb reverse`
- 設備**斷開** → 打印警告，等待重連
- **Ctrl+C** 退出

適合「長期插著手機」的工作流。

## adb 定位

所有腳本按以下順序查找 adb：
1. `PATH` 中的 `adb`
2. `$ANDROID_HOME/platform-tools/adb(.exe)`
3. `$ANDROID_SDK_ROOT/platform-tools/adb(.exe)`

任一找到即用，否則報錯退出。

## 錯誤碼

| 退出碼 | 含義 |
|--------|------|
| 0 | 成功 |
| 1 | adb 不可用（未安裝或未在 PATH） |
| 2 | 未找到已授權的設備 |
| 4 | `adb reverse` 失敗（端口被佔用等） |

## 何時開工

**Phase 1 跑通（服務器可接收） + Phase 2 APK 安裝到手機** 後立即可用。

- [x] Phase 3.1：`bridge.bat`
- [x] Phase 3.2：`bridge.sh`（含 --watch）
- [x] Phase 3.3：PowerShell `bridge.ps1`（含 -Watch）
- [x] Phase 3.4：CLI 集成 `smsbridge bridge`
