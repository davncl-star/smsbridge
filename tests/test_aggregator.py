"""聚合器測試。"""
from __future__ import annotations

import asyncio

import pytest

from server.aggregator import FORWARD, QUEUED, SmsAggregator
from server.models import IncomingSMS


def _sms(body: str, number: str = "+8613800000000", sim: int = 0) -> IncomingSMS:
    return IncomingSMS(
        sender="Dav" if number else "",
        number=number, body=body,
        received_at="2026-07-03T18:00:00", sim_slot=sim,
    )


@pytest.mark.asyncio
async def test_window_zero_returns_forward():
    agg = SmsAggregator(window_seconds=0)
    assert agg.window == 0
    assert await agg.add(_sms("hello")) == FORWARD


@pytest.mark.asyncio
async def test_window_zero_always_forward():
    agg = SmsAggregator(window_seconds=0)
    assert await agg.add(_sms("a")) == FORWARD
    assert await agg.add(_sms("b", number="+8613800000001")) == FORWARD
    assert await agg.add(_sms("c")) == FORWARD


@pytest.mark.asyncio
async def test_window_nonzero_first_is_forward():
    agg = SmsAggregator(window_seconds=60)
    result = await agg.add(_sms("first"))
    assert result == FORWARD


@pytest.mark.asyncio
async def test_window_nonzero_second_is_queued():
    agg = SmsAggregator(window_seconds=60)
    await agg.add(_sms("first"))
    result = await agg.add(_sms("second"))
    assert result == QUEUED


@pytest.mark.asyncio
async def test_different_numbers_not_queued():
    agg = SmsAggregator(window_seconds=60)
    await agg.add(_sms("a", number="+8613800000000"))
    result = await agg.add(_sms("b", number="+8613800000001"))
    assert result == FORWARD


@pytest.mark.asyncio
async def test_different_sim_separate_buffers():
    agg = SmsAggregator(window_seconds=60)
    await agg.add(_sms("a", sim=0))
    result = await agg.add(_sms("b", sim=1))
    assert result == FORWARD


def test_build_aggregated_single():
    batch = [_sms("hello")]
    text = SmsAggregator.build_aggregated(batch)
    assert "hello" in text
    assert "──" not in text


def test_build_aggregated_multiple():
    batch = [_sms("first"), _sms("second"), _sms("third")]
    text = SmsAggregator.build_aggregated(batch)
    assert "first" in text
    assert "second" in text
    assert "third" in text
    assert "#2" in text
    assert "#3" in text
    assert "──" in text


@pytest.mark.asyncio
async def test_flush_calls_send_fn():
    """確認 _flush_after 調用 send_fn。"""
    called = []

    async def fake_send(batch):
        called.append(batch)

    agg = SmsAggregator(window_seconds=0.05, send_fn=fake_send)
    await agg.add(_sms("first"))
    await agg.add(_sms("second"))
    await asyncio.sleep(0.15)
    assert len(called) == 1
