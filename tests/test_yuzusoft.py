"""柚子社幸运角色加载测试。"""

from __future__ import annotations

import json
from datetime import date

from omikuji_box import draw, yuzusoft


def _write_character(
    root,
    game: str,
    filename: str,
    *,
    name: str,
    cn_name: str,
    sex: str = "f",
    sexual: int = 0,
    url: str = "https://example.invalid/ch.jpg",
) -> None:
    game_dir = root / game
    char_dir = game_dir / "角色"
    char_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "游戏介绍.json").write_text(
        json.dumps(
            {"title": game, "cn_title": "测试作品"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (char_dir / filename).write_text(
        json.dumps(
            {
                "name": name,
                "original": name,
                "cn_name": cn_name,
                "sex": sex,
                "image": {"url": url, "sexual": sexual},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_pick_filters_and_uses_chinese_work(monkeypatch, tmp_path) -> None:
    root = tmp_path / "lib" / "ゆずソフト"
    _write_character(
        root,
        "Game",
        "a.json",
        name="四季 ナツメ",
        cn_name="四季夏目",
    )
    _write_character(
        root,
        "Game",
        "b.json",
        name="NSFW",
        cn_name="不可用",
        sexual=1,
    )
    _write_character(
        root,
        "Game",
        "c.json",
        name="Male",
        cn_name="男性",
        sex="m",
    )
    monkeypatch.setenv("OMIKUJI_LIBRARY_DIR", str(tmp_path / "lib"))
    yuzusoft._characters = None
    yuzusoft._work_cache.clear()

    character = yuzusoft.pick(1, "2026-10-26")
    assert character is not None
    assert character.name == "四季夏目"
    assert character.work == "测试作品"
    assert character.image_url.endswith(".jpg")


def test_pick_returns_none_without_library(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_LIBRARY_DIR", str(tmp_path / "missing"))
    yuzusoft._characters = None
    yuzusoft._work_cache.clear()
    assert yuzusoft.pick(1, "2026-10-26") is None


def _write_state(tmp_path, record: dict | None) -> None:
    payload = {"version": 1, "users": {}}
    if record is not None:
        payload["users"]["123"] = record
    (tmp_path / "waifu_state.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def test_user_waifu_uses_today_yuzuwaifu(monkeypatch, tmp_path) -> None:
    _write_state(
        tmp_path,
        {
            "date": "2026-10-26",
            "source": "yuzu",
            "name": "Shiina Yuki",
            "original": "椎名 雪",
            "image_url": "https://example.invalid/yuki.jpg",
            "vns": [{"id": "v55002", "title": "ハッピーウィークエンド"}],
        },
    )
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OMIKUJI_LIBRARY_DIR", str(tmp_path / "missing"))

    character = yuzusoft.user_waifu(123, "2026-10-26")
    assert character is not None
    assert character.name == "椎名 雪"
    assert character.work == "ハッピーウィークエンド"
    assert character.image_url.endswith("yuki.jpg")


def test_user_waifu_uses_library_chinese_name_and_work(
    monkeypatch, tmp_path
) -> None:
    root = tmp_path / "lib" / "ゆずソフト"
    _write_character(
        root,
        "Game",
        "a.json",
        name="四季 ナツメ",
        cn_name="四季夏目",
    )
    _write_state(
        tmp_path,
        {
            "date": "2026-10-26",
            "source": "yuzu",
            "name": "Shiki Natsume",
            "original": "四季 ナツメ",
            "image_url": "https://example.invalid/old.jpg",
            "library_path": "ゆずソフト/Game/角色/a.json",
            "vns": [{"id": "v1", "title": "Game"}],
        },
    )
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OMIKUJI_LIBRARY_DIR", str(tmp_path / "lib"))
    yuzusoft._work_cache.clear()

    character = yuzusoft.user_waifu(123, "2026-10-26")
    assert character is not None
    assert character.name == "四季夏目"
    assert character.work == "测试作品"
    assert character.image_url == "https://example.invalid/ch.jpg"


def test_user_waifu_ignores_non_yuzu_and_other_days(
    monkeypatch, tmp_path
) -> None:
    _write_state(
        tmp_path,
        {
            "date": "2026-10-26",
            "source": "waifu",
            "name": "Other",
            "image_url": "https://example.invalid/other.jpg",
        },
    )
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    assert yuzusoft.user_waifu(123, "2026-10-26") is None
    assert yuzusoft.user_waifu(123, "2026-10-27") is None


def test_draw_prefers_user_yuzuwaifu(monkeypatch, tmp_path) -> None:
    _write_state(
        tmp_path,
        {
            "date": "2026-10-26",
            "source": "yuzu",
            "name": "Shiina Yuki",
            "original": "椎名 雪",
            "image_url": "https://example.invalid/yuki.jpg",
            "vns": [{"id": "v55002", "title": "ハッピーウィークエンド"}],
        },
    )
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OMIKUJI_LIBRARY_DIR", str(tmp_path / "missing"))
    monkeypatch.setattr(
        yuzusoft,
        "pick",
        lambda user_id, day, lang="zh": yuzusoft.YuzuCharacter(
            name="随机角色",
            original="随机角色",
            work="随机作品",
            image_url="https://example.invalid/random.jpg",
        ),
    )

    result = draw.draw(123, date(2026, 10, 26))
    assert result.yuzu_name == "椎名 雪"
    assert result.yuzu_work == "ハッピーウィークエンド"
