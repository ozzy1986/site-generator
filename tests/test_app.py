from __future__ import annotations

from unittest.mock import patch

import pytest

from app import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestAdminIndex:
    def test_get(self, client) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Generate Site" in resp.data


class TestGenerateEndpoint:
    @patch("app.generate_site")
    @patch("app.Config.from_env")
    def test_success(self, mock_config, mock_gen, client) -> None:
        mock_gen.return_value = {"yesterday": 5, "today": 10, "tomorrow": 8}
        resp = client.post("/generate")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    @patch("app.Config.from_env", side_effect=ValueError("PANDASCORE_TOKEN"))
    def test_missing_token(self, mock_config, client) -> None:
        resp = client.post("/generate")
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    @patch("app.generate_site", side_effect=Exception("boom"))
    @patch("app.Config.from_env")
    def test_unexpected_error(self, mock_config, mock_gen, client) -> None:
        resp = client.post("/generate")
        assert resp.status_code == 500


class TestOpenOutput:
    @patch("app.Config.from_env")
    def test_no_dir(self, mock_config, client, tmp_path) -> None:
        mock_config.return_value.output_dir = tmp_path / "nonexistent"
        resp = client.post("/open-output")
        assert resp.status_code == 404
