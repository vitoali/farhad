"""بارگذاری و ذخیره تنظیمات."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config.json"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.json"


def ensure_config(path: Path = DEFAULT_CONFIG_PATH) -> Path:
    if not path.exists():
        if not EXAMPLE_CONFIG_PATH.exists():
            raise FileNotFoundError("config.example.json پیدا نشد.")
        shutil.copy(EXAMPLE_CONFIG_PATH, path)
    return path


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = ensure_config(path or DEFAULT_CONFIG_PATH)
    with cfg_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data


def save_config(data: dict[str, Any], path: Path | None = None) -> None:
    cfg_path = path or DEFAULT_CONFIG_PATH
    with cfg_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def resolve_path(maybe_relative: str) -> Path:
    p = Path(maybe_relative)
    if p.is_absolute():
        return p
    return (ROOT / p).resolve()


def clone_config(cfg: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(cfg)
