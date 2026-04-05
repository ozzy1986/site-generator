from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    pandascore_token: str
    site_url: str
    site_name: str
    site_timezone: str
    output_dir: Path
    base_dir: Path

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> Config:
        load_dotenv()
        base = base_dir or Path.cwd()

        token = os.environ.get("PANDASCORE_TOKEN", "")
        if not token:
            raise ValueError("Не задана переменная окружения PANDASCORE_TOKEN")

        site_timezone = os.environ.get("SITE_TIMEZONE", "Europe/Moscow")
        try:
            ZoneInfo(site_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Неизвестная таймзона SITE_TIMEZONE: {site_timezone}") from exc

        return cls(
            pandascore_token=token,
            site_url=os.environ.get("SITE_URL", "https://site-generator.ozzy1986.com").rstrip("/"),
            site_name=os.environ.get("SITE_NAME", "Киберспортивные матчи"),
            site_timezone=site_timezone,
            output_dir=base / os.environ.get("OUTPUT_DIR", "generated_site"),
            base_dir=base,
        )
