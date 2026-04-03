from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from site_generator.pandascore_client import PandaScoreClient, PandaScoreError


class TestPandaScoreClient:
    def _client(self) -> PandaScoreClient:
        return PandaScoreClient(token="test-token")

    def test_auth_header(self) -> None:
        client = self._client()
        assert client._session.headers["Authorization"] == "Bearer test-token"
        client.close()

    def test_context_manager(self) -> None:
        with self._client() as client:
            assert client._session is not None

    @patch.object(PandaScoreClient, "_request")
    def test_fetch_matches_single_page(self, mock_req: MagicMock) -> None:
        resp = MagicMock()
        resp.json.return_value = [{"id": 1, "begin_at": "2026-04-03T10:00:00Z"}]
        resp.headers = {"X-Total": "1"}
        mock_req.return_value = resp

        with self._client() as client:
            matches = client.fetch_matches_for_day(date(2026, 4, 3))

        assert len(matches) == 1
        mock_req.assert_called_once()
        call_params = mock_req.call_args[0][1]
        assert call_params["filter[begin_at]"] == "2026-04-03"
        assert call_params["sort"] == "begin_at"

    @patch.object(PandaScoreClient, "_request")
    def test_fetch_matches_pagination(self, mock_req: MagicMock) -> None:
        page1 = MagicMock()
        page1.json.return_value = [{"id": i, "begin_at": "2026-04-03T10:00:00Z"} for i in range(100)]
        page1.headers = {"X-Total": "150"}

        page2 = MagicMock()
        page2.json.return_value = [{"id": i, "begin_at": "2026-04-03T12:00:00Z"} for i in range(100, 150)]
        page2.headers = {"X-Total": "150"}

        mock_req.side_effect = [page1, page2]

        with self._client() as client:
            matches = client.fetch_matches_for_day(date(2026, 4, 3))

        assert len(matches) == 150
        assert mock_req.call_count == 2

    @patch.object(PandaScoreClient, "_request")
    def test_fetch_matches_empty(self, mock_req: MagicMock) -> None:
        resp = MagicMock()
        resp.json.return_value = []
        resp.headers = {"X-Total": "0"}
        mock_req.return_value = resp

        with self._client() as client:
            matches = client.fetch_matches_for_day(date(2026, 4, 3))

        assert matches == []

    @patch.object(PandaScoreClient, "_request")
    def test_filters_wrong_date(self, mock_req: MagicMock) -> None:
        resp = MagicMock()
        resp.json.return_value = [
            {"id": 1, "begin_at": "2026-04-03T10:00:00Z"},
            {"id": 2, "begin_at": "2026-04-04T01:00:00Z"},
        ]
        resp.headers = {"X-Total": "2"}
        mock_req.return_value = resp

        with self._client() as client:
            matches = client.fetch_matches_for_day(date(2026, 4, 3))

        assert len(matches) == 1
        assert matches[0]["id"] == 1


class TestPandaScoreErrors:
    def _make_response(self, status: int, text: str = "err") -> MagicMock:
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status
        resp.text = text
        resp.headers = {}
        return resp

    def test_401(self) -> None:
        client = PandaScoreClient.__new__(PandaScoreClient)
        client._session = MagicMock()
        client._session.get.return_value = self._make_response(401)
        with pytest.raises(PandaScoreError, match="401"):
            client._request("/matches")
        client._session.close()

    def test_429(self) -> None:
        client = PandaScoreClient.__new__(PandaScoreClient)
        client._session = MagicMock()
        client._session.get.return_value = self._make_response(429)
        with pytest.raises(PandaScoreError, match="Rate limit"):
            client._request("/matches")
        client._session.close()

    def test_403(self) -> None:
        client = PandaScoreClient.__new__(PandaScoreClient)
        client._session = MagicMock()
        client._session.get.return_value = self._make_response(403)
        with pytest.raises(PandaScoreError, match="403"):
            client._request("/matches")
        client._session.close()

    def test_generic_4xx(self) -> None:
        client = PandaScoreClient.__new__(PandaScoreClient)
        client._session = MagicMock()
        client._session.get.return_value = self._make_response(422, "bad entity")
        with pytest.raises(PandaScoreError, match="422"):
            client._request("/matches")
        client._session.close()


class TestMatchOnDate:
    def test_matching(self) -> None:
        assert PandaScoreClient._match_on_date(
            {"begin_at": "2026-04-03T23:59:00Z"}, date(2026, 4, 3),
        ) is True

    def test_not_matching(self) -> None:
        assert PandaScoreClient._match_on_date(
            {"begin_at": "2026-04-04T00:01:00Z"}, date(2026, 4, 3),
        ) is False

    def test_null_begin_at(self) -> None:
        assert PandaScoreClient._match_on_date({"begin_at": None}, date(2026, 4, 3)) is False

    def test_bad_format(self) -> None:
        assert PandaScoreClient._match_on_date({"begin_at": "nope"}, date(2026, 4, 3)) is False
