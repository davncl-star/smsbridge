"""CLI 入口：smsbridge start/stop/status/config/bridge/filter/agg。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


# ── 核心命令 ─────────────────────────────────────────────────────────────


def cmd_start(args: argparse.Namespace) -> int:
    from .config import get_settings
    s = get_settings()
    s.log_file.parent.mkdir(parents=True, exist_ok=True)

    # 優先 CLI 參數，其次環境變量，最後預設
    cert = args.tls_cert or s.tls_certfile
    key = args.tls_key or s.tls_keyfile

    scheme = "https" if (cert and key) else "http"
    print(f"start smsbridge @ {scheme}://{s.server_host}:{s.server_port}")
    if cert and key:
        print(f"  tls cert={cert}  key={key}")

    uvicorn.run(
        "server.main:app",
        host=s.server_host,
        port=s.server_port,
        log_level=s.log_level.lower(),
        ssl_certfile=str(cert) if cert else None,
        ssl_keyfile=str(key) if key else None,
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from .config import get_settings
    s = get_settings()
    print(f"config ok: token={'set' if s.has_token else 'MISSING'}, chats={len(s.telegram_chat_ids)}")
    print(f"log file: {s.log_file}  exists={s.log_file.exists()}")

    # 顯示過濾器統計
    from .filter_engine import FilterEngine
    from .main import app
    fe: FilterEngine | None = getattr(app.state, "filter", None)
    if fe:
        print(f"filter: enabled={fe.enabled}  keywords={len(fe.keywords)}  regex={len(fe.patterns)}")
    else:
        print("filter: (not initialized / server not started)")

    # 顯示聚合統計
    from .main import app as _app
    agg = getattr(_app.state, "aggregator", None)
    if agg:
        print(f"aggregator: window={agg.window}s {'enabled' if agg.window > 0 else 'disabled'}")
    else:
        print("aggregator: (not initialized / server not started)")

    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """打印當前生效配置（隱藏 token）。"""
    from .config import get_settings
    s = get_settings()
    masked = (s.telegram_bot_token[:8] + "***") if s.has_token else "(unset)"
    print(f"host              : {s.server_host}")
    print(f"port              : {s.server_port}")
    print(f"bot_token         : {masked}")
    print(f"chat_ids          : {s.telegram_chat_ids}")
    print(f"parse_mode        : {s.telegram_parse_mode}")
    print(f"log_level         : {s.log_level}")
    print(f"log_file          : {s.log_file}")
    print(f"filter_enabled    : {s.filter_enabled}")
    print(f"filter_keywords   : {s.filter_keywords_block}")
    print(f"filter_regex      : {s.filter_regex_block}")
    print(f"aggregate_window  : {s.aggregate_window}s")
    return 0


# ── bridge ────────────────────────────────────────────────────────────────


def cmd_bridge(args: argparse.Namespace) -> int:
    """調用 platform-specific 橋接腳本（scripts/bridge.*）。

    Windows → scripts/bridge.ps1 (推薦) / bridge.bat
    Linux/macOS → scripts/bridge.sh
    """
    import subprocess

    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"

    if sys.platform == "win32":
        script = scripts_dir / "bridge.ps1"
        if not script.exists():
            script = scripts_dir / "bridge.bat"
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), *args.script_args]
    else:
        script = scripts_dir / "bridge.sh"
        cmd = [str(script), *args.script_args]

    if not script.exists():
        print(f"[ERROR] bridge script not found: {script}", file=sys.stderr)
        return 1

    print(f"[INFO] running: {' '.join(cmd)}")
    return subprocess.call(cmd)


# ── filter ────────────────────────────────────────────────────────────────


def cmd_filter(args: argparse.Namespace) -> int:
    """管理短信內容過濾規則。

    操作：list / add <keyword> / remove <keyword> / regex-add <pattern> / regex-remove <pattern>
    規則存於 .env 的 filter_keywords_block / filter_regex_block。
    """
    from .config import get_settings

    if args.filter_cmd == "list":
        s = get_settings()
        print(f"filter: enabled={s.filter_enabled}")
        print(f"keywords ({len(s.filter_keywords_block)}):")
        for kw in s.filter_keywords_block:
            print(f"  - {kw}")
        print(f"regex patterns ({len(s.filter_regex_block)}):")
        for p in s.filter_regex_block:
            print(f"  - {p}")
        return 0

    # 以下操作需要寫回 .env
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        print("[ERROR] .env not found in current directory", file=sys.stderr)
        return 1

    raw = env_path.read_text(encoding="utf-8")
    s = get_settings()

    if args.filter_cmd in ("add", "remove"):
        key = "filter_keywords_block"
        current = list(s.filter_keywords_block)
    elif args.filter_cmd in ("regex-add", "regex-remove"):
        key = "filter_regex_block"
        current = list(s.filter_regex_block)
    else:
        print(f"[ERROR] unknown filter cmd: {args.filter_cmd}", file=sys.stderr)
        return 1

    value = args.filter_value

    if args.filter_cmd in ("add", "regex-add"):
        if value in current:
            print(f"[OK] already in list: {value}")
            return 0
        current.append(value)
        print(f"[OK] added: {value}")

    elif args.filter_cmd in ("remove", "regex-remove"):
        if value not in current:
            print(f"[WARN] not found in list: {value}")
            return 0
        current.remove(value)
        print(f"[OK] removed: {value}")

    # 寫回 .env
    import json

    new_line = f'{key}={json.dumps(current, ensure_ascii=False)}\n'
    # 替換或追加
    marker = f"{key}="
    if marker in raw:
        lines = raw.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(marker):
                lines[i] = new_line
                break
        raw = "".join(lines)
    else:
        raw = raw.rstrip("\n") + "\n" + new_line

    env_path.write_text(raw, encoding="utf-8")
    return 0


# ── agg ───────────────────────────────────────────────────────────────────


def cmd_agg(args: argparse.Namespace) -> int:
    """查看和配置消息聚合。"""
    from .config import get_settings

    s = get_settings()
    if args.agg_cmd == "status":
        print(f"aggregate_window: {s.aggregate_window}s {'(disabled)' if s.aggregate_window == 0 else ''}")
        return 0

    if args.agg_cmd == "set":
        try:
            val = int(args.agg_value)
        except (ValueError, TypeError):
            print("[ERROR] value must be integer seconds (0=disable)", file=sys.stderr)
            return 1
        if val < 0:
            print("[ERROR] value must be >= 0", file=sys.stderr)
            return 1

        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            print("[ERROR] .env not found in current directory", file=sys.stderr)
            return 1

        raw = env_path.read_text(encoding="utf-8")
        new_line = f"aggregate_window={val}\n"
        marker = "aggregate_window="
        if marker in raw:
            lines = raw.splitlines(keepends=True)
            for i, line in enumerate(lines):
                if line.startswith(marker):
                    lines[i] = new_line
                    break
            raw = "".join(lines)
        else:
            raw = raw.rstrip("\n") + "\n" + new_line

        env_path.write_text(raw, encoding="utf-8")
        print(f"[OK] aggregate_window set to {val}s {'(disabled)' if val == 0 else ''}")
        return 0

    print(f"[ERROR] unknown agg cmd: {args.agg_cmd}", file=sys.stderr)
    return 1


# ── 入口 ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smsbridge", description="SMS → Telegram forwarding daemon")
    sub = parser.add_subparsers(dest="cmd", required=True)

    start_p = sub.add_parser("start", help="啟動服務器（HTTP 或 HTTPS）")
    start_p.add_argument(
        "--tls-cert",
        default=None,
        help="TLS 憑證檔案路徑（PEM），指定後啟用 HTTPS",
    )
    start_p.add_argument(
        "--tls-key",
        default=None,
        help="TLS 私鑰檔案路徑（PEM）",
    )
    start_p.set_defaults(func=cmd_start)
    sub.add_parser("status", help="查看配置/日誌/過濾器/聚合狀態").set_defaults(func=cmd_status)
    sub.add_parser("config", help="打印當前生效配置").set_defaults(func=cmd_config)

    # bridge
    bridge_p = sub.add_parser(
        "bridge",
        help="ADB 橋接：建立 reverse 端口（轉發剩餘參數到 bridge 腳本）",
    )
    bridge_p.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="傳遞給 bridge 腳本的參數，如 --watch",
    )
    bridge_p.set_defaults(func=cmd_bridge)

    # filter
    filter_p = sub.add_parser("filter", help="管理短信內容過濾規則")
    filter_p.add_argument(
        "filter_cmd",
        choices=["list", "add", "remove", "regex-add", "regex-remove"],
        help="操作：list=列出規則 / add=添加關鍵詞 / remove=移出關鍵詞 / regex-add=添加正則 / regex-remove=移出正則",
    )
    filter_p.add_argument(
        "filter_value",
        nargs="?",
        default=None,
        help="關鍵詞或正則表達式（list 操作不需要此參數）",
    )
    filter_p.set_defaults(func=cmd_filter)

    # agg
    agg_p = sub.add_parser("agg", help="查看和配置消息聚合")
    agg_p.add_argument(
        "agg_cmd",
        choices=["status", "set"],
        help="status=查看當前窗口 / set=設置聚合窗口秒數",
    )
    agg_p.add_argument(
        "agg_value",
        nargs="?",
        default=None,
        help="聚合窗口秒數（0=關閉聚合）",
    )
    agg_p.set_defaults(func=cmd_agg)

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # 參數校驗
    if args.cmd == "filter" and args.filter_cmd != "list" and not args.filter_value:
        parser.error(f"filter {args.filter_cmd} requires a value")

    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
