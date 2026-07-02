"""FastAPI 入口：POST /api/sms + GET /health。"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from . import __version__
from .config import get_settings
from .models import ForwardResult, HealthResponse, IncomingSMS
from .telegram import send_sms


def _setup_logging() -> None:
    """讀取配置並初始化日誌（首次訪問時調用，避免 import 期崩潰）。"""
    s = get_settings()
    log_path = Path(s.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=s.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )


log = logging.getLogger("smsbridge")
_start_time = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服務器啟動時初始化日誌與單例配置。

    即使 .env 缺失或 token 為空，服務器也應啟動（端點自行判斷可用性）。
    """
    try:
        _setup_logging()
        s = get_settings()
        if s.has_token:
            log.info("smsbridge v%s listening @ http://%s:%s", __version__, s.server_host, s.server_port)
        else:
            log.warning("telegram bot token not configured — /api/sms will return 503")
    except Exception as exc:
        # 配置未就緒（缺 .env 等）時仍允許服務器啟動
        logging.basicConfig(level="WARNING", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        logging.getLogger("smsbridge").warning("lifespan init degraded: %s — /api/sms will return 503", exc)
    yield


app = FastAPI(
    title="SMSBridge",
    description="SMS → Telegram forwarding over USB (ADB reverse).",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """手機端心跳檢測。"""
    return HealthResponse(
        version=__version__,
        uptime_seconds=time.monotonic() - _start_time,
    )


@app.post("/api/sms", response_model=ForwardResult)
async def receive_sms(payload: IncomingSMS) -> ForwardResult:
    """手機端推送短信。"""
    try:
        settings = get_settings()
    except Exception:
        raise HTTPException(status_code=503, detail="telegram not configured — missing .env or TELEGRAM_BOT_TOKEN")
    if not settings.has_token:
        raise HTTPException(status_code=503, detail="telegram bot token not configured")

    log.info("received sms from=%s sim=%s body=%r", payload.number, payload.sim_slot, payload.body[:60])
    ok, delivered, err = await send_sms(payload, settings)

    if ok:
        return ForwardResult(ok=True, target_chats=delivered, status="delivered")

    log.error("forward failed: %s", err)
    return ForwardResult(ok=False, target_chats=delivered, error=err, status="failed")