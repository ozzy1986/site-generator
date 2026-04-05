from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE = "https://api.pandascore.co"
PAGE_SIZE = 100
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 15


class PandaScoreError(Exception):
    """Raised when PandaScore returns a non-success response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"PandaScore API {status_code}: {message}")


class PandaScoreClient:
    """Server-side HTTP client for the PandaScore REST API."""

    def __init__(self, token: str) -> None:
        self._session = self._build_session(token)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_matches_for_day(
        self,
        target_date: date,
        target_tz: tzinfo = timezone.utc,
    ) -> list[dict[str, Any]]:
        """Return matches whose *begin_at* falls on *target_date* in *target_tz*."""
        all_matches: dict[int | str, dict[str, Any]] = {}

        for query_date in self._query_dates_for_local_day(target_date, target_tz):
            fetched_for_query_date = 0
            page = 1

            while True:
                params: dict[str, Any] = {
                    "filter[begin_at]": query_date.isoformat(),
                    "sort": "begin_at",
                    "page[size]": PAGE_SIZE,
                    "page[number]": page,
                }
                resp = self._request("/matches", params)
                batch: list[dict[str, Any]] = resp.json()

                if not batch:
                    break

                for match in batch:
                    match_id = match.get("id")
                    key = match_id if match_id is not None else f"{query_date.isoformat()}-{len(all_matches)}"
                    all_matches[key] = match

                fetched_for_query_date += len(batch)
                total = int(resp.headers.get("X-Total", 0))
                if fetched_for_query_date >= total:
                    break
                page += 1

        return [m for m in all_matches.values() if self._match_on_date(m, target_date, target_tz)]

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> PandaScoreClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_session(token: str) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        url = f"{API_BASE}{path}"
        resp = self._session.get(url, params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))

        if resp.status_code == 429:
            raise PandaScoreError(429, "Rate limit exceeded. Try again later.")
        if resp.status_code == 401:
            raise PandaScoreError(401, "Invalid or missing API token.")
        if resp.status_code == 403:
            raise PandaScoreError(403, "Access forbidden — check your PandaScore plan.")
        if resp.status_code >= 400:
            raise PandaScoreError(resp.status_code, resp.text[:300])

        return resp

    @staticmethod
    def _match_on_date(
        match: dict[str, Any],
        target_date: date,
        target_tz: tzinfo = timezone.utc,
    ) -> bool:
        """Safety net: confirm *begin_at* really falls on *target_date* in *target_tz*."""
        begin_at = match.get("begin_at")
        if not begin_at:
            return False
        try:
            dt = datetime.fromisoformat(begin_at.replace("Z", "+00:00"))
            return dt.astimezone(target_tz).date() == target_date
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _query_dates_for_local_day(target_date: date, target_tz: tzinfo) -> tuple[date, ...]:
        """Return the UTC calendar dates that overlap the local day."""
        start_local = datetime.combine(target_date, time.min, tzinfo=target_tz)
        end_local = start_local + timedelta(days=1) - timedelta(microseconds=1)

        start_utc = start_local.astimezone(timezone.utc).date()
        end_utc = end_local.astimezone(timezone.utc).date()

        query_dates: list[date] = []
        current = start_utc
        while current <= end_utc:
            query_dates.append(current)
            current += timedelta(days=1)

        return tuple(query_dates)
