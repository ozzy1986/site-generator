from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, send_from_directory

from site_generator.config import Config
from site_generator.pandascore_client import PandaScoreError
from site_generator.services.generator import generate_site

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)

_BASE_DIR = Path(__file__).resolve().parent


def _can_open_output_directory() -> bool:
    """Return whether the current environment can open a local folder UI."""
    if sys.platform == "win32":
        return hasattr(os, "startfile")
    if sys.platform == "darwin":
        return shutil.which("open") is not None
    return (
        shutil.which("xdg-open") is not None
        and bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    )


@app.route("/")
@app.route("/admin")
def index() -> str:
    return render_template(
        "admin/index.html",
        can_open_output=_can_open_output_directory(),
    )


@app.route("/admin/static/<path:filename>")
def admin_static(filename: str):
    return send_from_directory(app.static_folder or "", filename)


@app.route("/generate", methods=["POST"])
def generate() -> tuple:
    try:
        config = Config.from_env(base_dir=_BASE_DIR)
        result = generate_site(config)
        return jsonify({
            "success": True,
            "message": "Сайт успешно собран и обновлён.",
            "counts": result,
        }), 200
    except PandaScoreError as exc:
        return jsonify({"success": False, "message": f"Ошибка PandaScore: {exc}"}), 502
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        logging.getLogger(__name__).exception("Generation failed")
        return jsonify({"success": False, "message": f"Непредвиденная ошибка: {exc}"}), 500


@app.route("/open-output", methods=["POST"])
def open_output() -> tuple:
    try:
        config = Config.from_env(base_dir=_BASE_DIR)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    if not config.output_dir.exists():
        return jsonify({"success": False, "message": "Каталог сборки пока не создан."}), 404

    if not _can_open_output_directory():
        return jsonify({
            "success": False,
            "message": "Открытие каталога доступно только в локальной графической среде.",
        }), 501

    if sys.platform == "win32":
        os.startfile(str(config.output_dir))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(config.output_dir)])
    else:
        subprocess.Popen(["xdg-open", str(config.output_dir)])

    return jsonify({"success": True}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
