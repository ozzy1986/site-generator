from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from site_generator.config import Config
from site_generator.models import (
    DaySchedule,
    GameInfo,
    MatchCard,
    MatchResult,
    TeamInfo,
    TournamentInfo,
    VideogameInfo,
)

FIXTURES_DIR = Path(__file__).parent


@pytest.fixture()
def env_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANDASCORE_TOKEN", "test-token-123")


@pytest.fixture()
def sample_config(tmp_path: Path, env_with_token: None) -> Config:
    return Config.from_env(base_dir=tmp_path)


def make_raw_match(**overrides: Any) -> dict[str, Any]:
    """Factory for a realistic raw PandaScore match dict."""
    base: dict[str, Any] = {
        "id": 100001,
        "name": "Round 1: Team Alpha vs Team Beta",
        "status": "not_started",
        "match_type": "best_of",
        "number_of_games": 3,
        "begin_at": "2026-04-03T14:00:00Z",
        "end_at": None,
        "winner_id": None,
        "forfeit": False,
        "rescheduled": False,
        "opponents": [
            {
                "opponent": {
                    "id": 1,
                    "name": "Team Alpha",
                    "image_url": "https://cdn.pandascore.co/images/team/image/1/alpha.png",
                },
                "type": "Team",
            },
            {
                "opponent": {
                    "id": 2,
                    "name": "Team Beta",
                    "image_url": "https://cdn.pandascore.co/images/team/image/2/beta.png",
                },
                "type": "Team",
            },
        ],
        "tournament": {"id": 500, "name": "Playoffs"},
        "league": {
            "id": 300,
            "name": "Pro League",
            "image_url": "https://cdn.pandascore.co/images/league/image/300/proleague.png",
        },
        "serie": {"full_name": "Pro League Season 1 2026"},
        "videogame": {"id": 3, "name": "Counter-Strike", "slug": "cs-go"},
        "games": [
            {"position": 1, "status": "not_started", "winner": {"id": None, "type": "Team"}, "length": None},
            {"position": 2, "status": "not_started", "winner": {"id": None, "type": "Team"}, "length": None},
            {"position": 3, "status": "not_started", "winner": {"id": None, "type": "Team"}, "length": None},
        ],
        "results": [],
        "streams_list": [
            {"raw_url": "https://twitch.tv/example", "main": True, "language": "en"},
        ],
    }
    base.update(overrides)
    return base


def make_finished_match(**overrides: Any) -> dict[str, Any]:
    return make_raw_match(
        status="finished",
        end_at="2026-04-03T16:30:00Z",
        winner_id=1,
        results=[{"team_id": 1, "score": 2}, {"team_id": 2, "score": 1}],
        games=[
            {"position": 1, "status": "finished", "winner": {"id": 1, "type": "Team"}, "length": 2400},
            {"position": 2, "status": "finished", "winner": {"id": 2, "type": "Team"}, "length": 3100},
            {"position": 3, "status": "finished", "winner": {"id": 1, "type": "Team"}, "length": 2800},
        ],
        **overrides,
    )


@pytest.fixture()
def raw_match() -> dict[str, Any]:
    return make_raw_match()


@pytest.fixture()
def raw_finished_match() -> dict[str, Any]:
    return make_finished_match()


@pytest.fixture()
def sample_match_card() -> MatchCard:
    return MatchCard(
        id=100001,
        name="Round 1: Team Alpha vs Team Beta",
        status="not_started",
        match_type="best_of",
        number_of_games=3,
        videogame=VideogameInfo(id=3, name="Counter-Strike", slug="cs-go"),
        tournament=TournamentInfo(
            id=500, name="Playoffs", league_name="Pro League",
            league_image_url="https://cdn.pandascore.co/images/league/image/300/proleague.png",
        ),
        teams=(
            TeamInfo(id=1, name="Team Alpha", image_url="https://cdn.pandascore.co/images/team/image/1/alpha.png"),
            TeamInfo(id=2, name="Team Beta", image_url="https://cdn.pandascore.co/images/team/image/2/beta.png"),
        ),
        begin_at=datetime(2026, 4, 3, 14, 0, tzinfo=timezone.utc),
        stream_url="https://twitch.tv/example",
    )


@pytest.fixture()
def sample_day_schedule(sample_match_card: MatchCard) -> DaySchedule:
    return DaySchedule(
        label="today",
        date_str="2026-04-03",
        display_date="April 3, 2026",
        matches=(sample_match_card,),
    )
