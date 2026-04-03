from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template

from site_generator.config import Config
from site_generator.pandascore_client import PandaScoreError
from site_generator.services.generator import generate_site

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)

_BASE_DIR = Path(__file__).resolve().parent


@app.route("/")
def index() -> str:
    return render_template("admin/index.html")


@app.route("/generate", methods=["POST"])
def generate() -> tuple:
    try:
        config = Config.from_env(base_dir=_BASE_DIR)
        result = generate_site(config)
        return jsonify({
            "success": True,
            "message": f"Site generated in {config.output_dir}",
            "counts": result,
        }), 200
    except PandaScoreError as exc:
        return jsonify({"success": False, "message": str(exc)}), 502
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        logging.getLogger(__name__).exception("Generation failed")
        return jsonify({"success": False, "message": f"Unexpected error: {exc}"}), 500


@app.route("/open-output", methods=["POST"])
def open_output() -> tuple:
    try:
        config = Config.from_env(base_dir=_BASE_DIR)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    if not config.output_dir.exists():
        return jsonify({"success": False, "message": "Output directory does not exist yet."}), 404

    if sys.platform == "win32":
        os.startfile(str(config.output_dir))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(config.output_dir)])
    else:
        subprocess.Popen(["xdg-open", str(config.output_dir)])

    return jsonify({"success": True}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
