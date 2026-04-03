from __future__ import annotations

import json
from typing import Any

from site_generator.models import DaySchedule, MatchCard

_STATUS_MAP: dict[str, str] = {
    "not_started": "https://schema.org/EventScheduled",
    "running": "https://schema.org/EventScheduled",
    "finished": "https://schema.org/EventCompleted",
    "canceled": "https://schema.org/EventCancelled",
    "postponed": "https://schema.org/EventPostponed",
}


def build_organization(site_url: str, site_name: str) -> dict[str, Any]:
    return {
        "@type": "Organization",
        "name": site_name,
        "url": site_url,
        "logo": f"{site_url}/assets/logo.svg",
    }


def build_sports_event(match: MatchCard) -> dict[str, Any]:
    event: dict[str, Any] = {
        "@type": "SportsEvent",
        "name": match.name,
        "eventStatus": _STATUS_MAP.get(match.status, _STATUS_MAP["not_started"]),
        "sport": match.videogame.name,
    }

    if match.begin_at:
        event["startDate"] = match.begin_at.isoformat()
    if match.end_at:
        event["endDate"] = match.end_at.isoformat()

    if match.teams:
        event["competitor"] = [
            {
                "@type": "SportsTeam",
                "name": t.name,
                **({"logo": t.image_url} if t.image_url else {}),
            }
            for t in match.teams
        ]

    location: dict[str, Any] = {"@type": "VirtualLocation", "name": "Online"}
    if match.stream_url:
        location["url"] = match.stream_url
    event["location"] = location

    if match.tournament:
        event["superEvent"] = {
            "@type": "SportsEvent",
            "name": f"{match.tournament.league_name} — {match.tournament.name}",
        }

    return event


def build_jsonld_block(
    schedule: DaySchedule,
    site_url: str,
    site_name: str,
) -> str:
    """Return a complete JSON-LD ``<script>`` body for a day page."""
    graph: dict[str, Any] = {
        "@context": "https://schema.org",
        "@graph": [
            build_organization(site_url, site_name),
            *(build_sports_event(m) for m in schedule.matches),
        ],
    }
    return json.dumps(graph, ensure_ascii=False, indent=2)


def build_home_jsonld(site_url: str, site_name: str) -> str:
    """Return a JSON-LD ``<script>`` body for the home page."""
    graph: dict[str, Any] = {
        "@context": "https://schema.org",
        "@graph": [build_organization(site_url, site_name)],
    }
    return json.dumps(graph, ensure_ascii=False, indent=2)
