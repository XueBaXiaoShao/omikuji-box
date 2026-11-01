"""柚子社元素：随机幸运角色、会社 logo 与立绘加载。"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx

from .config import config


@dataclass(frozen=True)
class YuzuCharacter:
    name: str
    original: str
    work: str
    image_url: str
    work_original: str = ""
    id: str = ""
    library_path: str = ""


_lock = threading.Lock()
_characters: list[YuzuCharacter] | None = None
_work_cache: dict[Path, str] = {}
_work_cache_ja: dict[Path, str] = {}
_portrait_cache: dict[str, bytes] = {}


def _localize(character: YuzuCharacter, lang: str) -> YuzuCharacter:
    if lang != "ja":
        return character
    return YuzuCharacter(
        name=character.original or character.name,
        original=character.original,
        work=character.work_original or character.work,
        image_url=character.image_url,
        work_original=character.work_original,
        id=character.id,
        library_path=character.library_path,
    )


def _library_base() -> Path:
    return Path(
        os.getenv("OMIKUJI_LIBRARY_DIR")
        or os.getenv("WAIFU_LIBRARY_DIR")
        or "/app/data/final_company_library"
    )


def _library_root() -> Path:
    return _library_base() / "ゆずソフト"


def _work_name(game_dir: Path) -> str:
    cached = _work_cache.get(game_dir)
    if cached is not None:
        return cached
    name = game_dir.name
    try:
        data = json.loads(
            (game_dir / "游戏介绍.json").read_text(encoding="utf-8")
        )
        name = (
            str(data.get("cn_title") or "").strip()
            or str(data.get("title") or "").strip()
            or str(data.get("jp_title") or "").strip()
            or name
        )
    except (OSError, json.JSONDecodeError):
        pass
    _work_cache[game_dir] = name
    return name


def _work_name_ja(game_dir: Path) -> str:
    cached = _work_cache_ja.get(game_dir)
    if cached is not None:
        return cached
    name = game_dir.name
    try:
        data = json.loads(
            (game_dir / "游戏介绍.json").read_text(encoding="utf-8")
        )
        name = (
            str(data.get("jp_title") or "").strip()
            or str(data.get("title") or "").strip()
            or str(data.get("cn_title") or "").strip()
            or name
        )
    except (OSError, json.JSONDecodeError):
        pass
    _work_cache_ja[game_dir] = name
    return name


def _load_characters() -> list[YuzuCharacter]:
    global _characters
    with _lock:
        if _characters is not None:
            return _characters
        characters: list[YuzuCharacter] = []
        root = _library_root()
        for path in sorted(root.glob("*/角色/*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not str(data.get("sex") or "").lower().startswith("f"):
                continue
            image = data.get("image") or {}
            if not isinstance(image, dict):
                continue
            if int(image.get("sexual") or 0) != 0:
                continue
            url = str(image.get("url") or "").strip()
            if not url:
                continue
            original = str(data.get("original") or data.get("name") or "").strip()
            name = str(data.get("cn_name") or "").strip() or original
            if not name:
                continue
            try:
                library_path = path.relative_to(
                    _library_base()
                ).as_posix()
            except ValueError:
                library_path = ""
            characters.append(
                YuzuCharacter(
                    name=name,
                    original=original,
                    work=_work_name(path.parent.parent),
                    image_url=url,
                    work_original=_work_name_ja(path.parent.parent),
                    id=str(data.get("id") or ""),
                    library_path=library_path,
                )
            )
        _characters = characters
        return characters


def _data_root() -> Path:
    return Path(
        os.getenv("OMIKUJI_DATA_DIR")
        or os.getenv("LOCALSTORE_DATA_DIR")
        or "data"
    )


def user_waifu(
    user_id: int, day: str, lang: str = "zh"
) -> YuzuCharacter | None:
    """读取 waifu-box 今日 yuzuwaifu；没有时返回 None。"""
    try:
        payload = json.loads(
            (_data_root() / "waifu_state.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None
    users = payload.get("users") if isinstance(payload, dict) else None
    record = users.get(str(user_id)) if isinstance(users, dict) else None
    if not isinstance(record, dict):
        return None
    if str(record.get("date") or "") != day:
        return None
    if str(record.get("source") or "") != "yuzu":
        return None

    name = str(
        record.get("original") or record.get("name") or ""
    ).strip()
    original = str(record.get("original") or name).strip()
    image_url = str(record.get("image_url") or "").strip()
    character_id = str(record.get("character_id") or "").strip()
    vns = record.get("vns") or []
    work = ""
    if vns and isinstance(vns[0], dict):
        work = str(vns[0].get("title") or "").strip()
    work_original = work

    library_path = str(record.get("library_path") or "").strip()
    if library_path:
        path = _library_base() / library_path
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            character_id = str(data.get("id") or character_id).strip()
            cn_name = str(data.get("cn_name") or "").strip()
            original = str(data.get("original") or original).strip()
            name = (
                original or cn_name or name
                if lang == "ja"
                else cn_name or original or name
            )
            image_url = str(
                (data.get("image") or {}).get("url") or image_url
            ).strip()
            work_zh = _work_name(path.parent.parent)
            work_ja = _work_name_ja(path.parent.parent)
            work = (work_ja or work_zh) if lang == "ja" else (work_zh or work_ja)
            work_original = work_ja

    if not name or not image_url:
        return None
    return YuzuCharacter(
        name=name,
        original=original,
        work=work,
        image_url=image_url,
        work_original=work_original,
        id=character_id,
        library_path=library_path,
    )


def pick(
    user_id: int, day: str, lang: str = "zh"
) -> YuzuCharacter | None:
    characters = _load_characters()
    if not characters:
        return None
    digest = hashlib.sha256(
        f"yuzu:{config.seed_salt}:{user_id}:{day}".encode("utf-8")
    ).digest()
    character = characters[int.from_bytes(digest, "big") % len(characters)]
    return _localize(character, lang)


def logo_path() -> Path | None:
    root = Path(
        os.getenv("OMIKUJI_LOGO_DIR")
        or os.getenv("WAIFU_LOGO_DIR")
        or "/app/data/company_logos"
    )
    for candidate in (
        root / "Yuzusoft.png",
        root / "Yuzusoft.jpg",
        root / "normalized" / "Yuzusoft.png",
    ):
        if candidate.is_file():
            return candidate
    return None


async def fetch_portrait(url: str) -> bytes | None:
    if not url:
        return None
    cached = _portrait_cache.get(url)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(
            timeout=8.0,
            headers={"User-Agent": "omikuji-box/0.1"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.content
    except Exception:
        return None
    if not data or len(data) > 2_000_000:
        return None
    if len(_portrait_cache) > 64:
        _portrait_cache.clear()
    _portrait_cache[url] = data
    return data
