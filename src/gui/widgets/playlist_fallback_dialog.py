from typing import Any, Dict, List, Optional, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QFrame, QComboBox, QPushButton, QCheckBox,
)


class VideoFallbackRow(QFrame):
    """One row per incompatible video: skip toggle + video/audio format selectors."""

    def __init__(self, entry: Dict[str, Any], index: int, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("cardFrame")
        self.setFrameShape(QFrame.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # ── Header row ──────────────────────────────────────────────
        header = QHBoxLayout()

        self.include_check = QCheckBox()
        self.include_check.setChecked(True)
        self.include_check.setToolTip("Uncheck to skip this video")
        header.addWidget(self.include_check)

        num_label = QLabel(f"#{index}")
        num_label.setStyleSheet("color: #71717a; font-size: 11px; min-width: 28px;")
        header.addWidget(num_label)

        title = entry.get("title") or entry.get("id") or f"Video {index}"
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: 600; color: #e4e4e7;")
        header.addWidget(title_label, 1)
        layout.addLayout(header)

        # ── Format selectors ────────────────────────────────────────
        fmt_row = QHBoxLayout()

        fmt_row.addWidget(QLabel("Video:"))
        self.video_combo = QComboBox()
        avail_video: list = entry.get("available_video_formats", [])
        if avail_video:
            for f in avail_video:
                self.video_combo.addItem(f["desc"], f["id"])
        else:
            self.video_combo.addItem("Best Available (auto)", "bestvideo")
        fmt_row.addWidget(self.video_combo, 1)

        fmt_row.addWidget(QLabel("Audio:"))
        self.audio_combo = QComboBox()
        avail_audio: list = entry.get("available_audio_formats", [])
        if avail_audio:
            for f in avail_audio:
                self.audio_combo.addItem(f["desc"], f["id"])
        else:
            self.audio_combo.addItem("Best Available (auto)", "bestaudio")
        fmt_row.addWidget(self.audio_combo, 1)

        layout.addLayout(fmt_row)

        self.include_check.stateChanged.connect(self._on_toggle)

    # ── Slots ────────────────────────────────────────────────────────
    def _on_toggle(self, state: int):
        enabled = state == Qt.Checked.value
        self.video_combo.setEnabled(enabled)
        self.audio_combo.setEnabled(enabled)

    # ── Public ───────────────────────────────────────────────────────
    def get_selection(self) -> Optional[Tuple[str, str, str, str]]:
        """Return (url, video_fmt_id, audio_fmt_id, title) or None if skipped."""
        if not self.include_check.isChecked():
            return None
        url = (
            self.entry.get("resolved_url")
            or self.entry.get("url")
            or self.entry.get("webpage_url")
            or f"https://www.youtube.com/watch?v={self.entry.get('id', '')}"
        )
        vid_id: str = self.video_combo.currentData() or "bestvideo"
        aud_id: str = self.audio_combo.currentData() or "bestaudio"
        title: str = self.entry.get("title") or f"Video {self.entry.get('id', '')}"
        return (url, vid_id, aud_id, title)


class PlaylistFallbackDialog(QDialog):
    """
    Shown after a pre-check finds videos that lack the selected format.
    Lets the user choose a per-video fallback format before queuing downloads.

    Emits downloads_queued(list) where each item is (url, vid_fmt_id, aud_fmt_id, title).
    """

    downloads_queued = Signal(list)

    def __init__(
        self,
        incompatible_entries: List[Dict[str, Any]],
        original_format_desc: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Format Unavailable — Select Fallback")
        self.setMinimumSize(720, 520)
        self.resize(820, 600)
        self.rows: List[VideoFallbackRow] = []
        self._build_ui(incompatible_entries, original_format_desc)

    # ── Private ──────────────────────────────────────────────────────
    def _build_ui(self, entries: list, original_format_desc: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Warning banner
        banner = QLabel(
            f"<b>⚠  {len(entries)} video(s)</b> don't have the selected format: "
            f"<span style='color:#a78bfa'>{original_format_desc}</span><br>"
            "Choose a fallback format for each or uncheck to skip it."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "color: #fbbf24; background: #1c1917; padding: 10px 14px;"
            "border: 1px solid #44403c; border-radius: 6px; font-size: 13px;"
        )
        root.addWidget(banner)

        # Scrollable list of rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(6)

        for entry in entries:
            row = VideoFallbackRow(entry, entry.get("playlist_index", 0))
            self.rows.append(row)
            content_layout.addWidget(row)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

        # ── Bottom buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()

        sel_all = QPushButton("Select All")
        sel_all.clicked.connect(lambda: [r.include_check.setChecked(True) for r in self.rows])
        btn_row.addWidget(sel_all)

        skip_all = QPushButton("Skip All")
        skip_all.clicked.connect(lambda: [r.include_check.setChecked(False) for r in self.rows])
        btn_row.addWidget(skip_all)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Queue Downloads")
        ok_btn.setObjectName("primaryButton")
        ok_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(ok_btn)

        root.addLayout(btn_row)

    def _on_confirm(self):
        selections = [r.get_selection() for r in self.rows]
        selections = [s for s in selections if s is not None]
        self.downloads_queued.emit(selections)
        self.accept()
