"""過濾引擎測試。"""
from __future__ import annotations

from server.filter_engine import FilterEngine
from server.models import IncomingSMS


def _sms(body: str, sender: str = "Dav", number: str = "+8613800000000") -> IncomingSMS:
    return IncomingSMS(
        sender=sender, number=number, body=body,
        received_at="2026-07-03T18:00:00", sim_slot=0,
    )


def test_no_rules_forward_all():
    f = FilterEngine(enabled=True)
    assert f.should_forward(_sms("anything")) is True


def test_disabled_forward_all():
    f = FilterEngine(keywords_block=["spam"], enabled=False)
    assert f.should_forward(_sms("this is spam")) is True


def test_keyword_block():
    f = FilterEngine(keywords_block=["广告", "spam"])
    assert f.should_forward(_sms("正常短信")) is True
    assert f.should_forward(_sms("这里有广告")) is False  # simplified Chinese
    assert f.should_forward(_sms("SPAM message")) is False  # case-insensitive


def test_regex_block():
    f = FilterEngine(regex_block=[r"\d{6,}"])
    assert f.should_forward(_sms("验证码是 123456")) is False
    assert f.should_forward(_sms("hello")) is True


def test_keyword_and_regex():
    f = FilterEngine(keywords_block=["spam"], regex_block=[r"\d{6}"])
    assert f.should_forward(_sms("spam")) is False
    assert f.should_forward(_sms("code 123456")) is False
    assert f.should_forward(_sms("normal text")) is True


def test_empty_keywords_no_error():
    f = FilterEngine(keywords_block=[], regex_block=[])
    assert f.should_forward(_sms("anything")) is True


def test_none_keywords():
    f = FilterEngine(keywords_block=None, regex_block=None)
    assert f.should_forward(_sms("anything")) is True
