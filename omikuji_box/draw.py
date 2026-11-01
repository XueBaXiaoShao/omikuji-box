"""确定性おみくじ抽取：同一 QQ 同一天结果固定。"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import content, content_ja, settings, state, yuzu_state, yuzusoft
from .config import config


@dataclass(frozen=True)
class CategoryFortune:
    name: str
    level: str
    advice: str


@dataclass(frozen=True)
class Omikuji:
    user_id: int
    day: str
    rank: str
    message: str
    categories: tuple[CategoryFortune, ...]
    lucky_item: str
    lucky_color_name: str
    lucky_color_hex: str
    lucky_direction: str
    lucky_number: int
    number: int
    yuzu_name: str = ""
    yuzu_work: str = ""
    yuzu_image_url: str = ""
    lucky_item_rare: bool = False
    lang: str = "zh"


def _today() -> date:
    try:
        zone = ZoneInfo(config.timezone)
    except Exception:
        zone = ZoneInfo("Asia/Shanghai")
    return datetime.now(zone).date()


def today_iso() -> str:
    return _today().isoformat()


def draw(user_id: int, day: date | None = None) -> Omikuji:
    target = day or _today()
    day_text = target.isoformat()
    lang = settings.get_lang(int(user_id))
    data = content_ja if lang == "ja" else content
    seed_text = f"{config.seed_salt}:{user_id}:{day_text}"
    reset_nonce = state.nonce(int(user_id), day_text)
    if reset_nonce:
        seed_text += f":reset:{reset_nonce}"
    seed = hashlib.sha256(seed_text.encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(seed, "big"))

    rank = rng.choices(
        data.RANKS, weights=data.RANK_WEIGHTS, k=1
    )[0]
    categories: list[CategoryFortune] = []
    for name, advice_map in data.CATEGORIES:
        level = rng.choices(
            data.CATEGORY_LEVELS,
            weights=data.CATEGORY_WEIGHTS,
            k=1,
        )[0]
        categories.append(
            CategoryFortune(
                name=name,
                level=level,
                advice=advice_map[level],
            )
        )
    color_name, color_hex = rng.choice(data.LUCKY_COLORS)
    item_rng = random.Random(
        int.from_bytes(seed, "big") ^ 0x9E3779B97F4A7C15
    )
    pool = data.LUCKY_ITEMS_BY_RANK.get(rank, data.LUCKY_ITEMS)
    rare_pool = data.RARE_LUCKY_ITEMS_BY_RANK.get(rank, ())
    rare = (
        bool(rare_pool)
        and config.rare_item_chance > 0
        and item_rng.random() < config.rare_item_chance
    )
    lucky_item = item_rng.choice(rare_pool if rare else pool)
    # 保留主随机序列，避免签号/方位因物品池变化而改变
    rng.choice(data.LUCKY_ITEMS)
    yuzu = yuzusoft.user_waifu(int(user_id), day_text, lang)
    if yuzu is None:
        yuzu = yuzusoft.pick(int(user_id), day_text, lang)
        if yuzu is not None:
            yuzu_state.record(int(user_id), day_text, yuzu)
    return Omikuji(
        user_id=int(user_id),
        day=day_text,
        rank=rank,
        message=data.RANK_MESSAGES[rank],
        categories=tuple(categories),
        lucky_item=lucky_item,
        lucky_color_name=color_name,
        lucky_color_hex=color_hex,
        lucky_direction=rng.choice(data.LUCKY_DIRECTIONS),
        lucky_number=rng.choice(data.LUCKY_NUMBERS),
        number=rng.randint(1, 100),
        yuzu_name=yuzu.name if yuzu else "",
        yuzu_work=yuzu.work if yuzu else "",
        yuzu_image_url=yuzu.image_url if yuzu else "",
        lucky_item_rare=rare,
        lang=lang,
    )


def caption(result: Omikuji) -> str:
    if result.lang == "ja":
        text = (
            f"今日の運勢：{result.rank}（第 {result.number} 番）\n"
            "同じ日の結果は固定です。また明日引いてね。"
        )
        if result.yuzu_name:
            text += f"\n今日の柚子ソフト幸運キャラ：{result.yuzu_name}"
        return text
    text = (
        f"今日运势：{result.rank}（第 {result.number} 签）\n"
        "同一天结果固定，明天再来抽吧。"
    )
    if result.yuzu_name:
        text += f"\n今日柚子社幸运角色：{result.yuzu_name}"
    return text
