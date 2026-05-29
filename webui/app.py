import json
import os
import queue
import re
import subprocess
import threading
import uuid
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)

_default_dir = os.path.join(os.path.dirname(__file__), "..", "downloads")
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", os.path.abspath(_default_dir))

# In-memory job store: {job_id: {...}}
jobs: dict = {}
jobs_lock = threading.Lock()

# SSE subscriber queues per job: {job_id: [Queue, ...]}
subscribers: dict = {}
subscribers_lock = threading.Lock()

# Patterns for bandcamp-dl stdout (progress lines are \r-delimited, no \n)
_RE_DOWNLOADING = re.compile(r'::\s+Downloading:\s+(.+)$')
_RE_ENCODING    = re.compile(r'::\s+Encoding:\s+(.+)$')
_RE_FINISHED    = re.compile(r'::\s+Finished:\s+(.+)$')
_RE_SKIPPED     = re.compile(r'File:\s+(.+?) already exists and is complete')
_RE_FAIL        = re.compile(r'Downloading failed\.\.')


def _history_path():
    return os.path.join(DOWNLOAD_DIR, ".bandcamp-dl-history.json")


def _load_history():
    path = _history_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_history_entry(entry: dict):
    history = _load_history()
    history.insert(0, entry)
    try:
        with open(_history_path(), "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def _album_label(url: str) -> str:
    """Derive a human-readable label from a Bandcamp URL."""
    parts = url.rstrip("/").split("/")
    artist = url.split("//")[-1].split(".")[0]
    for i, p in enumerate(parts):
        if p in ("album", "track") and i + 1 < len(parts):
            return f"{artist} – {parts[i + 1].replace('-', ' ').title()}"
    return artist


def _notify(job_id: str, data: dict):
    with subscribers_lock:
        for q in subscribers.get(job_id, []):
            q.put(data)


def _upsert_track(job_id: str, name: str, status: str):
    tracks = jobs[job_id]["tracks"]
    for t in tracks:
        if t["name"] == name:
            t["status"] = status
            return
    tracks.append({"name": name, "status": status})


def _parse_token(token: str):
    """Parse a single \\r-delimited token into a structured event or None."""
    token = token.strip()
    if not token:
        return None
    m = _RE_FINISHED.search(token)
    if m:
        return {"type": "track", "name": m.group(1).strip(), "status": "done"}
    m = _RE_ENCODING.search(token)
    if m:
        return {"type": "track", "name": m.group(1).strip(), "status": "encoding"}
    m = _RE_DOWNLOADING.search(token)
    if m:
        return {"type": "track", "name": m.group(1).strip(), "status": "downloading"}
    m = _RE_SKIPPED.search(token)
    if m:
        return {"type": "track", "name": m.group(1).strip(), "status": "skipped"}
    if _RE_FAIL.search(token):
        return {"type": "track_error", "message": token}
    return None


def _run(job_id: str, url: str):
    with jobs_lock:
        jobs[job_id]["status"] = "running"
    _notify(job_id, {"type": "status", "status": "running"})

    cmd = ["bandcamp-dl", "--base-dir", DOWNLOAD_DIR, "--no-confirm", url]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        buf = b""
        while True:
            chunk = proc.stdout.read(256)
            if not chunk:
                break
            buf += chunk
            # Split on \r and \n; process complete tokens
            while True:
                r_pos = buf.find(b'\r')
                n_pos = buf.find(b'\n')
                if r_pos == -1 and n_pos == -1:
                    break
                if r_pos == -1:
                    sep = n_pos
                elif n_pos == -1:
                    sep = r_pos
                else:
                    sep = min(r_pos, n_pos)
                token = buf[:sep].decode("utf-8", errors="replace")
                buf = buf[sep + 1:]
                evt = _parse_token(token)
                if evt and evt["type"] == "track":
                    with jobs_lock:
                        _upsert_track(job_id, evt["name"], evt["status"])
                    _notify(job_id, evt)
                elif token.strip():
                    _notify(job_id, {"type": "log", "line": token.strip()})
        # flush remainder
        if buf:
            evt = _parse_token(buf.decode("utf-8", errors="replace"))
            if evt and evt["type"] == "track":
                with jobs_lock:
                    _upsert_track(job_id, evt["name"], evt["status"])
                _notify(job_id, evt)

        proc.wait()
        final = "done" if proc.returncode == 0 else "error"
    except Exception as exc:
        _notify(job_id, {"type": "track_error", "message": str(exc)})
        final = "error"

    with jobs_lock:
        jobs[job_id]["status"] = final
        snapshot_tracks = list(jobs[job_id]["tracks"])

    if final == "done":
        _save_history_entry({
            "url": url,
            "label": _album_label(url),
            "tracks": snapshot_tracks,
            "finished": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

    _notify(job_id, {"type": "status", "status": final})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/download", methods=["POST"])
def download():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    job_id = uuid.uuid4().hex[:10]
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "url": url,
            "label": _album_label(url),
            "status": "queued",
            "tracks": [],
            "created": datetime.now().strftime("%H:%M:%S"),
        }

    threading.Thread(target=_run, args=(job_id, url), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/jobs")
def list_jobs():
    with jobs_lock:
        return jsonify(list(reversed(list(jobs.values()))))


@app.route("/api/history")
def get_history():
    return jsonify(_load_history())


@app.route("/api/jobs/<job_id>/stream")
def stream_job(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            return "Not found", 404
        existing_tracks = list(jobs[job_id]["tracks"])
        current_status = jobs[job_id]["status"]

    def generate():
        # Replay existing track state immediately
        for t in existing_tracks:
            yield f"data: {json.dumps({'type': 'track', 'name': t['name'], 'status': t['status']})}\n\n"

        if current_status in ("done", "error"):
            yield f"data: {json.dumps({'type': 'status', 'status': current_status})}\n\n"
            return

        q: queue.Queue = queue.Queue()
        with subscribers_lock:
            subscribers.setdefault(job_id, []).append(q)

        try:
            while True:
                try:
                    data = q.get(timeout=25)
                    yield f"data: {json.dumps(data)}\n\n"
                    if data.get("type") == "status" and data["status"] in ("done", "error"):
                        break
                except queue.Empty:
                    yield 'data: {"type":"ping"}\n\n'
        finally:
            with subscribers_lock:
                lst = subscribers.get(job_id, [])
                if q in lst:
                    lst.remove(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, threaded=True)
