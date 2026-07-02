"""Telegram Bot API 封裝：直接走 HTTP，不引入 python-telegram-bot。"""
from __future__ import annotations

import logging
from html import escape

import httpx

from .config import Settings
from .models import IncomingSMS

log = logging.getLogger(__name__)

_API = "https://api.telegram.org"


def format_sms(sms: IncomingSMS) -> str:
    """把短信格式化為 Telegram 消息（HTML 模式安全轉義）。"""
    sim = f"SIM{sms.sim_slot}" if sms.sim_slot else "SIM?"
    who = sms.sender or sms.number
    ts = sms.received_at.strftime("%Y-%m-%d %H:%M:%S")
    device = f"\nDevice: <code>{escape(sms.device_id)}</code>" if sms.device_id else ""

    return (
        f"📩 <b>新短信</b>  <i>{sim}</i>\n"
        f"<b>{escape(who)}</b>  <code>{escape(sms.number)}</code>\n"
        f"<i>{escape(ts)}</i>{device}\n\n"
        f"{escape(sms.body)}"
    )


async def send_sms(sms: IncomingSMS, settings: Settings) -> tuple[bool, list[int], str | None]:
    """把短信轉發給所有配置的 chat。

    Returns: (ok, delivered_chat_ids, error_message)
    """
    if not settings.telegram_chat_ids:
        return False, [], "no chat ids configured"

    text = format_sms(sms)
    delivered: list[int] = []
    last_error: str | None = None

    async with httpx.AsyncClient(timeout=10.0) as client:
        for chat_id in settings.telegram_chat_ids:
            try:
                resp = await client.post(
                    f"{_API}/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": settings.telegram_parse_mode,
                        "disable_web_page_preview": settings.telegram_disable_preview,
                    },
                )
                data = resp.json()
                if resp.status_code == 200 and data.get("ok"):
                    delivered.append(chat_id)
                    log.info("delivered sms to chat=%s", chat_id)
                else:
                    last_error = str(data.get("description", resp.text))
                    log.warning("telegram rejected: chat=%s err=%s", chat_id, last_error)
            except httpx.HTTPError as exc:
                last_error = repr(exc)
                log.error("telegram http error chat=%s: %s", chat_id, exc)

    return bool(delivered), delivered, last_error