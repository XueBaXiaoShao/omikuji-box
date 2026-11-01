"""签纸图片渲染测试。"""

from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path

from PIL import Image

from omikuji_box import card, content, draw


def test_card_renders_png() -> None:
    result = draw.draw(123456, date(2026, 10, 26))
    image_bytes = card.render_card(result)
    assert image_bytes.startswith(b"\x89PNG")
    image = Image.open(BytesIO(image_bytes))
    assert image.size == (card.WIDTH, card.HEIGHT)
    assert image.mode == "RGB"


def test_card_handles_each_rank() -> None:
    for rank in content.RANKS:
        result = replace(
            draw.draw(hash(rank) & 0xFFFF, date(2026, 10, 26)),
            rank=rank,
            message=content.RANK_MESSAGES[rank],
        )
        image_bytes = card.render_card(result)
        assert image_bytes.startswith(b"\x89PNG")


def test_card_renders_yuzusoft_portrait_and_logo(tmp_path) -> None:
    source = Image.new("RGB", (120, 160), (240, 163, 60))
    portrait = BytesIO()
    source.save(portrait, format="PNG")
    logo_path = tmp_path / "Yuzusoft.png"
    source.resize((104, 60)).save(logo_path)
    result = replace(
        draw.draw(42, date(2026, 10, 26)),
        yuzu_name="四季夏目",
        yuzu_work="星光咖啡馆与死神之蝶",
        yuzu_image_url="https://example.invalid/a.jpg",
    )
    image_bytes = card.render_card(
        result, portrait.getvalue(), logo_path
    )
    assert image_bytes.startswith(b"\x89PNG")


def test_uploaded_fonts_are_selected_by_language(monkeypatch, tmp_path) -> None:
    zh_font = tmp_path / "omikuji-zh.otf"
    ja_font = tmp_path / "omikuji-ja.otf"
    shutil.copy2(card._FONT_FILE, zh_font)
    shutil.copy2(card._FONT_FILE, ja_font)
    monkeypatch.setattr(card, "_FONT_DIR", tmp_path)

    card._font_local.lang = "zh"
    assert Path(card._font(20).path) == zh_font
    card._font_local.lang = "ja"
    assert Path(card._font(20).path) == ja_font


def test_zh_rank_font_override(monkeypatch, tmp_path) -> None:
    zh_font = tmp_path / "omikuji-zh.otf"
    ja_font = tmp_path / "omikuji-ja.otf"
    rank_font = tmp_path / "omikuji-rank-zh.otf"
    for path in (zh_font, ja_font, rank_font):
        shutil.copy2(card._FONT_FILE, path)
    monkeypatch.setattr(card, "_FONT_DIR", tmp_path)

    card._font_local.lang = "zh"
    assert Path(card._font(20).path) == zh_font
    assert Path(card._font(20, "rank").path) == rank_font

    card._font_local.lang = "ja"
    assert Path(card._font(20).path) == ja_font
    assert Path(card._font(20, "rank").path) == ja_font
