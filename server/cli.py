"""CLI 入口：smsbridge start/stop/status。"""
from __future__ import annotations

import argparse
import sys

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smsbridge", description="SMS → Telegram forwarding daemon")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("start", help="啟動本地 HTTP 服務器").set_defaults(func=cmd_start)
    sub.add_parser("status", help="查看配置/日志狀態").set_defaults(func=cmd_status)
    sub.add_parser("config", help="打印當前生效配置").set_defaults(func=cmd_config)

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())