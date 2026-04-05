from __future__ import annotations

from dataclasses import dataclass

from site_generator.models import DaySchedule

_DAY_TITLE_PREFIXES = {
    "yesterday": "Результаты киберспортивных матчей",
    "today": "Киберспортивные матчи сегодня",
    "tomorrow": "Киберспортивные матчи завтра",
}


def _match_phrase(count: int) -> str:
    remainder_100 = count % 100
    remainder_10 = count % 10

    if 11 <= remainder_100 <= 14:
        noun = "киберспортивных матчей"
    elif remainder_10 == 1:
        noun = "киберспортивного матча"
    elif 2 <= remainder_10 <= 4:
        noun = "киберспортивных матча"
    else:
        noun = "киберспортивных матчей"

    return f"{count} {noun}"


@dataclass(frozen=True)
class PageSeo:
    title: str
    description: str
    keywords: str
    canonical_url: str
    og_title: str
    og_description: str
    og_url: str
    og_image: str
    robots: str = "index, follow"


def build_day_seo(
    schedule: DaySchedule,
    site_url: str,
    site_name: str,
) -> PageSeo:
    """Build full SEO metadata for a day schedule page."""
    n = len(schedule.matches)
    videogames = sorted({m.videogame.name for m in schedule.matches})
    extra_kw = videogames[:8]

    if schedule.label == "yesterday":
        title = f"{_DAY_TITLE_PREFIXES[schedule.label]}: {schedule.display_date}"
        desc = (
            f"Результаты {_match_phrase(n)} за {schedule.display_date}: "
            "счёты, команды, турниры и статус встреч."
        )
    elif schedule.label == "today":
        title = f"{_DAY_TITLE_PREFIXES[schedule.label]}: {schedule.display_date}"
        desc = (
            f"Расписание {_match_phrase(n)} на {schedule.display_date}: "
            "живые статусы, турниры, команды и ближайшие игры."
        )
    else:
        title = f"{_DAY_TITLE_PREFIXES[schedule.label]}: {schedule.display_date}"
        desc = (
            f"Анонс {_match_phrase(n)} на {schedule.display_date}: "
            "предстоящие турниры, пары команд и формат встреч."
        )

    keywords = ", ".join(
        ["киберспорт", "матчи", "расписание", "результаты", schedule.display_date] + extra_kw,
    )
    canonical = f"{site_url}/{schedule.label}/"

    return PageSeo(
        title=f"{title} | {site_name}",
        description=desc,
        keywords=keywords,
        canonical_url=canonical,
        og_title=title,
        og_description=desc,
        og_url=canonical,
        og_image=f"{site_url}/assets/logo.svg",
    )


def build_home_seo(site_url: str, site_name: str) -> PageSeo:
    """Build SEO metadata for the landing/index page."""
    page_title = f"{site_name} — вчера, сегодня, завтра"
    return PageSeo(
        title=page_title,
        description=(
            "Расписание, результаты и актуальные статусы киберспортивных матчей "
            "на вчера, сегодня и завтра. Обновляется ежедневно."
        ),
        keywords="киберспорт, матчи, расписание, результаты, live, турниры",
        canonical_url=f"{site_url}/",
        # Same as <title>: avoid og:title duplicating og:site_name in crawlers/snippets.
        og_title=page_title,
        og_description=(
            "Смотрите расписание, результаты и статусы киберспортивных матчей. "
            "Обновляется ежедневно."
        ),
        og_url=f"{site_url}/",
        og_image=f"{site_url}/assets/logo.svg",
    )
