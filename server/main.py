"""FastAPI 入口：POST /api/sms + GET /health。"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from . import __version__
from .aggregator import FORWARD, QUEUED, SmsAggregator
from .config import get_settings
from .filter_engine import FilterEngine
from .models import ForwardResult, HealthResponse, IncomingSMS
from .telegram import send_text


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
    """服務器啟動時初始化日誌、過濾引擎、消息聚合器。"""
    try:
        _setup_logging()
        s = get_settings()

        # 過濾引擎
        app.state.filter = FilterEngine(
            keywords_block=s.filter_keywords_block,
            regex_block=s.filter_regex_block,
            enabled=s.filter_enabled,
        )

        # 消息聚合器（send callback 由 lifespan closure 持有 settings）
        async def _send_aggregated(batch: list[IncomingSMS]) -> None:
            settings = get_settings()
            text = SmsAggregator.build_aggregated(batch)
            ok, _, err = await send_text(text, settings)
            if not ok:
                log.error("aggregated send failed: %s", err)

        app.state.aggregator = SmsAggregator(
            window_seconds=s.aggregate_window,
            send_fn=_send_aggregated,
        )

        if s.has_token:
            log.info(
                "smsbridge v%s ready @ http://%s:%s  filter=%s agg=%ss",
                __version__, s.server_host, s.server_port,
                "on" if s.filter_enabled and (s.filter_keywords_block or s.filter_regex_block) else "off",
                s.aggregate_window or "off",
            )
        else:
            log.warning("telegram bot token not configured — /api/sms will return 503")
    except Exception as exc:
        logging.basicConfig(level="WARNING", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        logging.getLogger("smsbridge").warning("lifespan init degraded: %s — /api/sms will return 503", exc)
    yield
    # 關閉前沖刷聚合 buffer
    leftovers = await app.state.aggregator.flush_all()
    for key, batch in leftovers.items():
        if len(batch) > 1:
            log.info("shutdown flush %d msgs for key=%s", len(batch), key)


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
    """手機端推送短信。流程：過濾 → 聚合 → 發送。"""
    try:
        settings = get_settings()
    except Exception:
        raise HTTPException(status_code=503, detail="telegram not configured")
    if not settings.has_token:
        raise HTTPException(status_code=503, detail="telegram bot token not configured")

    log.info("received sms from=%s sim=%s body=%r", payload.number, payload.sim_slot, payload.body[:60])

    # 1. 過濾
    if not getattr(app.state, "filter", None) or not app.state.filter.should_forward(payload):
        return ForwardResult(ok=True, status="filtered")

    # 2. 聚合
    action = await app.state.aggregator.add(payload)
    if action == QUEUED:
        return ForwardResult(ok=True, status="queued")

    # 3. 轉發
    from .telegram import send_sms
    ok, delivered, err = await send_sms(payload, settings)
    if ok:
        return ForwardResult(ok=True, target_chats=delivered, status="delivered")

    log.error("forward failed: %s", err)
    return ForwardResult(ok=False, target_chats=delivered, error=err, status="failed")