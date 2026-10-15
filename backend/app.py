from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import tempfile
import shutil
import os

from compressor import compress_any, decompress_huff

app = Flask(__name__)
CORS(app)

BASE = Path(tempfile.gettempdir()) / "smart_huffman_compressor"
BASE.mkdir(parents=True, exist_ok=True)

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Smart Compression API running"})

@app.post("/api/compress")
def compress():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify({"error": "Invalid filename"}), 400

    job = BASE / next(tempfile._get_candidate_names())
    job.mkdir(parents=True, exist_ok=True)
    original = job / Path(uploaded.filename).name
    uploaded.save(original)

    try:
        result = compress_any(original, job)
        result["job"] = job.name
        return jsonify(result)
    except Exception as exc:
        shutil.rmtree(job, ignore_errors=True)
        return jsonify({"error": str(exc)}), 500

@app.get("/api/download/<job>/<filename>")
def download(job, filename):
    path = BASE / Path(job).name / Path(filename).name
    if not path.exists() or not path.is_file():
        return jsonify({"error": "File not found"}), 404
    return send_file(path, as_attachment=True, download_name=path.name)

@app.post("/api/decompress/<job>/<filename>")
def decompress(job, filename):
    job_path = BASE / Path(job).name
    compressed = job_path / Path(filename).name
    if not compressed.exists():
        return jsonify({"error": "File not found"}), 404
    try:
        restored, stats = decompress_huff(compressed, job_path)
        return jsonify({
            "restored_name": restored.name,
            "download": f"/api/download/{job}/{restored.name}",
            **stats
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
