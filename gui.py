#!/usr/bin/env python3
"""Graphical UI for the YouTube downloader."""

from __future__ import annotations

import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from downloader import (
    DEFAULT_PLAYLIST_URL,
    download_as_video,
    download_playlist_as_mp3,
)

APP_TITLE = "YouTube Downloader"
APP_MIN_SIZE = (640, 560)


class DownloaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(*APP_MIN_SIZE)
        self.geometry("720x620")

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._process_holder: list[subprocess.Popen] = []
        self._downloading = False

        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="YouTube Downloader", font=("", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(root, text="Download playlists or single videos as MP3, MP4, or video only").pack(
            anchor=tk.W, pady=(0, 8)
        )

        # URL
        url_frame = ttk.LabelFrame(root, text="URL (playlist or single video)", padding=8)
        url_frame.pack(fill=tk.X, **pad)

        self.url_var = tk.StringVar(value=DEFAULT_PLAYLIST_URL)
        ttk.Entry(url_frame, textvariable=self.url_var).pack(fill=tk.X, side=tk.LEFT, expand=True)
        ttk.Button(url_frame, text="Reset default", command=self._reset_url).pack(
            side=tk.RIGHT, padx=(8, 0)
        )

        # Scope: playlist vs single
        scope_frame = ttk.LabelFrame(root, text="Scope", padding=8)
        scope_frame.pack(fill=tk.X, **pad)

        self.scope_var = tk.StringVar(value="playlist")
        ttk.Radiobutton(scope_frame, text="Whole playlist", variable=self.scope_var, value="playlist").pack(
            side=tk.LEFT, padx=(0, 16)
        )
        ttk.Radiobutton(scope_frame, text="Single video only", variable=self.scope_var, value="single").pack(
            side=tk.LEFT
        )

        # Download type
        type_frame = ttk.LabelFrame(root, text="Download type", padding=8)
        type_frame.pack(fill=tk.X, **pad)

        self.type_var = tk.StringVar(value="audio")
        ttk.Radiobutton(
            type_frame, text="Audio only (MP3)", variable=self.type_var,
            value="audio", command=self._on_type_change,
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            type_frame, text="Video + audio (MP4)", variable=self.type_var,
            value="video", command=self._on_type_change,
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            type_frame, text="Video only (no audio, MP4)", variable=self.type_var,
            value="video_only", command=self._on_type_change,
        ).pack(anchor=tk.W)

        # Quality
        qual_frame = ttk.LabelFrame(root, text="Quality", padding=8)
        qual_frame.pack(fill=tk.X, **pad)

        self.audio_qual_var = tk.StringVar(value="320K")
        self.video_qual_var = tk.StringVar(value="1080p")

        self.audio_qual = ttk.Combobox(
            qual_frame, textvariable=self.audio_qual_var,
            values=["128K", "192K", "256K", "320K"], state="readonly", width=12,
        )
        self.video_qual = ttk.Combobox(
            qual_frame, textvariable=self.video_qual_var,
            values=["480p", "720p", "1080p", "1440p", "2160p"], state="readonly", width=12,
        )

        self.qual_label = ttk.Label(qual_frame, text="MP3 bitrate:")
        self.qual_label.pack(side=tk.LEFT)
        self.audio_qual.pack(side=tk.LEFT, padx=(8, 0))

        # Output folder
        out_frame = ttk.LabelFrame(root, text="Save to folder", padding=8)
        out_frame.pack(fill=tk.X, **pad)

        self.out_var = tk.StringVar(value=str(Path.cwd() / "downloads"))
        ttk.Entry(out_frame, textvariable=self.out_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_frame, text="Browse…", command=self._browse_output).pack(
            side=tk.RIGHT, padx=(8, 0)
        )

        # Actions
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill=tk.X, **pad)

        self.download_btn = ttk.Button(btn_frame, text="Start download", command=self._start_download)
        self.download_btn.pack(side=tk.LEFT)

        self.cancel_btn = ttk.Button(
            btn_frame, text="Cancel", command=self._cancel_download, state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.progress = ttk.Progressbar(btn_frame, mode="indeterminate")
        self.progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(16, 0))

        # Log
        log_frame = ttk.LabelFrame(root, text="Progress log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=14, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status_var).pack(anchor=tk.W, pady=(4, 0))

        self._on_type_change()

    def _reset_url(self) -> None:
        self.url_var.set(DEFAULT_PLAYLIST_URL)

    def _on_type_change(self) -> None:
        is_audio = self.type_var.get() == "audio"
        self.audio_qual.pack_forget()
        self.video_qual.pack_forget()

        if is_audio:
            self.qual_label.config(text="MP3 bitrate:")
            self.audio_qual.pack(side=tk.LEFT, padx=(8, 0))
            cur = self.out_var.get()
            if "video" in cur.lower():
                self.out_var.set(str(Path.cwd() / "downloads"))
        else:
            self.qual_label.config(text="Max video height:")
            self.video_qual.pack(side=tk.LEFT, padx=(8, 0))
            cur = self.out_var.get()
            if Path(cur).name == "downloads":
                self.out_var.set(str(Path.cwd() / "video_downloads"))

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder", initialdir=self.out_var.get())
        if path:
            self.out_var.set(path)

    def _append_log(self, line: str) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _log_callback(self, message: str) -> None:
        self._log_queue.put(message)

    def _poll_log_queue(self) -> None:
        try:
            while True:
                self._append_log(self._log_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def _set_busy(self, busy: bool) -> None:
        self._downloading = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.download_btn.config(state=state)
        self.cancel_btn.config(state=tk.NORMAL if busy else tk.DISABLED)
        if busy:
            self.progress.start(12)
            self.status_var.set("Downloading…")
        else:
            self.progress.stop()
            self.status_var.set("Ready")

    def _start_download(self) -> None:
        if self._downloading:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_TITLE, "Please enter a URL.")
            return

        out = self.out_var.get().strip()
        if not out:
            messagebox.showwarning(APP_TITLE, "Please choose an output folder.")
            return

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        dtype = self.type_var.get()
        single = self.scope_var.get() == "single"
        quality = self.audio_qual_var.get() if dtype == "audio" else self.video_qual_var.get()

        self._set_busy(True)

        def worker() -> None:
            try:
                if dtype == "audio":
                    ok = download_playlist_as_mp3(
                        url, output_dir=out, quality=quality, single=single,
                        log=self._log_callback, process_holder=self._process_holder,
                    )
                else:
                    ok = download_as_video(
                        url, output_dir=out, quality=quality, single=single,
                        video_only=(dtype == "video_only"),
                        log=self._log_callback, process_holder=self._process_holder,
                    )
                msg = "Download finished successfully." if ok else "Finished with errors."
            except Exception as exc:
                ok = False
                msg = str(exc)
                self._log_callback(f"Error: {exc}")

            self.after(0, lambda: self._on_download_done(ok, msg))

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _on_download_done(self, success: bool, message: str) -> None:
        self._set_busy(False)
        self.status_var.set("Done" if success else "Finished with errors")
        if success:
            messagebox.showinfo(APP_TITLE, message)
        else:
            messagebox.showwarning(APP_TITLE, message)

    def _cancel_download(self) -> None:
        if not self._downloading:
            return
        for proc in list(self._process_holder):
            try:
                proc.terminate()
            except OSError:
                pass
        self._log_callback("\nDownload cancelled.")
        self.status_var.set("Cancelled")


def main() -> None:
    app = DownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
