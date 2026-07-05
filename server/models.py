"""短信數據模型：手機端 POST 過來的結構。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IncomingSMS(BaseModel):
    """手機端 POST /api/sms 的請求體。"""

    sender: str = Field(..., description="發件人姓名（通訊錄匹配後），可能為空字符串")
    number: str = Field(..., description="發件人手機號")
    body: str = Field(..., description="短信正文")
    received_at: datetime = Field(..., description="短信接收時間（手機本地時區 ISO 8601）")
    sim_slot: int = Field(0, ge=0, le=3, description="SIM 卡槽位，0/1 為主流，預設 0")
    device_id: str | None = Field(None, description="設備唯一標識（多用戶/多手機場景）")

    def summary(self) -> str:
        sim = f"SIM{self.sim_slot}" if self.sim_slot else "SIM?"
        who = self.sender or self.number
        return f"[{sim}] {who}: {self.body}"


class ForwardResult(BaseModel):
    """POST /api/sms 的響應體。"""

    ok: bool
    target_chats: list[int] = Field(default_factory=list)
    error: str | None = None
    status: Literal["delivered", "queued", "failed"] = "delivered"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    uptime_seconds: float


class SettingsRead(BaseModel):
    """Web 面板設定頁面的唯讀配置視圖。"""

    server_host: str
    server_port: int
    telegram_bot_token: str
    telegram_chat_ids: list[int]
    telegram_parse_mode: str
    log_level: str
    log_file: str
    filter_enabled: bool
    filter_keywords_block: list[str]
    filter_regex_block: list[str]
    aggregate_window: int
    heartbeat_timeout: int