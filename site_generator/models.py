from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TeamInfo:
    id: int
    name: str
    image_url: str | None = None

    @property
    def thumb_image_url(self) -> str | None:
        """PandaScore CDN thumbnail variant for faster loading."""
        if not self.image_url:
            return None
        parts = self.image_url.rsplit("/", 1)
        if len(parts) == 2:
            return f"{parts[0]}/thumb_{parts[1]}"
        return self.image_url


@dataclass(frozen=True)
class TournamentInfo:
    id: int
    name: str
    league_name: str
    league_image_url: str | None = None
    serie_full_name: str | None = None


@dataclass(frozen=True)
class VideogameInfo:
    id: int
    name: str
    slug: str


@dataclass(frozen=True)
class GameInfo:
    position: int
    status: str
    winner_id: int | None = None
    length: int | None = None


@dataclass(frozen=True)
class MatchResult:
    team_id: int
    score: int


@dataclass(frozen=True)
class MatchCard:
    id: int
    name: str
    status: str
    match_type: str
    number_of_games: int
    videogame: VideogameInfo
    tournament: TournamentInfo
    teams: tuple[TeamInfo, ...] = ()
    games: tuple[GameInfo, ...] = ()
    results: tuple[MatchResult, ...] = ()
    begin_at: datetime | None = None
    end_at: datetime | None = None
    winner_id: int | None = None
    forfeit: bool = False
    rescheduled: bool = False
    stream_url: str | None = None

    @property
    def is_live(self) -> bool:
        return self.status == "running"

    @property
    def is_finished(self) -> bool:
        return self.status == "finished"

    @property
    def is_upcoming(self) -> bool:
        return self.status == "not_started"

    @property
    def score_display(self) -> str:
        if len(self.results) >= 2:
            return f"{self.results[0].score} - {self.results[1].score}"
        return ""

    @property
    def format_display(self) -> str:
        if self.match_type == "best_of":
            return f"Bo{self.number_of_games}"
        if self.match_type == "first_to":
            return f"Ft{self.number_of_games}"
        return self.match_type.replace("_", " ").title()

    @property
    def status_display(self) -> str:
        return {
            "not_started": "Upcoming",
            "running": "Live",
            "finished": "Finished",
            "canceled": "Canceled",
            "postponed": "Postponed",
        }.get(self.status, self.status.replace("_", " ").title())


@dataclass(frozen=True)
class DaySchedule:
    label: str
    date_str: str
    display_date: str
    matches: tuple[MatchCard, ...] = ()


# ---------------------------------------------------------------------------
# Normalization: raw PandaScore JSON → typed models
# ---------------------------------------------------------------------------

def normalize_match(raw: dict[str, Any]) -> MatchCard:
    """Transform a raw PandaScore match dict into a MatchCard."""
    teams = tuple(
        TeamInfo(
            id=opp["opponent"]["id"],
            name=opp["opponent"]["name"],
            image_url=opp["opponent"].get("image_url"),
        )
        for opp in raw.get("opponents", [])
        if isinstance(opp, dict) and "opponent" in opp
    )

    tournament_raw = raw.get("tournament") or {}
    league_raw = raw.get("league") or {}
    serie_raw = raw.get("serie") or {}
    videogame_raw = raw.get("videogame") or {}

    tournament = TournamentInfo(
        id=tournament_raw.get("id", 0),
        name=tournament_raw.get("name", "Unknown"),
        league_name=league_raw.get("name", "Unknown"),
        league_image_url=league_raw.get("image_url"),
        serie_full_name=serie_raw.get("full_name"),
    )

    videogame = VideogameInfo(
        id=videogame_raw.get("id", 0),
        name=videogame_raw.get("name", "Unknown"),
        slug=videogame_raw.get("slug", ""),
    )

    games = tuple(
        GameInfo(
            position=g.get("position", 0),
            status=g.get("status", "not_started"),
            winner_id=(g.get("winner") or {}).get("id"),
            length=g.get("length"),
        )
        for g in raw.get("games", [])
        if isinstance(g, dict)
    )

    results = tuple(
        MatchResult(team_id=r.get("team_id", 0), score=r.get("score", 0))
        for r in raw.get("results", [])
        if isinstance(r, dict)
    )

    streams = raw.get("streams_list") or []
    stream_url: str | None = None
    for s in streams:
        if isinstance(s, dict) and s.get("raw_url"):
            stream_url = s["raw_url"]
            if s.get("main"):
                break

    return MatchCard(
        id=raw["id"],
        name=raw.get("name", ""),
        status=raw.get("status", "not_started"),
        match_type=raw.get("match_type", "best_of"),
        number_of_games=raw.get("number_of_games", 0),
        videogame=videogame,
        tournament=tournament,
        teams=teams,
        games=games,
        results=results,
        begin_at=_parse_datetime(raw.get("begin_at")),
        end_at=_parse_datetime(raw.get("end_at")),
        winner_id=raw.get("winner_id"),
        forfeit=raw.get("forfeit", False),
        rescheduled=raw.get("rescheduled", False),
        stream_url=stream_url,
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
