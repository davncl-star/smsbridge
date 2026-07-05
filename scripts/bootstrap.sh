#!/usr/bin/env bash
# SMSBridge · 一鍵自助安裝腳本
# 用法：bash scripts/bootstrap.sh
# 功能：建立 .env → 安裝 uv 依賴 → 啟用 systemd → 建立 ADB reverse → 啟動服務

set -euo pipefail

BRIDGE_SCRIPT="$(cd "$(dirname "$0")" && pwd)/bridge.sh"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
VENV_DIR="$PROJECT_DIR/.venv"

# ── 色彩輸出 ───────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$*"; }

# ── 步驟 1：檢查 ADB ──────────────────────────────────────────────────
step_adb() {
    info "檢查 ADB..."
    local adb_path
    adb_path="$(command -v adb)" || true
    if [[ -z "$adb_path" && -n "${ANDROID_HOME:-}" ]]; then
        adb_path="$ANDROID_HOME/platform-tools/adb"
    fi
    if [[ -z "$adb_path" ]]; then
        warn "adb not found. 請安裝 Android SDK Platform-Tools 或設定 ANDROID_HOME"
        warn "後續步驟仍可繼續，但 ADB 橋接需手動處理。"
        return 0
    fi
    ok "adb found: $adb_path"

    # 啟動 adb server + 檢查設備
    "$adb_path" start-server 2>/dev/null || true
    local devices
    devices=$("$adb_path" devices | awk 'NR>1 && $2=="device" {print $1}')
    if [[ -z "$devices" ]]; then
        warn "未偵測到已授權的 Android 設備。請插 USB 並確認 USB 調試已啟用。"
    else
        ok "已授權設備: $(echo "$devices" | tr '\n' ' ')"
    fi
}

# ── 步驟 2：建立 .env ──────────────────────────────────────────────────
step_env() {
    if [[ -f "$ENV_FILE" ]]; then
        info ".env 已存在，跳過建立。"
        # 檢查 Token 和 Chat ID 是否已填
        if grep -q "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" \
            && ! grep -q "^TELEGRAM_BOT_TOKEN=123456\|^TELEGRAM_BOT_TOKEN=$" "$ENV_FILE" \
            && grep -q "^TELEGRAM_CHAT_IDS=" "$ENV_FILE" \
            && ! grep -q "^TELEGRAM_CHAT_IDS=123456789\|^TELEGRAM_CHAT_IDS=$" "$ENV_FILE"; then
            ok ".env 已填妥必要欄位。"
            return 0
        fi
        warn ".env 存在但 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_IDS 似未填妥。"
    fi

    echo ""
    info "┌──────────────────────────────────────────────┐"
    info "│  請輸入 Telegram Bot Token                  │"
    info "│  在 @BotFather 建立 Bot 後取得              │"
    info "│  格式: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz │"
    info "└──────────────────────────────────────────────┘"
    printf "${CYAN}Token:${NC} "
    read -r token
    token="$(echo "$token" | xargs)"  # trim
    if [[ -z "$token" ]]; then
        fail "Token 不能為空。"
        exit 1
    fi

    echo ""
    info "┌───────────────────────────────────────────────┐"
    info "│  請輸入 Telegram Chat ID                    │"
    info "│  發消息給 Bot 後呼叫 getUpdates 取得         │"
    info "│  支援逗號分隔（多個接收者）                   │"
    info "│  例如: 123456789 或 123456789,987654321       │"
    info "└───────────────────────────────────────────────┘"
    printf "${CYAN}Chat ID(s):${NC} "
    read -r chat_ids
    chat_ids="$(echo "$chat_ids" | xargs)"  # trim
    if [[ -z "$chat_ids" ]]; then
        fail "Chat ID 不能為空。"
        exit 1
    fi

    # 建立 .env
    cat > "$ENV_FILE" <<EOF
# SMSBridge · 自動產生的配置檔
# 可隨時手動編輯，或重新執行本腳本更新

TELEGRAM_BOT_TOKEN=${token}
TELEGRAM_CHAT_IDS=${chat_ids}

# 服務器設定
SERVER_HOST=127.0.0.1
SERVER_PORT=8580

# 內容過濾（可選）
FILTER_ENABLED=True
FILTER_KEYWORDS_BLOCK=
FILTER_REGEX_BLOCK=

# 消息聚合（可選，0=關閉）
AGGREGATE_WINDOW=0

# 心跳告警（可選，預設 120 秒）
HEARTBEAT_TIMEOUT=120

# 日誌
LOG_LEVEL=INFO
LOG_FILE=logs/smsbridge.log
EOF

    ok ".env 已建立於 $ENV_FILE"
}

# ── 步驟 3：安裝 uv 依賴 ──────────────────────────────────────────────
step_deps() {
    info "安裝 Python 依賴..."
    cd "$PROJECT_DIR"

    if ! command -v uv &>/dev/null; then
        warn "uv 未安裝，嘗試自動安裝..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # 重新載入 PATH
        export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    fi

    if ! command -v uv &>/dev/null; then
        fail "uv 安裝失敗。請手動安裝: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    uv sync
    ok "Python 依賴安裝完成。"
}

# ── 步驟 4：啟用 systemd 服務 ─────────────────────────────────────────
step_systemd() {
    if [[ "$(uname -s)" != "Linux" ]]; then
        info "非 Linux 系統，跳過 systemd 設定。"
        return 0
    fi

    if ! command -v systemctl &>/dev/null; then
        info "systemctl 不可用，跳過 systemd 設定。"
        return 0
    fi

    info "啟用 systemd user services..."

    # 確保目錄存在
    mkdir -p "$HOME/.config/systemd/user"

    # 寫入 smsbridge.service
    cat > "$HOME/.config/systemd/user/smsbridge.service" <<EOF
[Unit]
Description=SMSBridge · SMS → Telegram forwarding server
After=network.target
Wants=smsbridge-bridge.service

[Service]
Type=simple
ExecStart=${VENV_DIR}/bin/smsbridge start
WorkingDirectory=${PROJECT_DIR}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:${PROJECT_DIR}/logs/server.systemd.log
StandardError=append:${PROJECT_DIR}/logs/server.systemd.log
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=${PROJECT_DIR}/logs

[Install]
WantedBy=default.target
EOF

    # 寫入 smsbridge-bridge.service
    cat > "$HOME/.config/systemd/user/smsbridge-bridge.service" <<EOF
[Unit]
Description=SMSBridge · ADB reverse port bridge (hot-plug watch)
After=network.target
PartOf=smsbridge.service

[Service]
Type=simple
ExecStart=/usr/bin/bash ${BRIDGE_SCRIPT} --watch
ExecStop=/usr/bin/adb reverse --remove-all
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable smsbridge.service smsbridge-bridge.service 2>/dev/null || true
    systemctl --user restart smsbridge-bridge.service 2>/dev/null || true
    systemctl --user restart smsbridge.service 2>/dev/null || true
    ok "systemd services 已寫入並啟用。"
}

# ── 步驟 5：建立 ADB reverse ──────────────────────────────────────────
step_bridge() {
    info "建立 ADB reverse 橋接..."
    if command -v adb &>/dev/null; then
        if adb devices | awk 'NR>1 && $2=="device" {exit 0} {exit 1}'; then
            adb reverse tcp:8580 tcp:8580 2>/dev/null && ok "ADB reverse 已建立: tcp:8580" \
                || warn "ADB reverse 失敗，請稍後手動執行: adb reverse tcp:8580 tcp:8580"
        else
            warn "未偵測到已授權設備，跳過 ADB reverse。插上 USB 後手動執行: bash $BRIDGE_SCRIPT"
        fi
    else
        warn "adb 不可用，跳過 ADB reverse。"
    fi
}

# ── 完成提示 ───────────────────────────────────────────────────────────
print_summary() {
    echo ""
    ok "============================================"
    ok "  SMSBridge 安裝完成！"
    ok "============================================"
    echo ""
    echo "  1️⃣   手機上打開 SMSBridge App"
    echo "  2️⃣   點「啟動服務」"
    echo "  3️⃣   確認狀態指示燈變綠「已連接」"
    echo ""
    echo "  🌐   Server 日誌: tail -f $PROJECT_DIR/logs/smsbridge.log"
    echo "  🌐   systemd 日誌: journalctl --user -u smsbridge.service -f"
    echo ""
    echo "  🛠️  管理指令:"
    echo "       uv run smsbridge status           # 查看服務狀態"
    echo "       uv run smsbridge config           # 查看配置"
    echo "       uv run smsbridge filter list      # 管理過濾規則"
    echo "       uv run smsbridge agg status       # 查看聚合設定"
    echo ""
    echo "  📖   完整文檔: docs/INSTALL.md"
    echo ""
}

# ── 主流程 ─────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "╔═══════════════════════════════════════╗"
    echo "║     SMSBridge · 一鍵自助安裝          ║"
    echo "╚═══════════════════════════════════════╝"
    echo ""

    step_adb
    echo ""
    step_env
    echo ""
    step_deps
    echo ""
    step_systemd
    echo ""
    step_bridge
    echo ""
    print_summary
}

main "$@"
