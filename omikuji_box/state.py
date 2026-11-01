"""おみくじ重置状态：按用户和日期保存每日随机盐。"""

from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def data_dir() -> Path:
    return Path(
        os.getenv("OMIKUJI_DATA_DIR")
        or os.getenv("LOCALSTORE_DATA_DIR")
        or "data"
    )


def state_file() -> Path:
    return data_dir() / "omikuji_state.json"


def _load() -> dict[str, Any]:
    try:
        payload = json.loads(state_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save(payload: dict[str, Any]) -> None:
    path = state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def nonce(user_id: int, day: str) -> int:
    """返回某用户某天的重置盐；没有重置时返回 0。"""
    with _lock:
        users = _load().get("users")
        if not isinstance(users, dict):
            return 0
        entry = users.get(str(user_id))
        if not isinstance(entry, dict) or str(entry.get("date") or "") != day:
            return 0
        try:
            return int(entry.get("nonce") or 0)
        except (TypeError, ValueError):
            return 0


def reset(user_id: int, day: str) -> int:
    """重置某用户某天的签，返回新的随机盐。"""
    with _lock:
        payload = _load()
        users = payload.setdefault("users", {})
        if not isinstance(users, dict):
            users = {}
            payload["users"] = users
        entry = users.get(str(user_id))
        old = 0
        if isinstance(entry, dict) and str(entry.get("date") or "") == day:
            try:
                old = int(entry.get("nonce") or 0)
            except (TypeError, ValueError):
                old = 0
        new = old
        while new == old:
            new = secrets.randbelow(2**63 - 1) + 1
        users[str(user_id)] = {"date": day, "nonce": new}
        _save(payload)
        return new
