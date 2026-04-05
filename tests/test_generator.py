from __future__ import annotations

import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from site_generator.config import Config
from site_generator.services.generator import (
    build_day_schedule,
    compute_day_dates,
    format_display_date,
    generate_site,
    normalize_matches,
)
from tests.conftest import make_raw_match


class TestComputeDayDates:
    def test_returns_three_consecutive_dates(self) -> None:
        msk = ZoneInfo("Europe/Moscow")
        yesterday, today, tomorrow = compute_day_dates(
            msk,
            now=datetime(2026, 4, 4, 21, 30, tzinfo=timezone.utc),
        )
        assert yesterday == date(2026, 4, 4)
        assert today == date(2026, 4, 5)
        assert tomorrow == date(2026, 4, 6)


class TestFormatDisplayDate:
    def test_no_leading_zero(self) -> None:
        assert format_display_date(date(2026, 4, 3)) == "3 апреля 2026"

    def test_double_digit_day(self) -> None:
        assert format_display_date(date(2026, 12, 15)) == "15 декабря 2026"


class TestBuildDaySchedule:
    def test_sorts_by_begin_at(self) -> None:
        from site_generator.models import MatchCard, TournamentInfo, VideogameInfo

        late = MatchCard(
            id=1, name="Late", status="not_started", match_type="best_of",
            number_of_games=1,
            videogame=VideogameInfo(id=1, name="G", slug="g"),
            tournament=TournamentInfo(id=1, name="T", league_name="L"),
            begin_at=datetime(2026, 4, 3, 20, 0, tzinfo=timezone.utc),
        )
        early = MatchCard(
            id=2, name="Early", status="not_started", match_type="best_of",
            number_of_games=1,
            videogame=VideogameInfo(id=1, name="G", slug="g"),
            tournament=TournamentInfo(id=1, name="T", league_name="L"),
            begin_at=datetime(2026, 4, 3, 8, 0, tzinfo=timezone.utc),
        )
        schedule = build_day_schedule("today", date(2026, 4, 3), [late, early])
        assert schedule.matches[0].name == "Early"
        assert schedule.matches[1].name == "Late"


class TestNormalizeMatches:
    def test_list(self) -> None:
        raws = [make_raw_match(id=i) for i in range(3)]
        cards = normalize_matches(raws)
        assert len(cards) == 3
        assert cards[0].id == 0


class TestGenerateSiteIntegration:
    """Smoke test: wire real templates → verify output structure."""

    @patch("site_generator.services.generator.PandaScoreClient")
    def test_produces_all_pages(
        self, MockClient: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PANDASCORE_TOKEN", "tok")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Copy real templates and static assets
        src_root = Path(__file__).resolve().parent.parent
        shutil.copytree(src_root / "templates" / "site", project_dir / "templates" / "site")
        static_src = src_root / "static" / "site"
        if static_src.exists():
            shutil.copytree(static_src, project_dir / "static" / "site")

        config = Config(
            pandascore_token="tok",
            site_url="https://test.local",
            site_name="Test",
            site_timezone="Europe/Moscow",
            output_dir=project_dir / "generated_site",
            base_dir=project_dir,
        )

        instance = MockClient.return_value.__enter__.return_value
        instance.fetch_matches_for_day.return_value = [make_raw_match(id=i) for i in range(1, 5)]

        result = generate_site(config)

        assert (config.output_dir / "index.html").exists()
        assert (config.output_dir / "yesterday" / "index.html").exists()
        assert (config.output_dir / "today" / "index.html").exists()
        assert (config.output_dir / "tomorrow" / "index.html").exists()
        home_html = (config.output_dir / "index.html").read_text(encoding="utf-8")
        today_html = (config.output_dir / "today" / "index.html").read_text(encoding="utf-8")
        assert "Киберспорт без лишнего шума" not in home_html
        assert '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">' in home_html
        assert 'rel="preconnect" href="https://cdn.pandascore.co"' in home_html
        assert "Матчи по дням" in home_html
        assert "Часовой пояс: МСК" in today_html
        assert "17:00 МСК" in today_html
        assert 'loading="eager"' in today_html
        assert 'loading="lazy"' in today_html
        assert 'decoding="async"' in today_html
        assert 'fetchpriority="low"' in today_html
        assert result["today"] >= 0

    @patch("site_generator.services.generator.PandaScoreClient")
    def test_normalizes_output_permissions_after_generation(
        self, MockClient: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PANDASCORE_TOKEN", "tok")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        src_root = Path(__file__).resolve().parent.parent
        shutil.copytree(src_root / "templates" / "site", project_dir / "templates" / "site")
        static_src = src_root / "static" / "site"
        if static_src.exists():
            shutil.copytree(static_src, project_dir / "static" / "site")

        config = Config(
            pandascore_token="tok",
            site_url="https://test.local",
            site_name="Test",
            site_timezone="Europe/Moscow",
            output_dir=project_dir / "generated_site",
            base_dir=project_dir,
        )

        instance = MockClient.return_value.__enter__.return_value
        instance.fetch_matches_for_day.return_value = [make_raw_match()]

        with patch("site_generator.services.generator._ensure_public_permissions") as ensure_permissions:
            generate_site(config)

        ensure_permissions.assert_called_once_with(config.output_dir)

    @patch("site_generator.services.generator.PandaScoreClient")
    def test_empty_day(
        self, MockClient: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PANDASCORE_TOKEN", "tok")

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        src_root = Path(__file__).resolve().parent.parent
        shutil.copytree(src_root / "templates" / "site", project_dir / "templates" / "site")
        static_src = src_root / "static" / "site"
        if static_src.exists():
            shutil.copytree(static_src, project_dir / "static" / "site")

        config = Config(
            pandascore_token="tok",
            site_url="https://test.local",
            site_name="Test",
            site_timezone="Europe/Moscow",
            output_dir=project_dir / "generated_site",
            base_dir=project_dir,
        )

        instance = MockClient.return_value.__enter__.return_value
        instance.fetch_matches_for_day.return_value = []

        result = generate_site(config)

        assert result["today"] == 0
        html = (config.output_dir / "today" / "index.html").read_text(encoding="utf-8")
        assert "На этот день матчей пока нет." in html
