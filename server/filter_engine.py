"""短信過濾引擎：關鍵詞 / 正則黑名單。"""
from __future__ import annotations

import logging
import re

from .models import IncomingSMS

log = logging.getLogger(__name__)


class FilterEngine:
    """基於配置規則判斷短信是否應該被轉發。"""

    def __init__(
        self,
        keywords_block: list[str] | None = None,
        regex_block: list[str] | None = None,
        enabled: bool = True,
    ):
        self._enabled = enabled
        self._keywords = [k.lower() for k in (keywords_block or [])]
        self._patterns = [re.compile(p) for p in (regex_block or [])]
        if enabled:
            log.info(
                "filter loaded: %d keywords, %d regex patterns",
                len(self._keywords),
                len(self._patterns),
            )

    def should_forward(self, sms: IncomingSMS) -> bool:
        """返回 True 表示該放行（轉發），False 表示攔截。"""
        if not self._enabled or (not self._keywords and not self._patterns):
            return True

        body_lower = sms.body.lower()

        for kw in self._keywords:
            if kw in body_lower:
                log.info("filter [keyword] blocked %s  kw=%r", sms.summary(), kw)
                return False

        for pat in self._patterns:
            m = pat.search(sms.body)
            if m:
                log.info("filter [regex] blocked %s  pat=%s", sms.summary(), pat.pattern)
                return False

        return True
