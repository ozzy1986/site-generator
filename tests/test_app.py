from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app import app
from site_generator.config import Config


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestAdminIndex:
    def test_get(self, client) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Собрать сайт".encode("utf-8") in resp.data
        assert "Скачать сгенерированный сайт".encode("utf-8") in resp.data
        assert "Журнал сервиса".encode("utf-8") in resp.data

    def test_admin_alias(self, client) -> None:
        resp = client.get("/admin")
        assert resp.status_code == 200
        assert "Панель управления".encode("utf-8") in resp.data

    def test_admin_static_alias(self, client) -> None:
        resp = client.get("/admin/static/admin/styles.css")
        assert resp.status_code == 200


class TestGenerateEndpoint:
    @patch("app.generate_site")
    @patch("app.Config.from_env")
    def test_success(self, mock_config, mock_gen, client) -> None:
        mock_gen.return_value = {
            "yesterday": 5,
            "today": 10,
            "tomorrow": 8,
            "duration_seconds": 3.0,
        }
        resp = client.post("/generate")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "Сайт успешно собран и обновлён за 3 секунды." == data["message"]
        assert data["counts"] == {"yesterday": 5, "today": 10, "tomorrow": 8}

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


class TestDownloadSite:
    @patch("app.Config.from_env")
    def test_returns_zip_with_files(self, mock_config, client, tmp_path: Path) -> None:
        out = tmp_path / "generated_site"
        out.mkdir()
        (out / "index.html").write_text("<html>ok</html>", encoding="utf-8")
        mock_config.return_value = Config(
            pandascore_token="tok",
            site_url="https://example.com",
            site_name="Test",
            site_timezone="UTC",
            output_dir=out,
            base_dir=tmp_path,
        )

        resp = client.get("/download-site")

        assert resp.status_code == 200
        assert resp.mimetype == "application/zip"
        zf = zipfile.ZipFile(io.BytesIO(resp.data))
        names = zf.namelist()
        assert "index.html" in names

    @patch("app.Config.from_env")
    def test_missing_output_dir(self, mock_config, client, tmp_path: Path) -> None:
        missing = tmp_path / "nope"
        mock_config.return_value = Config(
            pandascore_token="tok",
            site_url="https://example.com",
            site_name="Test",
            site_timezone="UTC",
            output_dir=missing,
            base_dir=tmp_path,
        )

        resp = client.get("/download-site")

        assert resp.status_code == 404

    @patch("app.Config.from_env", side_effect=ValueError("Не задана переменная окружения PANDASCORE_TOKEN"))
    def test_missing_token(self, mock_config, client) -> None:
        resp = client.get("/download-site")
        assert resp.status_code == 400


class TestServiceLog:
    @patch("app._read_service_journal_tail")
    def test_returns_lines(self, mock_tail, client) -> None:
        mock_tail.return_value = (True, "", ["alpha", "beta"])
        resp = client.get("/service-log")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["lines"] == ["alpha", "beta"]

    @patch("app._read_service_journal_tail")
    def test_returns_message_when_unavailable(self, mock_tail, client) -> None:
        mock_tail.return_value = (False, "Журнал недоступен.", [])
        resp = client.get("/service-log")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is False
        assert data["message"] == "Журнал недоступен."
