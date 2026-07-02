"""配置加載：優先 .env，其次環境變量。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """運行時配置。所有字段都允許從環境變量覆蓋。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = Field(..., description="@BotFather 給的 Bot Token")
    # NoDecode 避免 pydantic-settings 預設的列表解析邏輯（它會輸出單個 int 而非 list）
    telegram_chat_ids: Annotated[list[int], NoDecode] = Field(
        default_factory=list,
        description="目標 Chat ID 列表。環境變量接受逗號分隔或 JSON 數組",
    )
    telegram_parse_mode: str = "HTML"
    telegram_disable_preview: bool = True

    @field_validator("telegram_chat_ids", mode="before")
    @classmethod
    def _parse_chat_ids(cls, v):
        """接受 list / JSON 字符串 / 逗號分隔字符串。"""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    # 服務器
    server_host: str = "127.0.0.1"
    server_port: int = 8580

    # 日誌
    log_level: str = "INFO"
    log_file: Path = Path("logs/smsbridge.log")

    @property
    def has_token(self) -> bool:
        return bool(self.telegram_bot_token) and ":" in self.telegram_bot_token


@lru_cache
def get_settings() -> Settings:
    """單例配置。首次調用時從 .env / 環境變量讀取。"""
    return Settings()  # type: ignore[call-arg]