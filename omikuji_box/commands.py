"""おみくじ命令入口。"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path

from nonebot import get_driver, logger, on_command
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from . import card, draw, settings, state, yuzu_state, yuzusoft

def _is_slash_omikuji(event: MessageEvent) -> bool:
    """只响应带斜杠的 /omikuji、/おみくじ 等，避免普通文本误触发。"""
    return (event.get_plaintext() or "").lstrip().startswith("/")


omikuji_cmd = on_command(
    "omikuji",
    aliases={"おみくじ", "御神籤", "omukuji"},
    rule=_is_slash_omikuji,
    priority=5,
    block=True,
)


def _switch_file() -> Path:
    return state.data_dir() / "plugin_switches.json"


def _admin_ids() -> set[int]:
    ids: set[int] = set()
    try:
        payload = json.loads(
            (state.data_dir() / "admin_ids.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        payload = {}
    admins = payload.get("admins") if isinstance(payload, dict) else None
    if isinstance(admins, list):
        ids.update(
            int(item) for item in admins if str(item).strip().isdigit()
        )
    try:
        ids.update(
            int(user)
            for user in get_driver().config.superusers
            if str(user).strip().isdigit()
        )
    except Exception:
        pass
    return ids


def _is_admin(user_id: int) -> bool:
    return int(user_id) in _admin_ids()


def _at_user_ids(event: MessageEvent) -> list[int]:
    result: list[int] = []
    message = getattr(event, "message", None)
    if message is None:
        return result
    for segment in message:
        data = getattr(segment, "data", None) or {}
        if (
            getattr(segment, "type", None) == "at"
            and str(data.get("qq") or "").isdigit()
        ):
            result.append(int(data["qq"]))
    return result


def _reset_target(event: MessageEvent, text: str) -> int | None:
    at_ids = _at_user_ids(event)
    if at_ids:
        return at_ids[0]
    parts = (text or "").split()
    if parts and parts[0].isdigit():
        return int(parts[0])
    return None


def _allowed_users() -> set[int] | None:
    """允许使用おみくじ的用户；None 表示不限制（全员开放）。"""
    raw = os.getenv("OMIKUJI_ALLOWED_USERS", "").replace("，", ",").strip()
    if raw.lower() in {"*", "all"}:
        return None
    if raw:
        return {
            int(part) for part in raw.split(",") if part.strip().isdigit()
        }
    try:
        superusers = get_driver().config.superusers
    except Exception:
        return set()
    return {
        int(user)
        for user in superusers
        if str(user).strip().isdigit()
    }


def _enabled_for_event(event: MessageEvent) -> bool:
    group_id = getattr(event, "group_id", None)
    if group_id is None:
        return True
    try:
        payload = json.loads(_switch_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(payload, dict):
        return True
    groups = payload.get("groups")
    if isinstance(groups, dict):
        entry = groups.get(str(group_id))
        if isinstance(entry, dict) and "omikuji_box" in entry:
            return bool(entry["omikuji_box"])
    defaults = payload.get("defaults")
    if isinstance(defaults, dict) and "omikuji_box" in defaults:
        return bool(defaults["omikuji_box"])
    return True




def _help_text() -> str:
    return """【おみくじ】
- /omikuji（/おみくじ、/御神籤）—— 抽今日御神签（每天固定）
- /omikuji settings JP on|off —— 切换中文/日文
- /omikuji reset @某人|<QQ号> —— 重置今日结果（管理员）"""


async def _handle_settings(
    matcher: Matcher, user_id: int, value: str
) -> None:
    parts = (value or "").split()
    current = "日本語" if settings.get_lang(user_id) == "ja" else "中文"
    if not parts:
        await matcher.finish(
            f"当前语言：{current}\n用法：/omikuji settings JP on|off"
        )
    if parts[0].lower() not in {
        "jp",
        "ja",
        "japanese",
        "日本語",
        "日文",
    }:
        await matcher.finish("用法：/omikuji settings JP on|off")
    if len(parts) < 2:
        await matcher.finish(
            f"当前语言：{current}\n用法：/omikuji settings JP on|off"
        )
    flag = parts[1].lower()
    if flag in {"on", "true", "1", "yes", "开启"}:
        settings.set_lang(user_id, "ja")
        await matcher.finish("已切换为日本語版御神签。")
    if flag in {"off", "false", "0", "no", "关闭"}:
        settings.set_lang(user_id, "zh")
        await matcher.finish("已切换为中文版御神签。")
    await matcher.finish("用法：/omikuji settings JP on|off")


@omikuji_cmd.handle()
async def handle_omikuji(
    event: MessageEvent,
    matcher: Matcher,
    arg: Message = CommandArg(),
) -> None:
    user_id = int(getattr(event, "user_id", 0))
    text = (arg.extract_plain_text() or "").strip()
    lower = text.lower()
    if lower in ("help", "帮助", "用法"):
        await matcher.finish(_help_text())
    is_reset = (
        lower == "reset"
        or lower.startswith("reset ")
        or text == "重置"
        or text.startswith("重置 ")
    )
    if is_reset:
        if not _is_admin(user_id):
            await matcher.finish("只有管理员可以重置御神签")
        rest = text[5:].strip() if lower.startswith("reset") else text[2:].strip()
        target = _reset_target(event, rest)
        if target is None:
            await matcher.finish(
                "用法：/omikuji reset @某人 或 /omikuji reset <QQ号>"
            )
        today = draw.today_iso()
        state.reset(target, today)
        yuzu_state.clear(target, today)
        await matcher.finish(
            f"已重置用户 {target} 的今日御神签，重新发送 /omikuji 即可。"
        )
    allowed = _allowed_users()
    if allowed is not None and user_id not in allowed:
        return
    if lower == "settings" or lower.startswith("settings "):
        rest = text[len("settings"):].strip()
        await _handle_settings(matcher, user_id, rest)
        return
    if not _enabled_for_event(event):
        await matcher.finish("本群未开启御神签")
    result = draw.draw(user_id)
    caption = draw.caption(result)
    portrait = await yuzusoft.fetch_portrait(result.yuzu_image_url)
    try:
        image_bytes = await asyncio.to_thread(
            card.render_card,
            result,
            portrait,
            yuzusoft.logo_path(),
        )
    except Exception:
        logger.exception("御神签签纸渲染失败")
        await matcher.finish(caption)
    segments: list[MessageSegment] = []
    if getattr(event, "group_id", None) is not None:
        segments.append(MessageSegment.at(user_id))
    segments.append(
        MessageSegment.image(
            "base64://" + base64.b64encode(image_bytes).decode("ascii")
        )
    )
    segments.append(MessageSegment.text(caption))
    await matcher.finish(Message(segments))
