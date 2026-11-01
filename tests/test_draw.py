"""确定性抽签测试。"""

from __future__ import annotations

from datetime import date

from omikuji_box import content, draw, yuzu_state, yuzusoft


def test_same_user_same_day_is_stable() -> None:
    day = date(2026, 10, 26)
    first = draw.draw(123456, day)
    second = draw.draw(123456, day)
    assert first == second


def test_different_user_or_day_changes_result() -> None:
    day = date(2026, 10, 26)
    base = draw.draw(123456, day)
    assert base != draw.draw(123457, day)
    assert base != draw.draw(123456, date(2026, 10, 27))


def test_result_fields_are_complete() -> None:
    result = draw.draw(42, date(2026, 10, 26))
    assert result.rank in content.RANKS
    assert len(result.categories) == len(content.CATEGORIES)
    for item in result.categories:
        assert item.level in content.CATEGORY_LEVELS
        assert item.advice
    allowed = set(content.LUCKY_ITEMS_BY_RANK[result.rank]) | set(
        content.RARE_LUCKY_ITEMS_BY_RANK.get(result.rank, ())
    )
    assert result.lucky_item in allowed
    assert result.lucky_item_rare == (
        result.lucky_item in content.RARE_LUCKY_ITEMS
    )
    assert (result.lucky_color_name, result.lucky_color_hex) in content.LUCKY_COLORS
    assert result.lucky_direction in content.LUCKY_DIRECTIONS
    assert result.lucky_number in content.LUCKY_NUMBERS
    assert 1 <= result.number <= 100


def test_all_ranks_are_reachable() -> None:
    day = date(2026, 10, 26)
    ranks = {draw.draw(user_id, day).rank for user_id in range(2000)}
    assert ranks == set(content.RANKS)


def test_caption_mentions_rank_and_fixed_result() -> None:
    result = draw.draw(42, date(2026, 10, 26))
    text = draw.caption(result)
    assert result.rank in text
    assert "同一天结果固定" in text


def test_rare_item_only_for_daikichi(monkeypatch) -> None:
    day = date(2026, 10, 26)
    daikichi_weights = tuple(
        1 if rank == "大吉" else 0 for rank in content.RANKS
    )
    monkeypatch.setattr(content, "RANK_WEIGHTS", daikichi_weights)
    monkeypatch.setattr(draw.config, "rare_item_chance", 1.0)
    result = draw.draw(123, day)
    assert result.rank == "大吉"
    assert result.lucky_item == "月望的白丝"
    assert result.lucky_item_rare is True

    monkeypatch.setattr(draw.config, "rare_item_chance", 0.0)
    result = draw.draw(123, day)
    assert result.lucky_item in content.LUCKY_ITEMS_BY_RANK["大吉"]
    assert result.lucky_item_rare is False


def test_rare_item_not_available_for_chuukichi(monkeypatch) -> None:
    day = date(2026, 10, 26)
    chuukichi_weights = tuple(
        1 if rank == "中吉" else 0 for rank in content.RANKS
    )
    monkeypatch.setattr(content, "RANK_WEIGHTS", chuukichi_weights)
    monkeypatch.setattr(draw.config, "rare_item_chance", 1.0)
    result = draw.draw(123, day)
    assert result.rank == "中吉"
    assert result.lucky_item in content.LUCKY_ITEMS_BY_RANK["中吉"]
    assert result.lucky_item_rare is False


def test_every_lucky_item_is_assigned_to_a_rank() -> None:
    used = set()
    for pool in content.LUCKY_ITEMS_BY_RANK.values():
        used.update(pool)
    used.update(content.RARE_LUCKY_ITEMS)
    assert used == set(content.LUCKY_ITEMS) | set(content.RARE_LUCKY_ITEMS)


def test_lucky_items_match_rank_pools() -> None:
    day = date(2026, 10, 26)
    for user_id in range(200):
        result = draw.draw(user_id, day)
        allowed = set(content.LUCKY_ITEMS_BY_RANK[result.rank]) | set(
            content.RARE_LUCKY_ITEMS_BY_RANK.get(result.rank, ())
        )
        assert result.lucky_item in allowed


def test_omikuji_records_yuzu_pick(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    fake = yuzusoft.YuzuCharacter(
        name="ヒロイン",
        original="ヒロイン",
        work="ゲーム",
        image_url="https://img/1.jpg",
        id="c1",
        library_path="ゆずソフト/ゲーム/角色/ヒロイン.json",
    )
    monkeypatch.setattr(yuzusoft, "user_waifu", lambda *args, **kwargs: None)
    monkeypatch.setattr(yuzusoft, "pick", lambda *args, **kwargs: fake)

    day = date(2026, 10, 26)
    result = draw.draw(123, day)
    record = yuzu_state.get(123, day.isoformat())

    assert result.yuzu_name == "ヒロイン"
    assert record is not None
    assert record["character_id"] == "c1"
    assert record["library_path"].endswith("ヒロイン.json")


def test_yuzu_state_clear(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OMIKUJI_DATA_DIR", str(tmp_path))
    fake = yuzusoft.YuzuCharacter(
        name="ヒロイン",
        original="ヒロイン",
        work="ゲーム",
        image_url="https://img/1.jpg",
        id="c1",
        library_path="ゆずソフト/ゲーム/角色/ヒロイン.json",
    )
    day = date(2026, 10, 26)
    yuzu_state.record(123, day.isoformat(), fake)
    assert yuzu_state.get(123, day.isoformat()) is not None

    yuzu_state.clear(123, day.isoformat())
    assert yuzu_state.get(123, day.isoformat()) is None
