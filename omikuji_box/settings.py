"""おみくじ用户偏好：语言切换。"""

from __future__ import annotations

import json
import threading
from typing import Any

from . import state

_lock = threading.Lock()


def _file():
    return state.data_dir() / "omikuji_settings.json"


def _load() -> dict[str, Any]:
    try:
        payload = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save(payload: dict[str, Any]) -> None:
    path = _file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def get_lang(user_id: int) -> str:
    with _lock:
        users = _load().get("users")
        if not isinstance(users, dict):
            return "zh"
        entry = users.get(str(user_id))
        if not isinstance(entry, dict):
            return "zh"
        lang = str(entry.get("lang") or "").strip().lower()
        return "ja" if lang == "ja" else "zh"


def set_lang(user_id: int, lang: str) -> str:
    normalized = "ja" if str(lang).strip().lower() == "ja" else "zh"
    with _lock:
        payload = _load()
        users = payload.setdefault("users", {})
        if not isinstance(users, dict):
            users = {}
            payload["users"] = users
        entry = users.get(str(user_id))
        if not isinstance(entry, dict):
            entry = {}
            users[str(user_id)] = entry
        entry["lang"] = normalized
        _save(payload)
        return normalized
