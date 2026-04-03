from __future__ import annotations

from dataclasses import dataclass

from site_generator.models import DaySchedule


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
        title = f"Esports Results: {schedule.display_date}"
        desc = (
            f"{n} esports match result{'s' if n != 1 else ''} from "
            f"{schedule.display_date}. Scores, teams, and tournament details."
        )
    elif schedule.label == "today":
        title = f"Esports Matches Today: {schedule.display_date}"
        desc = (
            f"{n} esports match{'es' if n != 1 else ''} scheduled for today, "
            f"{schedule.display_date}. Live scores and upcoming games."
        )
    else:
        title = f"Upcoming Esports Matches: {schedule.display_date}"
        desc = (
            f"{n} esports match{'es' if n != 1 else ''} scheduled for "
            f"{schedule.display_date}. Preview upcoming tournaments and matchups."
        )

    keywords = ", ".join(
        ["esports", "matches", "schedule", schedule.display_date] + extra_kw,
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
        og_image=f"{site_url}/assets/og-image.png",
    )


def build_home_seo(site_url: str, site_name: str) -> PageSeo:
    """Build SEO metadata for the landing/index page."""
    return PageSeo(
        title=f"{site_name} — Yesterday, Today, Tomorrow",
        description=(
            "Browse esports match schedules, live scores, and results "
            "across all major competitive games. Updated daily."
        ),
        keywords="esports, matches, schedule, results, live scores, tournaments",
        canonical_url=f"{site_url}/",
        og_title=site_name,
        og_description=(
            "Browse esports match schedules, live scores, and results. "
            "Updated daily."
        ),
        og_url=f"{site_url}/",
        og_image=f"{site_url}/assets/og-image.png",
    )
