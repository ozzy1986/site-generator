from __future__ import annotations

import json

from site_generator.models import DaySchedule, MatchCard, TeamInfo, TournamentInfo, VideogameInfo
from site_generator.services.schema import (
    build_home_jsonld,
    build_jsonld_block,
    build_organization,
    build_sports_event,
)

SITE_URL = "https://example.com"
SITE_NAME = "TestSite"


def _match(**kw) -> MatchCard:
    defaults = dict(
        id=1, name="A vs B", status="not_started", match_type="best_of",
        number_of_games=3,
        videogame=VideogameInfo(id=3, name="Counter-Strike", slug="cs-go"),
        tournament=TournamentInfo(id=1, name="Playoffs", league_name="Pro League"),
        teams=(TeamInfo(id=1, name="A", image_url="https://img/a.png"), TeamInfo(id=2, name="B")),
    )
    defaults.update(kw)
    return MatchCard(**defaults)


class TestOrganization:
    def test_fields(self) -> None:
        org = build_organization(SITE_URL, SITE_NAME)
        assert org["@type"] == "Organization"
        assert org["name"] == SITE_NAME
        assert org["url"] == SITE_URL


class TestSportsEvent:
    def test_basic(self) -> None:
        ev = build_sports_event(_match())
        assert ev["@type"] == "SportsEvent"
        assert ev["name"] == "A vs B"
        assert ev["sport"] == "Counter-Strike"

    def test_status_mapping(self) -> None:
        assert "Scheduled" in build_sports_event(_match(status="not_started"))["eventStatus"]
        assert "Completed" in build_sports_event(_match(status="finished"))["eventStatus"]
        assert "Cancelled" in build_sports_event(_match(status="canceled"))["eventStatus"]
        assert "Postponed" in build_sports_event(_match(status="postponed"))["eventStatus"]

    def test_competitors(self) -> None:
        ev = build_sports_event(_match())
        assert len(ev["competitor"]) == 2
        assert ev["competitor"][0]["name"] == "A"
        assert "logo" in ev["competitor"][0]
        assert "logo" not in ev["competitor"][1]

    def test_location_online(self) -> None:
        ev = build_sports_event(_match(stream_url="https://twitch.tv/x"))
        assert ev["location"]["@type"] == "VirtualLocation"
        assert ev["location"]["url"] == "https://twitch.tv/x"

    def test_super_event(self) -> None:
        ev = build_sports_event(_match())
        assert "Pro League" in ev["superEvent"]["name"]


class TestJsonLdBlock:
    def test_valid_json(self) -> None:
        schedule = DaySchedule(
            label="today", date_str="2026-04-03", display_date="April 3, 2026",
            matches=(_match(),),
        )
        raw = build_jsonld_block(schedule, SITE_URL, SITE_NAME)
        data = json.loads(raw)
        assert data["@context"] == "https://schema.org"
        assert len(data["@graph"]) == 2  # Organization + 1 SportsEvent


class TestHomeJsonLd:
    def test_valid_json(self) -> None:
        raw = build_home_jsonld(SITE_URL, SITE_NAME)
        data = json.loads(raw)
        assert data["@context"] == "https://schema.org"
        assert data["@graph"][0]["@type"] == "Organization"
