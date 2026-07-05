"""FastAPI 入口：POST /api/sms + GET /health。"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, HTTPException

from . import __version__
from .aggregator import FORWARD, QUEUED, SmsAggregator
from .config import get_settings
from .filter_engine import FilterEngine
from .models import ForwardResult, HealthResponse, IncomingSMS
from .telegram import send_text, send_text as _send_raw


_UNKNOWN_DEVICE = "unknown"


def _setup_logging() -> None:
    """讀取配置並初始化日誌（首次訪問時調用，避免 import 期崩潰）。"""
    s = get_settings()
    log_path = Path(s.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path, maxBytes=s.log_max_bytes, backupCount=s.log_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.basicConfig(
        level=s.log_level.upper(),
        handlers=[
            logging.StreamHandler(),
            handler,
        ],
        force=True,
    )


log = logging.getLogger("smsbridge")
_start_time = time.monotonic()

# ── 多設備心跳管理 ───────────────────────────────────────────────────────

_last_heartbeats: dict[str, float] = {}
_heartbeat_alarmed: set[str] = set()


def _record_heartbeat(device_id: str | None) -> str:
    """記錄一臺設備的心跳，返回規範化的 device_id。"""
    dev = device_id or _UNKNOWN_DEVICE
    _last_heartbeats[dev] = time.monotonic()
    _heartbeat_alarmed.discard(dev)
    return dev


def _last_heartbeat_time(device_id: str) -> float:
    return _last_heartbeats.get(device_id, _start_time)


async def _check_heartbeat_loop(app: FastAPI):
    """每 30 秒檢查所有設備心跳逾時，逐設備觸發告警。"""
    while True:
        await asyncio.sleep(30)
        s = get_settings()
        if not s.has_token:
            continue
        now = time.monotonic()
        for dev, ts in list(_last_heartbeats.items()):
            if dev in _heartbeat_alarmed:
                continue
            elapsed = now - ts
            if elapsed > s.heartbeat_timeout:
                _heartbeat_alarmed.add(dev)
                log.warning("heartbeat timeout %.0fs — device=%s sending alert", elapsed, dev)
                text = (
                    "🚨 <b>SMSBridge 設備離線告警</b>\n\n"
                    f"<b>設備</b>：<code>{dev}</code>\n"
                    f"超過 {s.heartbeat_timeout} 秒未發送心跳。\n"
                    "可能原因：手機重啟、USB 斷線、App 被殺後台。\n"
                    "請檢查 USB 連接並重啟 SMSBridge App。"
                )
                await _send_raw(text, s)


# ── 生命週期 ─────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服務器啟動時初始化日誌、過濾引擎、消息聚合器、心跳監控。"""
    heartbeat_task: asyncio.Task | None = None
    try:
        _setup_logging()
        s = get_settings()

        # 過濾引擎（全域共享 — 所有設備使用同一組過濾規則）
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

        # 心跳監控（多設備支援就緒）
        global _last_heartbeats, _heartbeat_alarmed
        _last_heartbeats.clear()
        _heartbeat_alarmed.clear()
        heartbeat_task = asyncio.create_task(_check_heartbeat_loop(app))

        if s.has_token:
            log.info(
                "smsbridge v%s ready @ http://%s:%s  filter=%s agg=%ss heartbeat_timeout=%ss",
                __version__, s.server_host, s.server_port,
                "on" if s.filter_enabled and (s.filter_keywords_block or s.filter_regex_block) else "off",
                s.aggregate_window or "off",
                s.heartbeat_timeout,
            )
        else:
            log.warning("telegram bot token not configured — /api/sms will return 503")
    except Exception as exc:
        logging.basicConfig(level="WARNING", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        logging.getLogger("smsbridge").warning("lifespan init degraded: %s — /api/sms will return 503", exc)
    yield
    # 關閉心跳監控
    if heartbeat_task:
        heartbeat_task.cancel()
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

# Web 管理面板（P2-9）
from .web import router as web_router
try:
    app.include_router(web_router)
    log.info("web panel mounted at / and /settings")
except Exception as exc:
    # Jinja2 模板缺失時不阻礙核心服務
    log.warning("web panel not mounted: %s", exc)


@app.get("/health", response_model=HealthResponse)
async def health(device_id: str | None = None) -> HealthResponse:
    """手機端心跳檢測。支援多設備：傳送 device_id 參數即可分設備記錄。"""
    dev = _record_heartbeat(device_id)
    log.debug("heartbeat received device=%s", dev)
    return HealthResponse(
        version=__version__,
        uptime_seconds=time.monotonic() - _start_time,
    )


@app.get("/health/devices")
async def device_health() -> dict[str, float]:
    """返回所有已知設備的上次心跳時間（Monotonic 時間戳）。"""
    return dict(_last_heartbeats)


@app.post("/api/sms", response_model=ForwardResult)
async def receive_sms(payload: IncomingSMS) -> ForwardResult:
    """手機端推送短信。流程：過濾 → 聚合 → 發送。"""
    try:
        settings = get_settings()
    except Exception:
        raise HTTPException(status_code=503, detail="telegram not configured")
    if not settings.has_token:
        raise HTTPException(status_code=503, detail="telegram bot token not configured")

    dev = payload.device_id or _UNKNOWN_DEVICE
    log.info("received sms device=%s from=%s sim=%s body=%r",
             dev, payload.number, payload.sim_slot, payload.body[:60])

    # 1. 過濾（全域規則）
    if not getattr(app.state, "filter", None) or not app.state.filter.should_forward(payload):
        return ForwardResult(ok=True, status="filtered")

    # 2. 聚合（全域 buffer，但自動以 number+sim_slot 為 key）
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