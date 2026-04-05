from __future__ import annotations

from dataclasses import replace
import logging
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from site_generator.config import Config
from site_generator.models import DaySchedule, MatchCard, normalize_match
from site_generator.pandascore_client import PandaScoreClient
from site_generator.services.schema import build_home_jsonld, build_jsonld_block
from site_generator.services.seo import PageSeo, build_day_seo, build_home_seo

logger = logging.getLogger(__name__)

_MONTH_NAMES_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

_TIMEZONE_LABELS = {
    "Europe/Moscow": "МСК",
}


def compute_day_dates(
    site_tz: tzinfo = timezone.utc,
    now: datetime | None = None,
) -> tuple[date, date, date]:
    """Return *(yesterday, today, tomorrow)* in the configured timezone."""
    if now is None:
        current = datetime.now(site_tz)
    elif now.tzinfo is None:
        current = now.replace(tzinfo=site_tz)
    else:
        current = now.astimezone(site_tz)

    today = current.date()
    return today - timedelta(days=1), today, today + timedelta(days=1)


def format_display_date(d: date) -> str:
    """Cross-platform Russian date format: ``3 апреля 2026``."""
    return f"{d.day} {_MONTH_NAMES_RU[d.month]} {d.year}"


def build_day_schedule(
    label: str,
    target_date: date,
    matches: list[MatchCard],
) -> DaySchedule:
    sentinel = datetime.min.replace(tzinfo=timezone.utc)
    return DaySchedule(
        label=label,
        date_str=target_date.isoformat(),
        display_date=format_display_date(target_date),
        matches=tuple(sorted(matches, key=lambda m: m.begin_at or sentinel)),
    )


def normalize_matches(raw: list[dict[str, Any]]) -> list[MatchCard]:
    return [normalize_match(m) for m in raw]


def localize_matches(matches: list[MatchCard], site_tz: tzinfo) -> list[MatchCard]:
    """Convert match datetimes from UTC to the configured site timezone."""
    localized: list[MatchCard] = []
    for match in matches:
        localized.append(replace(
            match,
            begin_at=match.begin_at.astimezone(site_tz) if match.begin_at else None,
            end_at=match.end_at.astimezone(site_tz) if match.end_at else None,
        ))
    return localized


def timezone_label(site_timezone: str) -> str:
    return _TIMEZONE_LABELS.get(site_timezone, site_timezone)


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def generate_site(config: Config) -> dict[str, Any]:
    """Fetch data, render templates, and write the static site atomically.

    Returns a summary dict with per-day match counts.
    """
    site_tz = ZoneInfo(config.site_timezone)
    yesterday_date, today_date, tomorrow_date = compute_day_dates(site_tz)
    logger.info(
        "Fetching PandaScore matches for %s / %s / %s in %s",
        yesterday_date, today_date, tomorrow_date, config.site_timezone,
    )

    with PandaScoreClient(config.pandascore_token) as client:
        raw_yesterday = client.fetch_matches_for_day(yesterday_date, site_tz)
        raw_today = client.fetch_matches_for_day(today_date, site_tz)
        raw_tomorrow = client.fetch_matches_for_day(tomorrow_date, site_tz)

    schedules = {
        "yesterday": build_day_schedule(
            "yesterday", yesterday_date, localize_matches(normalize_matches(raw_yesterday), site_tz),
        ),
        "today": build_day_schedule(
            "today", today_date, localize_matches(normalize_matches(raw_today), site_tz),
        ),
        "tomorrow": build_day_schedule(
            "tomorrow", tomorrow_date, localize_matches(normalize_matches(raw_tomorrow), site_tz),
        ),
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _render_site(config, schedules, tmp_path)

        if config.output_dir.exists():
            shutil.rmtree(config.output_dir)
        shutil.copytree(tmp_path, config.output_dir)
        _ensure_public_permissions(config.output_dir)

    logger.info("Site generated in %s", config.output_dir)
    return {
        "yesterday": len(schedules["yesterday"].matches),
        "today": len(schedules["today"].matches),
        "tomorrow": len(schedules["tomorrow"].matches),
    }


# ------------------------------------------------------------------
# Internal renderer
# ------------------------------------------------------------------

def _render_site(
    config: Config,
    schedules: dict[str, DaySchedule],
    output: Path,
) -> None:
    templates_dir = config.base_dir / "templates" / "site"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )

    _copy_assets(config.base_dir, output)

    ctx_common = {
        "site_name": config.site_name,
        "schedules": schedules,
        "site_timezone_label": timezone_label(config.site_timezone),
    }

    _write_home(env, config, schedules, output, ctx_common)

    for label, schedule in schedules.items():
        _write_day(env, config, schedule, output, ctx_common)


def _copy_assets(base_dir: Path, output: Path) -> None:
    src = base_dir / "static" / "site"
    dst = output / "assets"
    if src.exists():
        shutil.copytree(src, dst)
    else:
        dst.mkdir(parents=True, exist_ok=True)


def _write_home(
    env: Environment,
    config: Config,
    schedules: dict[str, DaySchedule],
    output: Path,
    ctx: dict[str, Any],
) -> None:
    seo = build_home_seo(config.site_url, config.site_name)
    jsonld = build_home_jsonld(config.site_url, config.site_name)
    tmpl = env.get_template("home.html")
    (output / "index.html").write_text(
        tmpl.render(seo=seo, jsonld=jsonld, **ctx),
        encoding="utf-8",
    )


def _write_day(
    env: Environment,
    config: Config,
    schedule: DaySchedule,
    output: Path,
    ctx: dict[str, Any],
) -> None:
    seo = build_day_seo(schedule, config.site_url, config.site_name)
    jsonld = build_jsonld_block(schedule, config.site_url, config.site_name)
    tmpl = env.get_template("day.html")

    day_dir = output / schedule.label
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "index.html").write_text(
        tmpl.render(seo=seo, jsonld=jsonld, schedule=schedule, **ctx),
        encoding="utf-8",
    )


def _ensure_public_permissions(output_dir: Path) -> None:
    """Ensure Apache can traverse and serve the generated static site."""
    if os.name == "nt":
        return

    output_dir.chmod(0o755)
    for path in output_dir.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)
