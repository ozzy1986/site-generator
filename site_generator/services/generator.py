from __future__ import annotations

import logging
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from site_generator.config import Config
from site_generator.models import DaySchedule, MatchCard, normalize_match
from site_generator.pandascore_client import PandaScoreClient
from site_generator.services.schema import build_home_jsonld, build_jsonld_block
from site_generator.services.seo import PageSeo, build_day_seo, build_home_seo

logger = logging.getLogger(__name__)


def compute_day_dates() -> tuple[date, date, date]:
    """Return *(yesterday, today, tomorrow)* in UTC."""
    today = datetime.now(timezone.utc).date()
    return today - timedelta(days=1), today, today + timedelta(days=1)


def format_display_date(d: date) -> str:
    """Cross-platform date format: ``April 3, 2026``."""
    return d.strftime("%B %d, %Y").replace(" 0", " ")


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


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def generate_site(config: Config) -> dict[str, Any]:
    """Fetch data, render templates, and write the static site atomically.

    Returns a summary dict with per-day match counts.
    """
    yesterday_date, today_date, tomorrow_date = compute_day_dates()
    logger.info(
        "Fetching PandaScore matches for %s / %s / %s",
        yesterday_date, today_date, tomorrow_date,
    )

    with PandaScoreClient(config.pandascore_token) as client:
        raw_yesterday = client.fetch_matches_for_day(yesterday_date)
        raw_today = client.fetch_matches_for_day(today_date)
        raw_tomorrow = client.fetch_matches_for_day(tomorrow_date)

    schedules = {
        "yesterday": build_day_schedule("yesterday", yesterday_date, normalize_matches(raw_yesterday)),
        "today": build_day_schedule("today", today_date, normalize_matches(raw_today)),
        "tomorrow": build_day_schedule("tomorrow", tomorrow_date, normalize_matches(raw_tomorrow)),
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _render_site(config, schedules, tmp_path)

        if config.output_dir.exists():
            shutil.rmtree(config.output_dir)
        shutil.copytree(tmp_path, config.output_dir)

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

    ctx_common = {"site_name": config.site_name, "schedules": schedules}

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
