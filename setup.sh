#!/usr/bin/env bash
# Install yt-dlp into a project virtual environment (Ubuntu-friendly)
set -e
cd "$(dirname "$0")"

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "python3-venv is required. Run:"
  echo "  sudo apt install python3.12-venv"
  echo ""
  echo "Or install yt-dlp system-wide instead:"
  echo "  sudo apt install yt-dlp"
  exit 1
fi

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
echo ""
echo "Setup complete. Run: ./run.sh"
