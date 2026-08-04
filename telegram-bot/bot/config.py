"""تنظیمات ربات از متغیرهای محیطی."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.replace(" ", "").split(","):
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    webhook_secret: str
    webhook_host: str
    webhook_port: int
    database_path: Path

    @property
    def has_admins(self) -> bool:
        return bool(self.admin_ids)


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است. فایل .env را از روی .env.example بسازید."
        )

    db_raw = os.getenv("DATABASE_PATH", "./data/bot.db").strip()
    db_path = Path(db_raw).expanduser()
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()

    return Settings(
        bot_token=token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        webhook_secret=os.getenv("WEBHOOK_SECRET", "").strip(),
        webhook_host=os.getenv("WEBHOOK_HOST", "0.0.0.0").strip() or "0.0.0.0",
        webhook_port=int(os.getenv("WEBHOOK_PORT", "8080")),
        database_path=db_path,
    )
