from __future__ import annotations

from pathlib import Path

import pytest

from site_generator.config import Config


class TestConfigFromEnv:
    def test_loads_with_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PANDASCORE_TOKEN", "tok-abc")
        cfg = Config.from_env(base_dir=tmp_path)

        assert cfg.pandascore_token == "tok-abc"
        assert cfg.site_url == "https://site-generator.ozzy1986.com"
        assert cfg.site_name == "Киберспортивные матчи"
        assert cfg.site_timezone == "UTC"
        assert cfg.output_dir == tmp_path / "generated_site"
        assert cfg.base_dir == tmp_path

    def test_custom_values(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PANDASCORE_TOKEN", "tok-xyz")
        monkeypatch.setenv("SITE_URL", "https://example.com/")
        monkeypatch.setenv("SITE_NAME", "My eSports")
        monkeypatch.setenv("SITE_TIMEZONE", "Europe/Moscow")
        monkeypatch.setenv("OUTPUT_DIR", "out")

        cfg = Config.from_env(base_dir=tmp_path)

        assert cfg.site_url == "https://example.com"  # trailing slash stripped
        assert cfg.site_name == "My eSports"
        assert cfg.site_timezone == "Europe/Moscow"
        assert cfg.output_dir == tmp_path / "out"

    def test_missing_token_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PANDASCORE_TOKEN", raising=False)
        with pytest.raises(ValueError, match="PANDASCORE_TOKEN"):
            Config.from_env(base_dir=tmp_path)

    def test_frozen(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PANDASCORE_TOKEN", "tok")
        cfg = Config.from_env(base_dir=tmp_path)
        with pytest.raises(AttributeError):
            cfg.pandascore_token = "new"  # type: ignore[misc]
