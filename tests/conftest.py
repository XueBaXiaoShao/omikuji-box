"""pytest 全局配置：先初始化 NoneBot，再导入插件。"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OMIKUJI_TIMEZONE", "Asia/Shanghai")
os.environ.setdefault("OMIKUJI_SEED_SALT", "test-omikuji")
os.environ.setdefault("OMIKUJI_DATA_DIR", tempfile.mkdtemp(prefix="omikuji-test-"))

import nonebot  # noqa: E402

_original_cwd = Path.cwd()
os.chdir(tempfile.gettempdir())
try:
    nonebot.init()
finally:
    os.chdir(_original_cwd)
