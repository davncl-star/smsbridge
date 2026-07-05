"""SMSBridge Web 管理面板（P2-9）。"""
from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path

from typing import Any

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from starlette.requests import Request
import jinja2

from .. import __version__
from ..config import get_settings
from ..models import SettingsRead

router = APIRouter(prefix="", tags=["web"])

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,
)


def _get_uptime(start_time: float) -> str:
    """格式化運行時間字串。"""
    elapsed = time.monotonic() - start_time
    hours, remainder = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def _human_time(monotonic_ts: float) -> str:
    """將 monotonic 時間戳轉為人類可讀的「N 秒前」格式。"""
    elapsed = time.monotonic() - monotonic_ts
    if elapsed < 60:
        return f"{int(elapsed)}s ago"
    if elapsed < 3600:
        return f"{int(elapsed // 60)}m {int(elapsed % 60)}s ago"
    h, m = divmod(int(elapsed // 60), 60)
    return f"{h}h {m}m ago"


# ── 路由 ─────────────────────────────────────────────────────────────────


def _render(name: str, **context: Any) -> HTMLResponse:
    """用 jinja2 Environment 直接渲染模板。"""
    html = _jinja_env.get_template(name).render(**context)
    return HTMLResponse(html)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    """儀表板主頁。"""
    from ..main import app, _last_heartbeats, _start_time

    s = get_settings()
    now = time.monotonic()
    # 只顯示最近 2×heartbeat_timeout 內有心跳的設備
    threshold = now - s.heartbeat_timeout * 2
    devices = []
    for dev_id, ts in sorted(_last_heartbeats.items()):
        if ts < threshold:
            continue
        devices.append({
            "id": dev_id,
            "last_seen": _human_time(ts),
        })

    fe = getattr(app.state, "filter", None)
    agg = getattr(app.state, "aggregator", None)

    return _render("dashboard.html",
        version=__version__,
        uptime=_get_uptime(_start_time),
        devices=devices,
        filter_enabled=fe.enabled if fe else False,
        filter_keywords=list(fe.keywords) if fe and fe.keywords else [],
        filter_patterns=[str(p) for p in (fe.patterns if fe else [])] if fe else [],
        agg_window=agg.window if agg else 0,
        server_host=s.server_host,
        server_port=s.server_port,
        log_file=str(s.log_file),
    )


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(request: Request):
    """配置頁面。"""
    s = get_settings()

    return _render("settings.html",
        version=__version__,
        config=SettingsRead(
            server_host=s.server_host,
            server_port=s.server_port,
            telegram_bot_token=s.telegram_bot_token[:8] + "***" if s.has_token else "(unset)",
            telegram_chat_ids=s.telegram_chat_ids,
            telegram_parse_mode=s.telegram_parse_mode,
            log_level=s.log_level,
            log_file=str(s.log_file),
            filter_enabled=s.filter_enabled,
            filter_keywords_block=list(s.filter_keywords_block) if s.filter_keywords_block else [],
            filter_regex_block=list(s.filter_regex_block) if s.filter_regex_block else [],
            aggregate_window=s.aggregate_window,
            heartbeat_timeout=s.heartbeat_timeout,
        ),
    )


@router.get("/api/web/filter", include_in_schema=False)
async def web_get_filter():
    """返回過濾規則（AJAX 用）。"""
    from ..main import app
    fe = getattr(app.state, "filter", None)
    if not fe:
        return {"enabled": False, "keywords": [], "patterns": []}
    return {
        "enabled": fe.enabled,
        "keywords": sorted(fe.keywords),
        "patterns": [str(p) for p in fe.patterns],
    }


@router.post("/api/web/filter/enable", include_in_schema=False)
async def web_toggle_filter(enabled: bool = Form(...)):
    """開關過濾器。"""
    from ..main import app
    from ..filter_engine import FilterEngine
    s = get_settings()
    fe = FilterEngine(
        keywords_block=s.filter_keywords_block,
        regex_block=s.filter_regex_block,
        enabled=enabled,
    )
    app.state.filter = fe
    return {"ok": True, "enabled": enabled}


@router.post("/api/web/filter/add", include_in_schema=False)
async def web_add_keyword(keyword: str = Form(...)):
    """添加關鍵詞（立即寫入 .env 並生效）。"""
    from ..main import app
    s = get_settings()
    new_list = list(s.filter_keywords_block) if s.filter_keywords_block else []
    if keyword not in new_list:
        new_list.append(keyword)
        _update_env_key("FILTER_KEYWORDS_BLOCK", ",".join(new_list))
    # 重新載入過濾器
    from ..filter_engine import FilterEngine
    s2 = get_settings(force=True)
    app.state.filter = FilterEngine(
        keywords_block=s2.filter_keywords_block,
        regex_block=s2.filter_regex_block,
        enabled=s2.filter_enabled,
    )
    return {"ok": True}


@router.post("/api/web/filter/remove", include_in_schema=False)
async def web_remove_keyword(keyword: str = Form(...)):
    """移除關鍵詞。"""
    from ..main import app
    s = get_settings()
    new_list = [k for k in (s.filter_keywords_block or []) if k != keyword]
    _update_env_key("FILTER_KEYWORDS_BLOCK", ",".join(new_list))
    from ..filter_engine import FilterEngine
    s2 = get_settings(force=True)
    app.state.filter = FilterEngine(
        keywords_block=s2.filter_keywords_block,
        regex_block=s2.filter_regex_block,
        enabled=s2.filter_enabled,
    )
    return {"ok": True}


@router.post("/api/web/filter/regex/add", include_in_schema=False)
async def web_add_regex(pattern: str = Form(...)):
    """添加正則表達式過濾。"""
    from ..main import app
    s = get_settings()
    new_list = list(s.filter_regex_block) if s.filter_regex_block else []
    if pattern not in new_list:
        new_list.append(pattern)
        _update_env_key("FILTER_REGEX_BLOCK", ",".join(new_list))
    from ..filter_engine import FilterEngine
    s2 = get_settings(force=True)
    app.state.filter = FilterEngine(
        keywords_block=s2.filter_keywords_block,
        regex_block=s2.filter_regex_block,
        enabled=s2.filter_enabled,
    )
    return {"ok": True}


@router.post("/api/web/filter/regex/remove", include_in_schema=False)
async def web_remove_regex(pattern: str = Form(...)):
    """移除正則表達式過濾。"""
    from ..main import app
    s = get_settings()
    new_list = [p for p in (s.filter_regex_block or []) if p != pattern]
    _update_env_key("FILTER_REGEX_BLOCK", ",".join(new_list))
    from ..filter_engine import FilterEngine
    s2 = get_settings(force=True)
    app.state.filter = FilterEngine(
        keywords_block=s2.filter_keywords_block,
        regex_block=s2.filter_regex_block,
        enabled=s2.filter_enabled,
    )
    return {"ok": True}


@router.post("/api/web/agg/set", include_in_schema=False)
async def web_set_agg(window: int = Form(...)):
    """設定聚合窗口。"""
    from ..main import app
    from ..aggregator import SmsAggregator
    _update_env_key("AGGREGATE_WINDOW", str(window))
    from ..config import get_settings as gs
    s = gs(force=True)

    async def _send_aggregated(batch):
        settings = gs()
        from ..telegram import send_text
        text = SmsAggregator.build_aggregated(batch)
        ok, _, err = await send_text(text, settings)
        if not ok:
            import logging
            logging.getLogger("smsbridge").error("aggregated send failed: %s", err)

    old_agg = getattr(app.state, "aggregator", None)
    # 沖刷舊 buffer
    if old_agg:
        import asyncio
        await old_agg.flush_all()

    app.state.aggregator = SmsAggregator(
        window_seconds=s.aggregate_window,
        send_fn=_send_aggregated,
    )
    return {"ok": True, "window": s.aggregate_window}


@router.post("/api/web/heartbeat/set", include_in_schema=False)
async def web_set_heartbeat(timeout: int = Form(...)):
    """設定心跳逾時秒數。"""
    _update_env_key("HEARTBEAT_TIMEOUT", str(timeout))
    from ..config import get_settings as gs
    gs(force=True)
    return {"ok": True, "timeout": timeout}


# ── 工具 ─────────────────────────────────────────────────────────────────


def _update_env_key(key: str, value: str) -> None:
    """在 .env 檔案中新增或更新一行。"""
    from ..config import find_env_path
    env_path = find_env_path()
    if not env_path:
        return
    raw = env_path.read_text(encoding="utf-8")
    marker = f"{key}="
    new_line = f"{key}={value}\n"
    if marker in raw:
        lines = raw.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(marker):
                lines[i] = new_line
                break
        raw = "".join(lines)
    else:
        raw = raw.rstrip("\n") + "\n" + new_line
    env_path.write_text(raw, encoding="utf-8")
