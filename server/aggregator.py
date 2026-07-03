"""消息聚合器：同一號碼短時間內的多條短信合併為一條。"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Coroutine

from .models import IncomingSMS
from .telegram import format_sms

log = logging.getLogger(__name__)

FORWARD = "forward"
QUEUED = "queued"


class SmsAggregator:
    """同一 (number, sim_slot) 第一條即時轉發，後續 N 秒內的併入緩衝。

    緩衝期過後若有累積多條 → 調用 send_fn 發送合併消息。
    window=0 時跳過聚合，每條都即時轉發。
    """

    def __init__(
        self,
        window_seconds: int = 0,
        send_fn: Callable[[list[IncomingSMS]], Coroutine] | None = None,
    ):
        self._window = max(0, window_seconds)
        self._buffers: dict[tuple[str, int], list[IncomingSMS]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._send_fn = send_fn

    @property
    def window(self) -> int:
        return self._window

    async def add(self, sms: IncomingSMS) -> str:
        """返回 FORWARD（即時轉發）或 QUEUED（已入緩衝）。"""
        if self._window == 0:
            return FORWARD

        key = (sms.number, sms.sim_slot)
        async with self._lock:
            self._buffers[key].append(sms)
            if len(self._buffers[key]) == 1:
                asyncio.ensure_future(self._flush_after(key))
                return FORWARD
            return QUEUED

    @staticmethod
    def build_aggregated(batch: list[IncomingSMS]) -> str:
        """多條短信合併為一條 Telegram 消息。"""
        if not batch:
            return ""
        if len(batch) == 1:
            return format_sms(batch[0])

        lines = [format_sms(batch[0])]
        for i, sms in enumerate(batch[1:], 2):
            ts = sms.received_at.strftime("%H:%M:%S")
            lines.append(f"\n── #{i} ({ts}) ──\n{sms.body}")
        return "\n".join(lines)

    async def _flush_after(self, key: tuple[str, int]) -> None:
        await asyncio.sleep(self._window)
        async with self._lock:
            batch = self._buffers.pop(key, None)
        if batch and len(batch) > 1:
            log.info("agg flush: %d msgs from key=%s", len(batch), key)
            if self._send_fn:
                await self._send_fn(batch)

    async def flush_all(self) -> dict[tuple[str, int], list[IncomingSMS]]:
        async with self._lock:
            items = dict(self._buffers)
            self._buffers.clear()
        return items
