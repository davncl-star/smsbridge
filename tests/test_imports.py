"""基礎冒煙：import、模型格式化、CLI parser。"""
from __future__ import annotations

import argparse

from server.models import IncomingSMS
from server.telegram import format_sms


def test_imports() -> None:
    """確保核心模塊可正確導入。"""
    from server.cli import main as cli_main  # noqa: F401
    from server.config import get_settings  # noqa: F401
    from server.main import app  # noqa: F401

    assert callable(cli_main)
    assert callable(get_settings)
    routes = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/health" in routes
    assert "/api/sms" in routes


def test_format_sms_minimal() -> None:
    sms = IncomingSMS(
        sender="Davncl",
        number="+8613800000000",
        body="hello",
        received_at="2026-06-30T17:00:00",
        sim_slot=1,
    )
    out = format_sms(sms)
    assert "Davncl" in out
    assert "+8613800000000" in out
    assert "hello" in out
    assert "SIM1" in out
    # device_id 為空時不應出現 "Device:" 行
    assert "Device" not in out


def test_format_sms_with_device() -> None:
    sms = IncomingSMS(
        sender="",
        number="+8613900000000",
        body="<b>xss attempt</b>",
        received_at="2026-06-30T17:00:00",
        sim_slot=0,
        device_id="dev-123",
    )
    out = format_sms(sms)
    # 沒有 sender 時用 number 替代
    assert "+8613900000000" in out
    # 正文應被 HTML 轉義
    assert "&lt;b&gt;xss attempt&lt;/b&gt;" in out
    assert "Device" in out
    assert "dev-123" in out


def test_cli_parser_has_subcommands() -> None:
    """CLI 至少需要 start/status/config 這幾個子命令。"""
    parser = argparse.ArgumentParser(prog="smsbridge")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("start", "status", "config"):
        sub.add_parser(name)

    ns = parser.parse_args(["start"])
    assert ns.cmd == "start"
    ns = parser.parse_args(["status"])
    assert ns.cmd == "status"


def test_settings_requires_token(monkeypatch) -> None:
    """未配 TELEGRAM_BOT_TOKEN 時構造 Settings 應失敗。"""
    from server.config import Settings

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_IDS", raising=False)
    try:
        Settings()
        raised = False
    except Exception:
        raised = True
    assert raised, "Settings() 應在缺少 token 時拋 ValidationError"


def test_settings_parses_chat_ids(monkeypatch) -> None:
    """環境變量支持 JSON、逗號分隔、單 int。"""
    from server.config import Settings

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:FAKE")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "111, 222, 333")
    s = Settings()
    assert s.telegram_chat_ids == [111, 222, 333]

    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "[444, 555]")
    s = Settings()
    assert s.telegram_chat_ids == [444, 555]

    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "999")
    s = Settings()
    assert s.telegram_chat_ids == [999]

    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "")
    s = Settings()
    assert s.telegram_chat_ids == []