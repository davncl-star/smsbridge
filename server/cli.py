"""CLI 入口：smsbridge start/stop/status/config/bridge。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


def cmd_start(args: argparse.Namespace) -> int:
    from .config import get_settings
    s = get_settings()
    s.log_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"start smsbridge @ http://{s.server_host}:{s.server_port}")
    uvicorn.run(
        "server.main:app",
        host=s.server_host,
        port=s.server_port,
        log_level=s.log_level.lower(),
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from .config import get_settings
    s = get_settings()
    print(f"config ok: token={'set' if s.has_token else 'MISSING'}, chats={len(s.telegram_chat_ids)}")
    print(f"log file: {s.log_file}  exists={s.log_file.exists()}")
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
    return 0


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smsbridge", description="SMS → Telegram forwarding daemon")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("start", help="啟動本地 HTTP 服務器").set_defaults(func=cmd_start)
    sub.add_parser("status", help="查看配置/日志狀態").set_defaults(func=cmd_status)
    sub.add_parser("config", help="打印當前生效配置").set_defaults(func=cmd_config)

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

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())