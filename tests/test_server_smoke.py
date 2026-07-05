"""服務器冒煙：FastAPI TestClient + httpx mock，無需真 Telegram。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def configured_env(monkeypatch):
    """設置假 Telegram 環境。"""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0000000:FAKE")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "123456789, -100987654321")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    # 清掉 lru_cache，避免跨測試污染
    from server.config import _cached_settings
    _cached_settings.cache_clear()


def test_health(configured_env) -> None:
    from server.main import app

    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime_seconds" in body
    assert body["uptime_seconds"] >= 0


def test_api_sms_unconfigured(monkeypatch) -> None:
    """未配 token 時 /api/sms 應返回 503。"""
    from server.config import _cached_settings
    from server.main import app

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_IDS", raising=False)
    _cached_settings.cache_clear()

    with TestClient(app) as client:
        resp = client.post("/api/sms", json={
            "sender": "x", "number": "+8613800000000", "body": "x",
            "received_at": "2026-06-30T17:00:00", "sim_slot": 0,
        })
    assert resp.status_code == 503


def _make_mock_resp(status_code: int, json_body: dict) -> MagicMock:
    """創建一個 httpx Response 的 mock 替身（json 是同步方法）。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    return resp


@pytest.fixture
def mock_telegram():
    """patch server.telegram.httpx.AsyncClient，返回 mock_instance。"""
    with patch("server.telegram.httpx.AsyncClient") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = instance
        yield instance


def test_api_sms_telegram_failure(configured_env, mock_telegram) -> None:
    """Telegram 返回失敗時，端點應 ok=False + 錯誤信息，不崩潰。"""
    from server.main import app

    mock_telegram.post.return_value = _make_mock_resp(401, {"ok": False, "description": "Unauthorized"})

    with TestClient(app) as client:
        resp = client.post("/api/sms", json={
            "sender": "Davncl", "number": "+8613800000000",
            "body": "test", "received_at": "2026-06-30T17:00:00",
            "sim_slot": 1, "device_id": "dev-1",
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["status"] == "failed"
    assert "Unauthorized" in (body.get("error") or "")


def test_api_sms_telegram_success(configured_env, mock_telegram) -> None:
    """Telegram 返回成功時，應 ok=True + 列出 delivered chat。"""
    from server.main import app

    mock_telegram.post.return_value = _make_mock_resp(200, {"ok": True, "result": {"message_id": 42}})

    with TestClient(app) as client:
        resp = client.post("/api/sms", json={
            "sender": "Davncl", "number": "+8613800000000",
            "body": "test", "received_at": "2026-06-30T17:00:00",
            "sim_slot": 0,
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["status"] == "delivered"
    assert set(body["target_chats"]) == {123456789, -100987654321}


def test_api_sms_validation_error(configured_env) -> None:
    """請求體缺字段應返回 422。"""
    from server.main import app

    with TestClient(app) as client:
        resp = client.post("/api/sms", json={"sender": "x"})  # 缺必要字段
    assert resp.status_code == 422