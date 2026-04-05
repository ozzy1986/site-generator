from __future__ import annotations

import io
import logging
import os
import subprocess
import zipfile
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, send_file, send_from_directory

from site_generator.config import Config
from site_generator.pandascore_client import PandaScoreError
from site_generator.services.generator import generate_site

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)

_BASE_DIR = Path(__file__).resolve().parent

_SYSTEMD_SERVICE_UNIT = "site-generator.service"
_JOURNAL_TAIL_LINES = 10


def _ru_seconds_word(n: int) -> str:
    """Return секунда/секунды/секунд for integer *n* (Russian plural rules)."""
    n = abs(n) % 100
    if 11 <= n <= 14:
        return "секунд"
    r = n % 10
    if r == 1:
        return "секунду"
    if r in (2, 3, 4):
        return "секунды"
    return "секунд"


def _build_success_message(duration_seconds: float) -> str:
    """User-facing line with measured wall time (matches admin report style)."""
    s = max(0.0, float(duration_seconds))
    if abs(s - round(s)) < 0.001:
        n = int(round(s))
        return f"Сайт успешно собран и обновлён за {n} {_ru_seconds_word(n)}."
    num_str = f"{s:.1f}".replace(".", ",")
    return f"Сайт успешно собран и обновлён за {num_str} секунды."


def _read_service_journal_tail() -> tuple[bool, str, list[str]]:
    """Return (ok, error_message, lines) from journalctl for the Flask service unit."""
    if os.name == "nt":
        return False, "Журнал systemd доступен только на сервере Linux.", []

    try:
        proc = subprocess.run(
            [
                "journalctl",
                "-u",
                _SYSTEMD_SERVICE_UNIT,
                "-n",
                str(_JOURNAL_TAIL_LINES),
                "--no-pager",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except FileNotFoundError:
        return False, "Команда journalctl не найдена.", []
    except subprocess.TimeoutExpired:
        return False, "Таймаут при чтении журнала.", []

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        msg = err or out or f"journalctl завершился с кодом {proc.returncode}"
        return False, msg, []

    lines = out.splitlines() if out else []
    return True, "", lines


def _zip_output_directory(output_dir: Path) -> io.BytesIO:
    """Pack the generated static site into a ZIP archive in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in output_dir.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(output_dir)
                zf.write(path, arcname)
    buf.seek(0)
    return buf


@app.route("/")
@app.route("/admin")
def index() -> str:
    return render_template("admin/index.html")


@app.route("/admin/static/<path:filename>")
def admin_static(filename: str):
    return send_from_directory(app.static_folder or "", filename)


@app.route("/generate", methods=["POST"])
def generate() -> tuple:
    try:
        config = Config.from_env(base_dir=_BASE_DIR)
        result = generate_site(config)
        duration = float(result.pop("duration_seconds", 0.0))
        return jsonify({
            "success": True,
            "message": _build_success_message(duration),
            "counts": result,
        }), 200
    except PandaScoreError as exc:
        return jsonify({"success": False, "message": f"Ошибка PandaScore: {exc}"}), 502
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        logging.getLogger(__name__).exception("Generation failed")
        return jsonify({"success": False, "message": f"Непредвиденная ошибка: {exc}"}), 500


@app.route("/service-log", methods=["GET"])
def service_log():
    """Last lines of systemd journal for site-generator.service (JSON)."""
    ok, err, lines = _read_service_journal_tail()
    if ok:
        return jsonify({"success": True, "lines": lines})
    return jsonify({"success": False, "message": err}), 200


@app.route("/download-site", methods=["GET"])
def download_site():
    """Serve a ZIP of the generated public static site."""
    try:
        config = Config.from_env(base_dir=_BASE_DIR)
    except ValueError as exc:
        abort(400, str(exc))

    if not config.output_dir.is_dir():
        abort(404, "Каталог сборки пока не создан.")

    buf = _zip_output_directory(config.output_dir)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="generated_site.zip",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
