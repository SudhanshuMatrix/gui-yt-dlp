from typing import Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..config import config_manager
from ..download_manager import download_manager
from ..utils.logger import get_logger
from ..utils.url_sanitizer import sanitize_url
from ..yt_dlp_worker import VideoAnalyzer

logger = get_logger("mobile_downloader_tab")

# "Audio Only" intentionally skips MP3 conversion (FFmpegExtractAudio) since
# no FFmpeg is bundled for Android in this build — it downloads the best
# native audio stream as-is (m4a/webm/opus) instead of silently failing the
# postprocessor step. See src/mobile/settings_tab.py for the full note.
MODE_BEST = 0
MODE_AUDIO = 1


class DownloaderTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self.current_analysis: dict[str, Any] = {}
        self.analyzer: VideoAnalyzer | None = None
        self.active_download_task_id: str | None = None

        self._init_ui()
        download_manager.task_updated.connect(self._on_task_updated)

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel("Download Video")
        title.setObjectName("screenTitle")
        layout.addWidget(title)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a video or playlist URL...")
        self.url_input.setMinimumHeight(44)
        url_row.addWidget(self.url_input, 1)
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.clicked.connect(self._paste_clipboard)
        url_row.addWidget(self.paste_btn)
        layout.addLayout(url_row)

        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setObjectName("primaryButton")
        self.analyze_btn.clicked.connect(self._start_analysis)
        layout.addWidget(self.analyze_btn)

        self.status_label = QLabel("Enter a URL above to get started.")
        self.status_label.setObjectName("mutedLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # ── Result card ────────────────────────────────────────────
        self.result_frame = QFrame()
        self.result_frame.setObjectName("card")
        self.result_frame.setVisible(False)
        result_layout = QVBoxLayout(self.result_frame)
        result_layout.setContentsMargins(14, 14, 14, 14)
        result_layout.setSpacing(10)

        self.title_label = QLabel()
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(True)
        result_layout.addWidget(self.title_label)

        self.meta_label = QLabel()
        self.meta_label.setObjectName("mutedLabel")
        result_layout.addWidget(self.meta_label)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Quality:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Best Quality (Video + Audio)")
        self.mode_combo.addItem("Audio Only (native format)")
        mode_row.addWidget(self.mode_combo, 1)
        result_layout.addLayout(mode_row)

        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.clicked.connect(self._download_now)
        result_layout.addWidget(self.download_btn)

        layout.addWidget(self.result_frame)

        # ── Progress card ──────────────────────────────────────────
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("card")
        self.progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(14, 14, 14, 14)
        progress_layout.setSpacing(10)

        self.progress_title = QLabel("Downloading...")
        self.progress_title.setObjectName("cardTitle")
        progress_layout.addWidget(self.progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        self.progress_detail = QLabel("")
        self.progress_detail.setObjectName("mutedLabel")
        self.progress_detail.setWordWrap(True)
        progress_layout.addWidget(self.progress_detail)

        prog_btn_row = QHBoxLayout()
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._toggle_pause)
        prog_btn_row.addWidget(self.pause_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.clicked.connect(self._cancel)
        prog_btn_row.addWidget(self.cancel_btn)
        progress_layout.addLayout(prog_btn_row)

        self.done_btn = QPushButton("Done")
        self.done_btn.setObjectName("primaryButton")
        self.done_btn.setVisible(False)
        self.done_btn.clicked.connect(self._reset)
        progress_layout.addWidget(self.done_btn)

        layout.addWidget(self.progress_frame)
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @Slot()
    def _paste_clipboard(self):
        self.url_input.setText(QGuiApplication.clipboard().text())

    @Slot()
    def _start_analysis(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a URL first.")
            return

        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyzing...")
        self.status_label.setText("Fetching video info...")
        self.status_label.setVisible(True)
        self.result_frame.setVisible(False)

        if self.analyzer:
            self.analyzer.cancel()
            try:
                self.analyzer.analysis_completed.disconnect()
                self.analyzer.analysis_failed.disconnect()
            except RuntimeError:
                pass

        self.analyzer = VideoAnalyzer(sanitize_url(url))
        self.analyzer.analysis_completed.connect(self._on_analysis_success)
        self.analyzer.analysis_failed.connect(self._on_analysis_failed)
        self.analyzer.start()

    @Slot(dict)
    def _on_analysis_success(self, info: dict):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        self.status_label.setVisible(False)
        self.current_analysis = info

        self.title_label.setText(info.get("title", "Unknown Title"))

        is_playlist = info.get("_type") == "playlist" or "entries" in info
        if is_playlist:
            entries = info.get("entries") or []
            if not isinstance(entries, list):
                try:
                    entries = list(entries)
                except Exception:
                    entries = []
            info["_entries_list"] = entries
            self.meta_label.setText(f"Playlist · {len(entries)} video(s)")
            self.download_btn.setText(f"Download All ({len(entries)})")
        else:
            duration = info.get("duration", 0) or 0
            mins, secs = divmod(int(duration), 60)
            self.meta_label.setText(f"{info.get('uploader', 'Unknown')} · {mins}:{secs:02d}")
            self.download_btn.setText("Download")

        self.result_frame.setVisible(True)

    @Slot(str)
    def _on_analysis_failed(self, error: str):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyze")
        self.status_label.setVisible(True)
        self.status_label.setText("Analysis failed.")
        QMessageBox.critical(self, "Analysis Failed", str(error))

    def _is_playlist(self) -> bool:
        return (
            self.current_analysis.get("_type") == "playlist" or "entries" in self.current_analysis
        )

    def _build_opts(self) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": config_manager.get("socket_timeout", 20),
        }
        if self.mode_combo.currentIndex() == MODE_AUDIO:
            opts["format"] = "bestaudio/best"
        else:
            # "best" first: a single already-combined stream needs no FFmpeg
            # merge step, which isn't available on this Android build yet.
            opts["format"] = "best/bestvideo+bestaudio"
        opts["outtmpl"] = {"default": config_manager.get("download_directory")}
        return opts

    @Slot()
    def _download_now(self):
        if not self.current_analysis:
            return
        base_opts = self._build_opts()

        if self._is_playlist():
            entries = self.current_analysis.get("_entries_list") or []
            base_opts["noplaylist"] = True
            queued = 0
            for idx, entry in enumerate(entries):
                vid_id = entry.get("id", "")
                url = (
                    entry.get("url")
                    or entry.get("webpage_url")
                    or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
                )
                if not url:
                    continue
                title = entry.get("title") or f"Video {idx + 1}"
                download_manager.add_task(url, title, base_opts.copy(), None)
                queued += 1

            QMessageBox.information(self, "Queued", f"Added {queued} video(s) to the queue.")
            self._reset()
            self.main_window.switch_tab(1)
            return

        url = self.current_analysis.get("webpage_url") or self.url_input.text().strip()
        title = self.current_analysis.get("title", "Unknown Title")
        task_id = download_manager.add_task(url, title, base_opts, None)
        self.active_download_task_id = task_id

        self.result_frame.setVisible(False)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_title.setText("Downloading…")
        self.progress_detail.setText("")
        self.pause_btn.setText("Pause")
        self.pause_btn.setVisible(True)
        self.pause_btn.setEnabled(True)
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.done_btn.setVisible(False)

    @Slot(str, dict)
    def _on_task_updated(self, task_id: str, data: dict):
        if task_id != self.active_download_task_id:
            return

        if "progress" in data:
            self.progress_bar.setValue(int(data["progress"]))

        if any(k in data for k in ("downloaded", "total", "speed", "eta")):
            task = download_manager.tasks.get(task_id, {})
            self.progress_detail.setText(
                f"{task.get('downloaded', '0 B')} / {task.get('total', 'Unknown')}  ·  "
                f"{task.get('speed', '0 B/s')}  ·  ETA {task.get('eta', 'Unknown')}"
            )

        if "status" in data:
            status = data["status"]
            self.progress_title.setText(status)
            if status == "Paused":
                self.pause_btn.setText("Resume")
            elif status == "Downloading":
                self.pause_btn.setText("Pause")
            elif status in ("Completed", "Failed", "Cancelled"):
                self.pause_btn.setVisible(False)
                self.cancel_btn.setVisible(False)
                self.done_btn.setVisible(True)
                if status == "Completed":
                    self.progress_title.setText("Download Completed!")

    @Slot()
    def _toggle_pause(self):
        if not self.active_download_task_id:
            return
        task = download_manager.tasks.get(self.active_download_task_id)
        if not task:
            return
        if task["status"] == "Downloading":
            download_manager.pause_task(self.active_download_task_id)
        elif task["status"] == "Paused":
            download_manager.resume_task(self.active_download_task_id)

    @Slot()
    def _cancel(self):
        if self.active_download_task_id:
            download_manager.cancel_task(self.active_download_task_id)

    @Slot()
    def _reset(self):
        self.active_download_task_id = None
        self.url_input.clear()
        self.current_analysis = {}
        self.result_frame.setVisible(False)
        self.progress_frame.setVisible(False)
        self.status_label.setVisible(True)
        self.status_label.setText("Enter a URL above to get started.")
