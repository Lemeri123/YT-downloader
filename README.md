# YouTube Playlist Downloader

Download every track from a YouTube playlist as **MP3** or **MP4**, similar to y2mate but for full playlists.

## Requirements

- Python 3 (`python3` on Ubuntu — there is no `python` command by default)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/) (for audio/video conversion)

### One-time setup (Ubuntu/Debian)

**Option A — easiest (recommended):**

```bash
sudo apt update
sudo apt install ffmpeg yt-dlp
```

**Option B — project virtual environment** (if you prefer not to use apt for yt-dlp):

```bash
sudo apt install ffmpeg python3.12-venv
cd ~/Documents/y2mate
./setup.sh
```

## Web UI (recommended)

Works in any browser; no extra GUI packages needed.

```bash
cd ~/Documents/y2mate
python3 web_app.py
```

Or use the launcher script:

```bash
chmod +x run.sh
./run.sh
```

Your browser opens automatically. Paste a playlist URL, choose MP3 or MP4, set quality and output folder, then click **Start download**.

## Desktop UI (optional)

Requires `python3-tk` (`sudo apt install python3-tk` on Ubuntu):

```bash
python3 gui.py
```

## Command-line (original script)

```bash
python3 downloader.py
```

## Project layout

| File | Purpose |
|------|---------|
| `web_app.py` | Browser UI (recommended) |
| `gui.py` | Desktop UI (needs `python3-tk`) |
| `downloader.py` | Download logic + CLI |
| `requirements.txt` | Python dependencies |
# YT-downloader
