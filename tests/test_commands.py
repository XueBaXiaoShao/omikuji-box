"""命令入口与群开关测试。"""

from __future__ import annotations

import json
from datetime import date

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from omikuji_box import commands, draw, state, yuzu_state, yuzusoft


class _Stop(Exception):
    pass


class _Matcher:
    def __init__(self) -> None:
        self.sent: list = []

    async def finish(self, message=None) -> None:
        self.sent.append(message)
        raise _Stop()


class _Event:
    def __init__(
        self,
        user_id: int,
        group_id: int | None = 912875556,
        text: str = "/omikuji",
    ) -> None:
        self.user_id = user_id
        self.group_id = group_id
        self._text = text

    def get_plaintext(self) -> str:
        return self._text


async def _run(coro) -> None:
    try:
        await coro
    except _Stop:
        pass


def _write_switches(tmp_path, payload: dict) -> None:
    (tmp_path / "plugin_switches.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def test_requires_slash_prefix() -> None:
    assert commands._is_slash_omikuji(_Event(1, text="/omikuji"))
    assert commands._is_slash_omikuji(_Event(1, text="/おみくじ"))
    assert not commands._is_slash_omikuji(_Event(1, text="omikuji"))
    assert not commands._is_slash_omikuji(_Event(1, text="おみくじ"))
    assert not commands._is_slash_omikuji(_Event(1, text="今天的 omikuji"))


def test_group_switch_defaults_to_enabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    assert commands._enabled_for_event(_Event(1)) is True


def test_group_switch_can_disable(monkeypatch, tmp_path) -> None:
    _write_switches(
        tmp_path,
        {"groups": {"912875556": {"omikuji_box": False}}},
    )
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    assert commands._enabled_for_event(_Event(1)) is False
    assert commands._enabled_for_event(_Event(1, group_id=123)) is True


def test_allowed_users_env_override(monkeypatch) -> None:
    monkeypatch.setenv("OMIKUJI_ALLOWED_USERS", "111，222")
    assert commands._allowed_users() == {111, 222}


def test_allowed_users_wildcard_opens_to_all(monkeypatch) -> None:
    monkeypatch.setenv("OMIKUJI_ALLOWED_USERS", "*")
    assert commands._allowed_users() is None


async def test_handler_sends_image(monkeypatch) -> None:
    monkeypatch.setattr(commands, "_allowed_users", lambda: {111})
    monkeypatch.setattr(commands, "_enabled_for_event", lambda event: True)

    async def fake_portrait(url: str):
        return None

    monkeypatch.setattr(commands.yuzusoft, "fetch_portrait", fake_portrait)
    monkeypatch.setattr(commands.yuzusoft, "logo_path", lambda: None)
    monkeypatch.setattr(commands.card, "render_card", lambda *args: b"PNG")
    matcher = _Matcher()
    await _run(commands.handle_omikuji(_Event(111), matcher, Message("")))
    text = str(matcher.sent[-1])
    assert "base64://" in text
    assert "[CQ:at,qq=111" in text
    assert "同一天结果固定" in text


async def test_handler_ignores_unauthorized_user(monkeypatch) -> None:
    monkeypatch.setattr(commands, "_allowed_users", lambda: {111})
    matcher = _Matcher()
    await _run(commands.handle_omikuji(_Event(222), matcher, Message("")))
    assert matcher.sent == []


async def test_handler_rejects_disabled_group(monkeypatch) -> None:
    monkeypatch.setattr(commands, "_allowed_users", lambda: {111})
    monkeypatch.setattr(commands, "_enabled_for_event", lambda event: False)
    matcher = _Matcher()
    await _run(commands.handle_omikuji(_Event(111), matcher, Message("")))
    assert "未开启" in str(matcher.sent[-1])


def _write_admin(tmp_path, admin_id: int) -> None:
    (tmp_path / "admin_ids.json").write_text(
        json.dumps({"version": 3, "admins": [admin_id]}),
        encoding="utf-8",
    )


async def test_reset_by_qq_admin(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    _write_admin(tmp_path, 999)
    matcher = _Matcher()
    await _run(
        commands.handle_omikuji(
            _Event(999), matcher, Message("reset 123")
        )
    )
    assert "已重置用户 123" in str(matcher.sent[-1])
    assert state.nonce(123, draw.today_iso()) != 0


async def test_reset_clears_omikuji_yuzu_pick(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    _write_admin(tmp_path, 999)
    today = draw.today_iso()
    yuzu_state.record(
        123,
        today,
        yuzusoft.YuzuCharacter(
            name="ヒロイン",
            original="ヒロイン",
            work="ゲーム",
            image_url="https://img/1.jpg",
            id="c1",
            library_path="ゆずソフト/ゲーム/角色/ヒロイン.json",
        ),
    )
    matcher = _Matcher()
    await _run(
        commands.handle_omikuji(
            _Event(999), matcher, Message("reset 123")
        )
    )
    assert yuzu_state.get(123, today) is None


async def test_reset_by_at_admin(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    _write_admin(tmp_path, 999)
    event = _Event(999)
    event.message = Message([MessageSegment.at(456)])
    matcher = _Matcher()
    await _run(commands.handle_omikuji(event, matcher, Message("reset")))
    assert "已重置用户 456" in str(matcher.sent[-1])
    assert state.nonce(456, draw.today_iso()) != 0


async def test_reset_requires_admin(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    _write_admin(tmp_path, 999)
    matcher = _Matcher()
    await _run(
        commands.handle_omikuji(
            _Event(111), matcher, Message("reset 123")
        )
    )
    assert "只有管理员" in str(matcher.sent[-1])
    assert state.nonce(123, draw.today_iso()) == 0


def test_reset_changes_daily_result(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(state.secrets, "randbelow", lambda n: 999)
    day = date(2026, 10, 26)
    before = draw.draw(123, day)
    state.reset(123, day.isoformat())
    after = draw.draw(123, day)
    assert before != after
