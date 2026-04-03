from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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
            raise ValueError("PANDASCORE_TOKEN environment variable is required")

        return cls(
            pandascore_token=token,
            site_url=os.environ.get("SITE_URL", "https://site-generator.ozzy1986.com").rstrip("/"),
            site_name=os.environ.get("SITE_NAME", "Esports Matches Schedule"),
            site_timezone=os.environ.get("SITE_TIMEZONE", "UTC"),
            output_dir=base / os.environ.get("OUTPUT_DIR", "generated_site"),
            base_dir=base,
        )
