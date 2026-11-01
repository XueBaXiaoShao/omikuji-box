"""おみくじ插件配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return min(1.0, max(0.0, value))


@dataclass
class Config:
    timezone: str = "Asia/Shanghai"
    seed_salt: str = "omikuji-box-v1"
    rare_item_chance: float = 0.05

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            timezone=_env_str("OMIKUJI_TIMEZONE") or "Asia/Shanghai",
            seed_salt=_env_str("OMIKUJI_SEED_SALT") or "omikuji-box-v1",
            rare_item_chance=_env_float("OMIKUJI_RARE_ITEM_CHANCE", 0.05),
        )


config = Config.from_env()
