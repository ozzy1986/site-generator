from __future__ import annotations

from site_generator.models import DaySchedule, MatchCard, TournamentInfo, VideogameInfo
from site_generator.services.seo import PageSeo, build_day_seo, build_home_seo

SITE_URL = "https://example.com"
SITE_NAME = "TestSite"


def _schedule(label: str, n_matches: int = 2) -> DaySchedule:
    cards = tuple(
        MatchCard(
            id=i,
            name=f"Match {i}",
            status="not_started",
            match_type="best_of",
            number_of_games=3,
            videogame=VideogameInfo(id=3, name="Counter-Strike", slug="cs-go"),
            tournament=TournamentInfo(id=1, name="T", league_name="L"),
        )
        for i in range(n_matches)
    )
    return DaySchedule(label=label, date_str="2026-04-03", display_date="3 апреля 2026", matches=cards)


class TestBuildDaySeo:
    def test_yesterday(self) -> None:
        seo = build_day_seo(_schedule("yesterday"), SITE_URL, SITE_NAME)
        assert "Результаты" in seo.title
        assert seo.canonical_url == f"{SITE_URL}/yesterday/"
        assert seo.robots == "index, follow"

    def test_today(self) -> None:
        seo = build_day_seo(_schedule("today"), SITE_URL, SITE_NAME)
        assert "сегодня" in seo.title

    def test_tomorrow(self) -> None:
        seo = build_day_seo(_schedule("tomorrow"), SITE_URL, SITE_NAME)
        assert "завтра" in seo.title

    def test_og_fields(self) -> None:
        seo = build_day_seo(_schedule("today"), SITE_URL, SITE_NAME)
        assert seo.og_url == f"{SITE_URL}/today/"
        assert seo.og_image.startswith(SITE_URL)

    def test_keywords_include_videogame(self) -> None:
        seo = build_day_seo(_schedule("today"), SITE_URL, SITE_NAME)
        assert "Counter-Strike" in seo.keywords

    def test_empty_day(self) -> None:
        seo = build_day_seo(_schedule("today", 0), SITE_URL, SITE_NAME)
        assert "0 киберспортивных матчей" in seo.description

    def test_singular_match(self) -> None:
        seo = build_day_seo(_schedule("today", 1), SITE_URL, SITE_NAME)
        assert "1 киберспортивного матча" in seo.description


class TestBuildHomeSeo:
    def test_structure(self) -> None:
        seo = build_home_seo(SITE_URL, SITE_NAME)
        assert isinstance(seo, PageSeo)
        assert SITE_NAME in seo.title
        assert "вчера, сегодня, завтра" in seo.title
        assert seo.canonical_url == f"{SITE_URL}/"
        assert seo.robots == "index, follow"
