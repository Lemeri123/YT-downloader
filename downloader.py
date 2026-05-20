#!/usr/bin/env python3
"""
YouTube Downloader — core logic (CLI + GUI).
Supports playlists and single videos as MP3, MP4 (video+audio), or video-only.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

LogCallback = Callable[[str], None]
DoneCallback = Callable[[bool, str], None]

PROJECT_ROOT = Path(__file__).resolve().parent

INSTALL_HELP = (
    "yt-dlp is not installed. On Ubuntu, run ONE of:\n"
    "  sudo apt install yt-dlp\n"
    "  sudo apt install python3.12-venv && ./setup.sh && ./run.sh"
)


def _ytdlp_command() -> list[str]:
    """Resolve yt-dlp: project venv, PATH, or python -m yt_dlp."""
    venv_bin = PROJECT_ROOT / ".venv" / "bin" / "yt-dlp"
    if venv_bin.is_file():
        return [str(venv_bin)]
    found = shutil.which("yt-dlp")
    if found:
        return [found]
    return [sys.executable, "-m", "yt_dlp"]


def _ensure_ytdlp(log: Optional[LogCallback]) -> bool:
    try:
        result = subprocess.run(
            [*_ytdlp_command(), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    _emit(log, f"\nError: {INSTALL_HELP}")
    return False


def _emit(log: Optional[LogCallback], message: str) -> None:
    if log:
        log(message)
    else:
        print(message)


def _run(
    cmd: list[str],
    output_dir: Path,
    log: Optional[LogCallback],
    process_holder: Optional[list],
) -> bool:
    """Shared subprocess runner."""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if process_holder is not None:
            process_holder.clear()
            process_holder.append(proc)

        assert proc.stdout is not None
        for line in proc.stdout:
            _emit(log, line.rstrip())

        proc.wait()
        if proc.returncode == 0:
            _emit(log, "\n" + "=" * 60)
            _emit(log, f"Download complete! Files saved to: {output_dir}")
            return True

        _emit(log, "\nDownload encountered errors. Some items may have failed.")
        return False

    except FileNotFoundError:
        _emit(log, f"\nError: {INSTALL_HELP}")
        return False
    except Exception as e:
        err = str(e)
        if "No module named 'yt_dlp'" in err or "yt-dlp" in err.lower():
            _emit(log, f"\nError: {INSTALL_HELP}")
        else:
            _emit(log, f"\nUnexpected error: {e}")
        return False


def download_playlist_as_mp3(
    url: str,
    output_dir: Path | str | None = None,
    quality: str = "320K",
    single: bool = False,
    log: Optional[LogCallback] = None,
    process_holder: Optional[list] = None,
) -> bool:
    """Download as MP3. Set single=True to download only the linked video, not the whole playlist."""
    if output_dir is None:
        output_dir = Path.cwd() / "downloads"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = "%(title)s.%(ext)s" if single else "%(playlist_index)02d - %(title)s.%(ext)s"
    output_template = str(output_dir / template)

    _emit(log, f"\nDownloading {'video' if single else 'playlist'} to: {output_dir}")
    _emit(log, f"Audio quality: {quality} MP3\n")
    _emit(log, "=" * 60)

    if not _ensure_ytdlp(log):
        return False

    cmd = [
        *_ytdlp_command(),
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", quality,
        "-o", output_template,
        "--ignore-errors",
        "--retries", "10",
    ]
    if single:
        cmd.append("--no-playlist")
    cmd.append(url)

    return _run(cmd, output_dir, log, process_holder)


def download_as_video(
    url: str,
    output_dir: Path | str | None = None,
    quality: str = "1080",
    single: bool = False,
    video_only: bool = False,
    log: Optional[LogCallback] = None,
    process_holder: Optional[list] = None,
) -> bool:
    """Download as MP4. single=True for one video; video_only=True strips audio."""
    if output_dir is None:
        output_dir = Path.cwd() / "video_downloads"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = "%(title)s.%(ext)s" if single else "%(playlist_index)02d - %(title)s.%(ext)s"
    output_template = str(output_dir / template)

    height = quality.rstrip("pP")
    label = "video only" if video_only else "video + audio"
    _emit(log, f"\nDownloading {'video' if single else 'playlist'} ({label}) to: {output_dir}")
    _emit(log, f"Video quality: up to {height}p\n")
    _emit(log, "=" * 60)

    if not _ensure_ytdlp(log):
        return False

    if video_only:
        fmt = f"bestvideo[height<={height}][ext=mp4]/bestvideo[height<={height}]"
        merge_args: list[str] = []
    else:
        fmt = f"bestvideo[height<={height}]+bestaudio/best"
        merge_args = ["--merge-output-format", "mp4"]

    cmd = [
        *_ytdlp_command(),
        "-f", fmt,
        *merge_args,
        "-o", output_template,
        "--ignore-errors",
        "--retries", "10",
    ]
    if single:
        cmd.append("--no-playlist")
    cmd.append(url)

    return _run(cmd, output_dir, log, process_holder)


def run_cli() -> None:
    """Interactive terminal UI."""
    print("\n" + "=" * 60)
    print("   YOUTUBE DOWNLOADER")
    print("   Playlists & single videos — MP3, MP4, or video only")
    print("=" * 60)

    url = input("\nURL (playlist or single video): ").strip()

    # Detect if it looks like a single video URL
    is_playlist_url = "list=" in url
    if is_playlist_url:
        single_choice = input("Download whole playlist or just this video? (playlist/single, default: playlist): ").strip().lower()
        single = single_choice == "single"
    else:
        single = True

    print("\nWhat do you want to download?")
    print("   1. Audio only (MP3)")
    print("   2. Video + Audio (MP4)")
    print("   3. Video only (no audio, MP4)")

    download_type = input("\nChoose (1/2/3, default: 1): ").strip()

    if download_type in ("2", "3"):
        quality = input("Video quality (480p, 720p, 1080p, 1440p, 2160p/4K, default: 1080p): ").strip() or "1080"
        download_as_video(url, quality=quality, single=single, video_only=(download_type == "3"))
    else:
        print("\nAudio Quality Options:")
        print("   128K - Good (smaller files)")
        print("   192K - Better (balanced)")
        print("   320K - Best (larger files)")
        quality = input("\nChoose quality (128, 192, 320, default: 320): ").strip() or "320"
        download_playlist_as_mp3(url, quality=f"{quality}K", single=single)


if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user", file=sys.stderr)
        sys.exit(1)
