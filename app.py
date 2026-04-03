from __future__ import annotations

import io
import logging
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
