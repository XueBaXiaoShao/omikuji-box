"""中文/日文语言切换测试。"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from io import BytesIO

from nonebot.adapters.onebot.v11 import Message
from PIL import Image

from omikuji_box import card, content, content_ja, draw, settings


class _Stop(Exception):
    pass


class _Matcher:
    def __init__(self) -> None:
        self.sent: list = []

    async def finish(self, message=None) -> None:
        self.sent.append(message)
        raise _Stop()


class _Event:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.group_id = 912875556

    def get_plaintext(self) -> str:
        return "/omikuji settings JP on"


async def _run(coro) -> None:
    try:
        await coro
    except _Stop:
        pass


def test_japanese_pools_match_chinese_order() -> None:
    for rank, zh_pool in content.LUCKY_ITEMS_BY_RANK.items():
        ja_pool = content_ja.LUCKY_ITEMS_BY_RANK[rank]
        assert len(ja_pool) == len(zh_pool)
    assert len(content_ja.LUCKY_COLORS) == len(content.LUCKY_COLORS)
    assert len(content_ja.LUCKY_DIRECTIONS) == len(content.LUCKY_DIRECTIONS)
    assert content_ja.RARE_LUCKY_ITEMS_BY_RANK.keys() == {"大吉"}


def test_settings_switches_language(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    assert settings.get_lang(111) == "zh"
    assert settings.set_lang(111, "ja") == "ja"
    assert settings.get_lang(111) == "ja"
    assert settings.set_lang(111, "zh") == "zh"
    assert settings.get_lang(111) == "zh"


def test_draw_language_switch_keeps_roll(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    day = date(2026, 10, 26)
    settings.set_lang(123, "zh")
    zh_result = draw.draw(123, day)
    settings.set_lang(123, "ja")
    ja_result = draw.draw(123, day)

    assert zh_result.rank == ja_result.rank
    assert [item.level for item in zh_result.categories] == [
        item.level for item in ja_result.categories
    ]
    assert zh_result.lucky_color_hex == ja_result.lucky_color_hex
    assert zh_result.lucky_number == ja_result.lucky_number
    assert zh_result.number == ja_result.number
    assert ja_result.lang == "ja"
    assert "今日の運勢" in draw.caption(ja_result)
    assert "同じ日の結果" in draw.caption(ja_result)


def test_japanese_card_renders(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    settings.set_lang(123, "ja")
    result = draw.draw(123, date(2026, 10, 26))
    png = card.render_card(result)
    assert png.startswith(b"\x89PNG")
    assert Image.open(BytesIO(png)).size == (card.WIDTH, card.HEIGHT)


async def test_settings_command(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OMIKUJI_ALLOWED_USERS", "*")
    matcher = _Matcher()
    await _run(
        __import__("omikuji_box.commands", fromlist=["handle_omikuji"]).handle_omikuji(
            _Event(111), matcher, Message("settings JP on")
        )
    )
    assert settings.get_lang(111) == "ja"
    assert "日本語" in str(matcher.sent[-1])

    matcher2 = _Matcher()
    from omikuji_box import commands

    await _run(
        commands.handle_omikuji(
            _Event(111), matcher2, Message("settings JP off")
        )
    )
    assert settings.get_lang(111) == "zh"
    assert "中文" in str(matcher2.sent[-1])
