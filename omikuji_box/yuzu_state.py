"""记录 omikuji 当天选中的柚子社角色，供 /yuzuwaifu 对齐。"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from . import state
from .yuzusoft import YuzuCharacter

_lock = threading.Lock()


def _file() -> Path:
    return state.data_dir() / "omikuji_yuzu.json"


def _load() -> dict[str, Any]:
    try:
        payload = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save(payload: dict[str, Any]) -> None:
    path = _file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def get(user_id: int, day: str) -> dict[str, Any] | None:
    with _lock:
        users = _load().get("users")
        if not isinstance(users, dict):
            return None
        entry = users.get(str(int(user_id)))
        if not isinstance(entry, dict):
            return None
        if str(entry.get("date") or "") != day:
            return None
        return entry


def record(user_id: int, day: str, character: YuzuCharacter) -> None:
    library_path = str(character.library_path or "").strip()
    if not library_path:
        return
    with _lock:
        payload = _load()
        users = payload.get("users")
        if not isinstance(users, dict):
            users = {}
            payload["users"] = users
        payload["version"] = 1
        users[str(int(user_id))] = {
            "date": day,
            "character_id": str(character.id or ""),
            "library_path": library_path,
            "name": character.name,
            "original": character.original,
            "image_url": character.image_url,
        }
        _save(payload)


def clear(user_id: int, day: str) -> None:
    with _lock:
        payload = _load()
        users = payload.get("users")
        if not isinstance(users, dict):
            return
        entry = users.get(str(int(user_id)))
        if not isinstance(entry, dict) or str(entry.get("date") or "") != day:
            return
        users.pop(str(int(user_id)), None)
        _save(payload)
