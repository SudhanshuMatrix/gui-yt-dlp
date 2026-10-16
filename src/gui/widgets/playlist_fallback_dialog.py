from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    FluentIcon,
    IconWidget,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
    SmoothScrollArea,
    isDarkTheme,
)


class VideoFallbackRow(SimpleCardWidget):
    """One row per incompatible video: skip toggle + video/audio format selectors."""

    def __init__(self, entry: dict[str, Any], index: int, parent=None):
        super().__init__(parent)
        self.entry = entry

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # ── Header row ──────────────────────────────────────────────
        header = QHBoxLayout()

        self.include_check = CheckBox()
        self.include_check.setChecked(True)
        self.include_check.setToolTip("Uncheck to skip this video")
        header.addWidget(self.include_check)

        num_label = CaptionLabel(f"#{index}")
        num_label.setStyleSheet("min-width: 28px;")
        header.addWidget(num_label)

        title = entry.get("title") or entry.get("id") or f"Video {index}"
        title_label = BodyLabel(title)
        title_label.setWordWrap(True)
        header.addWidget(title_label, 1)
        layout.addLayout(header)

        # ── Format selectors ────────────────────────────────────────
        fmt_row = QHBoxLayout()

        fmt_row.addWidget(BodyLabel("Video:"))
        self.video_combo = ComboBox()
        avail_video: list = entry.get("available_video_formats", [])
        if avail_video:
            for f in avail_video:
                self.video_combo.addItem(f["desc"], userData=f["id"])
        else:
            self.video_combo.addItem("Best Available (auto)", userData="bestvideo")
        fmt_row.addWidget(self.video_combo, 1)

        fmt_row.addWidget(BodyLabel("Audio:"))
        self.audio_combo = ComboBox()
        avail_audio: list = entry.get("available_audio_formats", [])
        if avail_audio:
            for f in avail_audio:
                self.audio_combo.addItem(f["desc"], userData=f["id"])
        else:
            self.audio_combo.addItem("Best Available (auto)", userData="bestaudio")
        fmt_row.addWidget(self.audio_combo, 1)

        layout.addLayout(fmt_row)

        self.include_check.stateChanged.connect(self._on_toggle)

    # ── Slots ────────────────────────────────────────────────────────
    def _on_toggle(self, state: int):
        enabled = state == Qt.Checked.value
        self.video_combo.setEnabled(enabled)
        self.audio_combo.setEnabled(enabled)

    # ── Public ───────────────────────────────────────────────────────
    def get_selection(self) -> tuple[str, str, str, str] | None:
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
        incompatible_entries: list[dict[str, Any]],
        original_format_desc: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Format Unavailable — Select Fallback")
        self.setMinimumSize(720, 520)
        self.resize(820, 600)
        # qfluentwidgets components repaint themselves per isDarkTheme(), but a
        # plain QDialog's own background doesn't — set it explicitly so this
        # window doesn't pop up with the OS's default light background.
        self.setStyleSheet(
            f"QDialog {{ background-color: {'#272727' if isDarkTheme() else '#f3f3f3'}; }}"
        )
        self.rows: list[VideoFallbackRow] = []
        self._build_ui(incompatible_entries, original_format_desc)

    # ── Private ──────────────────────────────────────────────────────
    def _build_ui(self, entries: list, original_format_desc: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Warning banner
        banner = SimpleCardWidget()
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(14, 12, 14, 12)
        banner_layout.setSpacing(10)
        warn_icon = IconWidget(FluentIcon.INFO)
        warn_icon.setFixedSize(20, 20)
        banner_layout.addWidget(warn_icon)
        banner_text = BodyLabel(
            f"{len(entries)} video(s) don't have the selected format: "
            f"{original_format_desc}. Choose a fallback format for each, "
            "or uncheck to skip it."
        )
        banner_text.setWordWrap(True)
        banner_layout.addWidget(banner_text, 1)
        root.addWidget(banner)

        # Scrollable list of rows
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(8)

        for entry in entries:
            row = VideoFallbackRow(entry, entry.get("playlist_index", 0))
            self.rows.append(row)
            content_layout.addWidget(row)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

        # ── Bottom buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()

        sel_all = PushButton("Select All")
        sel_all.clicked.connect(lambda: [r.include_check.setChecked(True) for r in self.rows])
        btn_row.addWidget(sel_all)

        skip_all = PushButton("Skip All")
        skip_all.clicked.connect(lambda: [r.include_check.setChecked(False) for r in self.rows])
        btn_row.addWidget(skip_all)

        btn_row.addStretch()

        cancel_btn = PushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = PrimaryPushButton(FluentIcon.CLOUD_DOWNLOAD, "Queue Downloads")
        ok_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(ok_btn)

        root.addLayout(btn_row)

    def _on_confirm(self):
        selections = [r.get_selection() for r in self.rows]
        selections = [s for s in selections if s is not None]
        self.downloads_queued.emit(selections)
        self.accept()
