"""和风おみくじ签纸渲染（中文 / 柚子社主题）。"""

from __future__ import annotations

import random
import threading
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import content
from .draw import Omikuji

WIDTH = 900
HEIGHT = 1400
MARGIN = 28

PAPER_TOP = (248, 242, 229)
PAPER_BOTTOM = (239, 228, 208)
INK = (43, 41, 37)
MUTED = (107, 99, 86)
GOLD = (160, 128, 75)
RED = (166, 52, 45)
LINE = (203, 185, 160)
YUZU_ORANGE = (240, 163, 60)
YUZU_GREEN = (111, 159, 85)
YUZU_LIGHT = (255, 245, 220)


_LABELS = {
    "zh": {
        "title": "御神签",
        "brand": "Yuzu Omikuji",
        "date_line": "{date} · 第 {n} 签",
        "overall": "综合运势",
        "lucky": "幸运",
        "lucky_item": "幸运物",
        "lucky_color": "幸运色",
        "lucky_direction": "幸运方位",
        "lucky_number": "幸运数字",
        "yuzu_section": "今日柚子社幸运角色",
        "yuzu_name_fallback": "柚子社角色",
        "yuzu_work_fallback": "今天也要加油",
        "no_portrait": "暂无立绘",
        "rare": "（稀有）",
        "footer": "同一天结果固定 · 明天再来抽吧",
    },
    "ja": {
        "title": "おみくじ",
        "brand": "ゆずおみくじ",
        "date_line": "{date} · 第 {n} 番",
        "overall": "総合運",
        "lucky": "ラッキー",
        "lucky_item": "アイテム",
        "lucky_color": "カラー",
        "lucky_direction": "方位",
        "lucky_number": "ナンバー",
        "yuzu_section": "今日の柚子ソフト幸運キャラ",
        "yuzu_name_fallback": "柚子ソフトキャラ",
        "yuzu_work_fallback": "今日もがんばろう",
        "no_portrait": "立ち絵なし",
        "rare": "（レア）",
        "footer": "同じ日の結果は固定・また明日",
    },
}


def _labels(result: Omikuji) -> dict[str, str]:
    return _LABELS.get(getattr(result, "lang", "zh"), _LABELS["zh"])


_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_FONT_FILE = _FONT_DIR / "NotoSansSC-Regular.otf"
_CUSTOM_FONT_EXTENSIONS = (".otf", ".ttf", ".ttc")
_font_local = threading.local()


def _font_path(kind: str = "text") -> Path:
    lang = getattr(_font_local, "lang", "zh")
    if kind == "rank":
        for extension in _CUSTOM_FONT_EXTENSIONS:
            candidate = _FONT_DIR / f"omikuji-rank-{lang}{extension}"
            if candidate.is_file():
                return candidate
    prefix = "omikuji-ja" if lang == "ja" else "omikuji-zh"
    for extension in _CUSTOM_FONT_EXTENSIONS:
        candidate = _FONT_DIR / f"{prefix}{extension}"
        if candidate.is_file():
            return candidate
    return _FONT_FILE


def _font(size: int, kind: str = "text") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_font_path(kind)), size=size)


def _hex(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _wrap(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    size: int,
    max_width: int,
    min_size: int = 16,
    kind: str = "text",
) -> ImageFont.FreeTypeFont:
    font = _font(size, kind)
    while size > min_size and draw.textlength(text, font=font) > max_width:
        size -= 2
        font = _font(size, kind)
    return font


def _draw_background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        color = tuple(
            int(PAPER_TOP[index] + (PAPER_BOTTOM[index] - PAPER_TOP[index]) * ratio)
            for index in range(3)
        )
        draw.line((0, y, WIDTH, y), fill=color)
    return image


def _draw_paper_texture(draw: ImageDraw.ImageDraw, result: Omikuji) -> None:
    rng = random.Random(f"{result.user_id}:{result.day}:texture")
    for _ in range(520):
        x = rng.randint(60, WIDTH - 60)
        y = rng.randint(70, HEIGHT - 70)
        color = (218, 205, 184) if rng.random() < 0.6 else (228, 216, 196)
        draw.point((x, y), fill=color)


def _draw_border(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle(
        (MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN),
        radius=18,
        outline=RED,
        width=3,
    )
    draw.rounded_rectangle(
        (MARGIN + 10, MARGIN + 10, WIDTH - MARGIN - 10, HEIGHT - MARGIN - 10),
        radius=14,
        outline=GOLD,
        width=1,
    )


def _paste_logo(image: Image.Image, logo_path: Path | None) -> None:
    if logo_path is not None and logo_path.is_file():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((108, 66))
            image.paste(logo, (58, 50), logo)
            return
        except Exception:
            pass
    draw = ImageDraw.Draw(image)
    draw.text(
        (58, 76),
        "Yuzusoft",
        font=_font(18),
        fill=YUZU_ORANGE,
        anchor="lm",
    )


def _draw_header(
    draw: ImageDraw.ImageDraw, result: Omikuji, date_text: str
) -> None:
    draw.text(
        (WIDTH / 2, 58),
        "O M I K U J I",
        font=_font(17),
        fill=GOLD,
        anchor="mm",
    )
    labels = _labels(result)
    draw.text(
        (WIDTH / 2, 112),
        labels["title"],
        font=_font(54),
        fill=RED,
        anchor="mm",
    )
    draw.text(
        (WIDTH / 2, 158),
        labels["date_line"].format(date=date_text, n=result.number),
        font=_font(17),
        fill=MUTED,
        anchor="mm",
    )
    draw.rounded_rectangle(
        (366, 174, 534, 198),
        radius=12,
        fill=YUZU_ORANGE,
        outline=(201, 128, 35),
        width=1,
    )
    draw.text(
        (450, 186),
        labels["brand"],
        font=_font(14),
        fill=(255, 250, 240),
        anchor="mm",
    )


def _draw_rank(draw: ImageDraw.ImageDraw, result: Omikuji) -> None:
    rank_color = _hex(content.RANK_COLORS[result.rank])
    draw.ellipse(
        (WIDTH / 2 - 132, 214, WIDTH / 2 + 132, 478),
        fill=(247, 238, 220),
        outline=(230, 207, 172),
        width=2,
    )
    draw.text(
        (WIDTH / 2, 284),
        _labels(result)["overall"],
        font=_font(20),
        fill=MUTED,
        anchor="mm",
    )
    rank_font = _fit_font(draw, result.rank, 118, 240, 68, kind="rank")
    draw.text(
        (WIDTH / 2, 364),
        result.rank,
        font=rank_font,
        fill=rank_color,
        anchor="mm",
        stroke_width=1,
        stroke_fill=rank_color,
    )
    message_font = _font(20)
    lines = _wrap(draw, result.message, message_font, 680)
    for index, line in enumerate(lines[:3]):
        draw.text(
            (WIDTH / 2, 514 + index * 30),
            line,
            font=message_font,
            fill=INK,
            anchor="mm",
        )


def _draw_divider(draw: ImageDraw.ImageDraw, y: int) -> None:
    draw.line((78, y, WIDTH - 78, y), fill=LINE, width=1)
    draw.polygon(
        (
            (WIDTH / 2, y - 7),
            (WIDTH / 2 + 7, y),
            (WIDTH / 2, y + 7),
            (WIDTH / 2 - 7, y),
        ),
        fill=YUZU_ORANGE,
    )


def _draw_categories(draw: ImageDraw.ImageDraw, result: Omikuji) -> None:
    start_y = 630
    row_height = 82
    for index, item in enumerate(result.categories):
        y = start_y + index * row_height
        if index:
            draw.line(
                (78, y - 12, WIDTH - 78, y - 12),
                fill=(226, 213, 194),
                width=1,
            )
        draw.text(
            (92, y + 8),
            item.name,
            font=_font(22),
            fill=INK,
            anchor="lm",
        )
        level_color = (
            _hex(content.RANK_COLORS[item.level])
            if item.level in content.RANK_COLORS
            else INK
        )
        draw.text(
            (290, y + 8),
            item.level,
            font=_font(27),
            fill=level_color,
            anchor="lm",
        )
        advice_font = _font(19)
        line = item.advice
        while draw.textlength(line, font=advice_font) > 470 and len(line) > 6:
            line = line[:-1]
        draw.text(
            (400, y + 8),
            line,
            font=advice_font,
            fill=MUTED,
            anchor="lm",
        )


def _load_portrait(data: bytes | None) -> Image.Image | None:
    if not data:
        return None
    try:
        image = Image.open(BytesIO(data)).convert("RGB")
        return ImageOps.fit(
            image,
            (96, 108),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.32),
        )
    except Exception:
        return None


def _draw_yuzu_character(
    image: Image.Image, result: Omikuji, portrait: bytes | None
) -> None:
    draw = ImageDraw.Draw(image)
    top = 1052
    draw.rounded_rectangle(
        (64, top, WIDTH - 64, top + 150),
        radius=14,
        fill=YUZU_LIGHT,
        outline=(232, 202, 155),
        width=1,
    )
    labels = _labels(result)
    draw.text(
        (88, top + 18),
        labels["yuzu_section"],
        font=_font(16),
        fill=YUZU_GREEN,
        anchor="lm",
    )
    portrait_image = _load_portrait(portrait)
    box = (88, top + 36, 184, top + 144)
    if portrait_image is not None:
        mask = Image.new("L", portrait_image.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, portrait_image.width - 1, portrait_image.height - 1),
            radius=12,
            fill=255,
        )
        image.paste(portrait_image, box[:2], mask)
    else:
        draw.rounded_rectangle(
            (88, top + 36, 184, top + 144),
            radius=12,
            fill=(250, 235, 205),
            outline=(224, 189, 132),
            width=1,
        )
        draw.text(
            (136, top + 90),
            labels["no_portrait"],
            font=_font(16),
            fill=MUTED,
            anchor="mm",
        )
    draw.rounded_rectangle(
        box,
        radius=12,
        outline=(224, 189, 132),
        width=1,
    )
    name = result.yuzu_name or labels["yuzu_name_fallback"]
    work = result.yuzu_work or labels["yuzu_work_fallback"]
    name_font = _fit_font(draw, name, 26, 430, 18)
    draw.text(
        (204, top + 60),
        name,
        font=name_font,
        fill=INK,
        anchor="lm",
    )
    work_font = _fit_font(draw, work, 18, 430, 14)
    draw.text(
        (204, top + 100),
        f"「{work}」",
        font=work_font,
        fill=MUTED,
        anchor="lm",
    )
    draw.text(
        (204, top + 128),
        "Yuzusoft",
        font=_font(14),
        fill=YUZU_ORANGE,
        anchor="lm",
    )


def _draw_lucky(draw: ImageDraw.ImageDraw, result: Omikuji) -> None:
    top = 1216
    draw.rounded_rectangle(
        (64, top, WIDTH - 64, top + 96),
        radius=14,
        fill=(247, 238, 223),
        outline=(225, 209, 184),
        width=1,
    )
    labels = _labels(result)
    draw.text(
        (88, top + 18),
        labels["lucky"],
        font=_font(16),
        fill=YUZU_GREEN,
        anchor="lm",
    )
    item_text = result.lucky_item
    if result.lucky_item_rare:
        item_text += labels["rare"]
    cells = (
        (labels["lucky_item"], item_text, 88),
        (labels["lucky_color"], result.lucky_color_name, 334),
        (labels["lucky_direction"], result.lucky_direction, 580),
        (labels["lucky_number"], str(result.lucky_number), 772),
    )
    for label, value, x in cells:
        draw.text(
            (x, top + 44),
            label,
            font=_font(14),
            fill=MUTED,
            anchor="lm",
        )
        draw.text(
            (x, top + 75),
            value,
            font=_font(22),
            fill=YUZU_ORANGE
            if label == labels["lucky_item"] and result.lucky_item_rare
            else INK,
            anchor="lm",
        )
    dot_x = 334 + draw.textlength(result.lucky_color_name, font=_font(22)) + 16
    draw.ellipse(
        (dot_x, top + 64, dot_x + 18, top + 82),
        fill=_hex(result.lucky_color_hex),
        outline=(120, 110, 95),
        width=1,
    )


def _draw_footer(draw: ImageDraw.ImageDraw, result: Omikuji) -> None:
    draw.text(
        (78, 1330),
        _labels(result)["footer"],
        font=_font(15),
        fill=MUTED,
        anchor="lm",
    )


def render_card(
    result: Omikuji,
    portrait: bytes | None = None,
    logo_path: Path | None = None,
) -> bytes:
    _font_local.lang = getattr(result, "lang", "zh")
    image = _draw_background()
    draw = ImageDraw.Draw(image)
    _draw_paper_texture(draw, result)
    _draw_border(draw)
    _paste_logo(image, logo_path)
    _draw_header(draw, result, result.day.replace("-", "."))
    _draw_rank(draw, result)
    _draw_divider(draw, 590)
    _draw_categories(draw, result)
    _draw_yuzu_character(image, result, portrait)
    draw = ImageDraw.Draw(image)
    _draw_lucky(draw, result)
    _draw_footer(draw, result)
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
