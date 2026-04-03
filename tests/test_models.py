from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from site_generator.models import (
    DaySchedule,
    MatchCard,
    MatchResult,
    TeamInfo,
    TournamentInfo,
    VideogameInfo,
    normalize_match,
)
from tests.conftest import make_finished_match, make_raw_match


class TestTeamInfo:
    def test_thumb_url(self) -> None:
        t = TeamInfo(id=1, name="X", image_url="https://cdn.pandascore.co/images/team/image/1/logo.png")
        assert t.thumb_image_url == "https://cdn.pandascore.co/images/team/image/1/thumb_logo.png"

    def test_thumb_url_none(self) -> None:
        t = TeamInfo(id=1, name="X", image_url=None)
        assert t.thumb_image_url is None


class TestMatchCardProperties:
    def _card(self, **kw: Any) -> MatchCard:
        defaults: dict[str, Any] = dict(
            id=1, name="A vs B", status="not_started", match_type="best_of",
            number_of_games=3,
            videogame=VideogameInfo(id=1, name="G", slug="g"),
            tournament=TournamentInfo(id=1, name="T", league_name="L"),
        )
        defaults.update(kw)
        return MatchCard(**defaults)

    def test_is_live(self) -> None:
        assert self._card(status="running").is_live is True
        assert self._card(status="finished").is_live is False

    def test_is_finished(self) -> None:
        assert self._card(status="finished").is_finished is True

    def test_is_upcoming(self) -> None:
        assert self._card(status="not_started").is_upcoming is True

    def test_score_display_two_results(self) -> None:
        card = self._card(results=(MatchResult(1, 2), MatchResult(2, 1)))
        assert card.score_display == "2 - 1"

    def test_score_display_no_results(self) -> None:
        assert self._card().score_display == ""

    def test_format_display_best_of(self) -> None:
        assert self._card(match_type="best_of", number_of_games=5).format_display == "Bo5"

    def test_format_display_first_to(self) -> None:
        assert self._card(match_type="first_to", number_of_games=3).format_display == "Ft3"

    def test_format_display_other(self) -> None:
        assert self._card(match_type="red_bull_home_ground").format_display == "Red Bull Home Ground"

    def test_status_display(self) -> None:
        assert self._card(status="running").status_display == "Идёт"
        assert self._card(status="canceled").status_display == "Отменён"


class TestDaySchedule:
    def test_display_label(self) -> None:
        assert DaySchedule(label="today", date_str="2026-04-03", display_date="3 апреля 2026").display_label == "Сегодня"


class TestNormalizeMatch:
    def test_full_payload(self, raw_match: dict[str, Any]) -> None:
        card = normalize_match(raw_match)

        assert card.id == 100001
        assert card.status == "not_started"
        assert card.match_type == "best_of"
        assert card.number_of_games == 3
        assert len(card.teams) == 2
        assert card.teams[0].name == "Team Alpha"
        assert card.videogame.name == "Counter-Strike"
        assert card.tournament.league_name == "Pro League"
        assert card.begin_at == datetime(2026, 4, 3, 14, 0, tzinfo=timezone.utc)
        assert card.stream_url == "https://twitch.tv/example"

    def test_finished_payload(self) -> None:
        raw = make_finished_match()
        card = normalize_match(raw)

        assert card.is_finished
        assert card.winner_id == 1
        assert card.score_display == "2 - 1"
        assert len(card.games) == 3

    def test_missing_opponents(self) -> None:
        raw = make_raw_match(opponents=[])
        card = normalize_match(raw)
        assert card.teams == ()

    def test_null_begin_at(self) -> None:
        raw = make_raw_match(begin_at=None)
        card = normalize_match(raw)
        assert card.begin_at is None

    def test_bad_datetime_is_none(self) -> None:
        raw = make_raw_match(begin_at="not-a-date")
        card = normalize_match(raw)
        assert card.begin_at is None

    def test_stream_prefers_main(self) -> None:
        raw = make_raw_match(streams_list=[
            {"raw_url": "https://a.tv", "main": False},
            {"raw_url": "https://b.tv", "main": True},
        ])
        card = normalize_match(raw)
        assert card.stream_url == "https://b.tv"

    def test_no_streams(self) -> None:
        raw = make_raw_match(streams_list=[])
        card = normalize_match(raw)
        assert card.stream_url is None

    def test_null_nested_objects(self) -> None:
        raw = make_raw_match(tournament=None, league=None, serie=None, videogame=None)
        card = normalize_match(raw)
        assert card.tournament.name == "Неизвестно"
        assert card.videogame.name == "Неизвестно"
