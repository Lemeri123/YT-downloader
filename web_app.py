#!/usr/bin/env python3
"""Web UI for the YouTube downloader (opens in your browser)."""

from __future__ import annotations

import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from downloader import (
    download_as_video,
    download_playlist_as_mp3,
)

HOST = "127.0.0.1"
PORT = 8765

# job_id -> {"lines": list[str], "done": bool, "ok": bool, "proc": list}
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


def _html_page() -> str:
    default_audio_out = repr(str(Path.cwd() / "downloads"))
    default_video_out = repr(str(Path.cwd() / "video_downloads"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Downloader</title>
  <style>
    :root {{
      --bg:#0f0f12;--card:#1a1a22;--border:#2e2e3a;
      --text:#e8e8ef;--muted:#9898a8;
      --accent:#ff3b5c;--accent-hover:#ff5c78;--ok:#3dd68c;
    }}
    *{{box-sizing:border-box;}}
    body{{margin:0;min-height:100vh;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;}}
    .wrap{{max-width:720px;margin:0 auto;padding:2rem 1.25rem;}}
    h1{{font-size:1.75rem;margin:0 0 .25rem;}}
    .sub{{color:var(--muted);margin-bottom:1.5rem;}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.25rem;margin-bottom:1rem;}}
    label{{display:block;font-size:.85rem;color:var(--muted);margin-bottom:.35rem;}}
    input[type="text"],select{{width:100%;padding:.65rem .75rem;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:1rem;}}
    .row{{display:flex;gap:.75rem;flex-wrap:wrap;align-items:flex-end;}}
    .row>*{{flex:1;min-width:140px;}}
    .radios{{display:flex;flex-direction:column;gap:.5rem;}}
    .radios label{{display:flex;align-items:center;gap:.5rem;color:var(--text);font-size:1rem;cursor:pointer;}}
    .inline-radios{{display:flex;gap:1.5rem;flex-wrap:wrap;}}
    .inline-radios label{{display:flex;align-items:center;gap:.4rem;color:var(--text);font-size:1rem;cursor:pointer;}}
    button{{background:var(--accent);color:#fff;border:none;padding:.75rem 1.5rem;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer;margin-right:.5rem;}}
    button:hover{{background:var(--accent-hover);}}
    button:disabled{{opacity:.5;cursor:not-allowed;}}
    button.secondary{{background:var(--border);}}
    #log{{font-family:ui-monospace,monospace;font-size:.8rem;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:.75rem;height:280px;overflow-y:auto;white-space:pre-wrap;word-break:break-word;}}
    .status{{margin-top:.75rem;color:var(--muted);font-size:.9rem;}}
    .status.ok{{color:var(--ok);}}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>YouTube Downloader</h1>
    <p class="sub">Download playlists or single videos — MP3, MP4, or video only</p>

    <form id="form" class="card">
      <label for="url">URL (playlist or single video)</label>
      <input type="text" id="url" name="url" placeholder="Paste video/playlist URL" required>

      <div style="margin-top:1rem">
        <label>Scope</label>
        <div class="inline-radios">
          <label><input type="radio" name="scope" value="playlist" checked> Whole playlist</label>
          <label><input type="radio" name="scope" value="single"> Single video only</label>
        </div>
      </div>

      <div style="margin-top:1rem">
        <label>Download type</label>
        <div class="radios">
          <label><input type="radio" name="type" value="audio" checked> Audio only (MP3)</label>
          <label><input type="radio" name="type" value="video"> Video + audio (MP4)</label>
          <label><input type="radio" name="type" value="video_only"> Video only (no audio, MP4)</label>
        </div>
      </div>

      <div class="row" style="margin-top:1rem">
        <div id="audioQualWrap">
          <label for="audioQual">MP3 bitrate</label>
          <select id="audioQual" name="audioQual">
            <option value="128K">128K — smaller files</option>
            <option value="192K">192K — balanced</option>
            <option value="256K">256K</option>
            <option value="320K" selected>320K — best</option>
          </select>
        </div>
        <div id="videoQualWrap" style="display:none">
          <label for="videoQual">Max video height</label>
          <select id="videoQual" name="videoQual">
            <option value="480p">480p</option>
            <option value="720p">720p</option>
            <option value="1080p" selected>1080p</option>
            <option value="1440p">1440p (2K)</option>
            <option value="2160p">2160p (4K)</option>
          </select>
        </div>
      </div>

      <div style="margin-top:1rem">
        <label for="out">Save to folder (full path)</label>
        <input type="text" id="out" name="out" value="" placeholder="e.g. /home/you/Music">
      </div>

      <div style="margin-top:1.25rem">
        <button type="submit" id="startBtn">Start download</button>
        <button type="button" class="secondary" id="cancelBtn" disabled>Cancel</button>
      </div>
    </form>

    <div class="card">
      <label>Progress log</label>
      <div id="log"></div>
      <p class="status" id="status">Ready</p>
    </div>
  </div>

  <script>
    const defaultAudioOut = {default_audio_out};
    const defaultVideoOut = {default_video_out};
    document.getElementById("out").value = defaultAudioOut;

    function isAudioType() {{
      return document.querySelector('input[name="type"]:checked').value === "audio";
    }}

    document.querySelectorAll('input[name="type"]').forEach(r => {{
      r.addEventListener("change", () => {{
        const audio = isAudioType();
        document.getElementById("audioQualWrap").style.display = audio ? "block" : "none";
        document.getElementById("videoQualWrap").style.display = audio ? "none" : "block";
        const out = document.getElementById("out");
        if (audio && out.value === defaultVideoOut) out.value = defaultAudioOut;
        if (!audio && out.value === defaultAudioOut) out.value = defaultVideoOut;
      }});
    }});

    let jobId = null;
    let pollTimer = null;

    function setBusy(busy) {{
      document.getElementById("startBtn").disabled = busy;
      document.getElementById("cancelBtn").disabled = !busy;
    }}

    async function pollJob(id) {{
      const res = await fetch("/api/status?id=" + encodeURIComponent(id));
      const data = await res.json();
      const logEl = document.getElementById("log");
      logEl.textContent = data.lines.join("\\n");
      logEl.scrollTop = logEl.scrollHeight;
      const st = document.getElementById("status");
      if (data.done) {{
        clearInterval(pollTimer);
        setBusy(false);
        st.textContent = data.ok ? "Download complete." : "Finished with errors.";
        st.className = "status " + (data.ok ? "ok" : "");
        jobId = null;
      }} else {{
        st.textContent = "Downloading\u2026";
        st.className = "status";
      }}
    }}

    document.getElementById("form").addEventListener("submit", async (e) => {{
      e.preventDefault();
      if (jobId) return;
      document.getElementById("log").textContent = "";
      setBusy(true);
      const fd = new FormData(e.target);
      const body = new URLSearchParams(fd);
      const audio = isAudioType();
      body.set("quality", audio ? fd.get("audioQual") : fd.get("videoQual"));
      body.delete("audioQual");
      body.delete("videoQual");

      const res = await fetch("/api/start", {{ method: "POST", body }});
      const data = await res.json();
      if (!data.job_id) {{
        document.getElementById("log").textContent = data.error || "Failed to start";
        setBusy(false);
        return;
      }}
      jobId = data.job_id;
      pollTimer = setInterval(() => pollJob(jobId), 800);
    }});

    document.getElementById("cancelBtn").addEventListener("click", async () => {{
      if (!jobId) return;
      await fetch("/api/cancel?id=" + encodeURIComponent(jobId), {{ method: "POST" }});
      document.getElementById("log").textContent += "\\nDownload cancelled.";
      clearInterval(pollTimer);
      setBusy(false);
      jobId = null;
      document.getElementById("status").textContent = "Cancelled";
    }});
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        pass

    def _send(self, code: int, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        import json
        body = json.dumps(obj).encode()
        self._send(code, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send(200, _html_page().encode())
            return
        if parsed.path == "/api/status":
            qs = parse_qs(parsed.query)
            job_id = (qs.get("id") or [""])[0]
            with _JOBS_LOCK:
                job = _JOBS.get(job_id)
            if not job:
                self._json(404, {"error": "not found"})
                return
            self._json(200, {"lines": job["lines"], "done": job["done"], "ok": job["ok"]})
            return
        self._send(404, b"Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode() if length else ""
        qs = parse_qs(raw)

        def field(name: str, default: str = "") -> str:
            return (qs.get(name) or [default])[0].strip()

        if parsed.path == "/api/cancel":
            job_id = field("id")
            with _JOBS_LOCK:
                job = _JOBS.get(job_id)
                if job and job.get("proc"):
                    try:
                        job["proc"][0].terminate()
                    except OSError:
                        pass
                    job["lines"].append("\nDownload cancelled.")
                    job["done"] = True
                    job["ok"] = False
            self._json(200, {"ok": True})
            return

        if parsed.path == "/api/start":
            url = field("url")
            if not url:
                self._json(400, {"error": "URL required"})
                return
            out = field("out") or str(Path.cwd() / "downloads")
            dtype = field("type", "audio")
            quality = field("quality", "320K")
            single = field("scope", "playlist") == "single"
            job_id = str(uuid.uuid4())

            with _JOBS_LOCK:
                _JOBS[job_id] = {"lines": [], "done": False, "ok": False, "proc": []}

            def log(msg: str) -> None:
                with _JOBS_LOCK:
                    _JOBS[job_id]["lines"].append(msg)

            def worker() -> None:
                holder: list = []
                with _JOBS_LOCK:
                    _JOBS[job_id]["proc"] = holder
                try:
                    if dtype == "audio":
                        ok = download_playlist_as_mp3(
                            url, output_dir=out, quality=quality, single=single,
                            log=log, process_holder=holder,
                        )
                    else:
                        ok = download_as_video(
                            url, output_dir=out, quality=quality, single=single,
                            video_only=(dtype == "video_only"),
                            log=log, process_holder=holder,
                        )
                except Exception as exc:
                    log(f"Error: {exc}")
                    ok = False
                with _JOBS_LOCK:
                    _JOBS[job_id]["done"] = True
                    _JOBS[job_id]["ok"] = ok

            threading.Thread(target=worker, daemon=True).start()
            self._json(200, {"job_id": job_id})
            return

        self._send(404, b"Not found")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"Open in browser: {url}")
    print("Press Ctrl+C to stop the server.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
