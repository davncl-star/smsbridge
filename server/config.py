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

    # 內容過濾
    filter_enabled: bool = True
    filter_keywords_block: list[str] = Field(
        default_factory=list,
        description="關鍵詞黑名單，命中則不轉發。逗號分隔或 JSON 數組",
    )
    filter_regex_block: list[str] = Field(
        default_factory=list,
        description="正則黑名單，命中則不轉發。逗號分隔或 JSON 數組",
    )

    @field_validator("filter_keywords_block", "filter_regex_block", mode="before")
    @classmethod
    def _parse_str_list(cls, v):
        """接受 list / JSON 字符串 / 逗號分隔字符串。"""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    # 消息聚合
    aggregate_window: int = Field(
        0,
        ge=0,
        description="消息聚合窗口（秒），0=關閉。同一號碼在此時間內的多條短信將合併爲一條",
    )

    # 日誌（P1-5 RotatingFileHandler）
    log_level: str = "INFO"
    log_file: Path = Path("logs/smsbridge.log")
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3

    # 心跳告警（P0-2）
    heartbeat_timeout: int = Field(
        120,
        ge=30,
        description="手機心跳逾時秒數，超過此值未收到心跳則發送 Telegram 告警",
    )

    @property
    def has_token(self) -> bool:
        return bool(self.telegram_bot_token) and ":" in self.telegram_bot_token


@lru_cache
def get_settings() -> Settings:
    """單例配置。首次調用時從 .env / 環境變量讀取。"""
    return Settings()  # type: ignore[call-arg]