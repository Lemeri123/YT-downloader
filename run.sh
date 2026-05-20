#!/usr/bin/env bash
# Launch the web UI
set -e
cd "$(dirname "$0")"

if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg is required: sudo apt install ffmpeg"
  exit 1
fi

PYTHON=python3
if [[ -x .venv/bin/python3 ]]; then
  PYTHON=.venv/bin/python3
elif ! command -v yt-dlp >/dev/null; then
  echo "yt-dlp not found."
  echo ""
  echo "Quick fix (recommended):"
  echo "  sudo apt install yt-dlp"
  echo ""
  echo "Or use a project virtual environment:"
  echo "  sudo apt install python3.12-venv"
  echo "  ./setup.sh"
  echo "  ./run.sh"
  exit 1
fi

exec "$PYTHON" web_app.py
