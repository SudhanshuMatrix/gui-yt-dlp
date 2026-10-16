from typing import Any

from PySide6.QtWidgets import QHBoxLayout
from qfluentwidgets import BodyLabel, ComboBox, MessageBoxBase, SubtitleLabel


class SingleVideoFormatSelectionDialog(MessageBoxBase):
    def __init__(
        self,
        title: str,
        video_formats: list[dict[str, Any]],
        audio_formats: list[dict[str, Any]],
        parent=None,
    ):
        super().__init__(parent)
        self.video_fmt_id = ""
        self.audio_fmt_id = ""

        self._build_ui(title, video_formats, audio_formats)

        self.widget.setMinimumWidth(460)
        self.yesButton.setText("Apply and Queue")

    def _build_ui(self, title: str, video_formats: list, audio_formats: list):
        header = SubtitleLabel("Format Unavailable")
        self.viewLayout.addWidget(header)

        subtitle = BodyLabel(f"for: {title}")
        subtitle.setWordWrap(True)
        self.viewLayout.addWidget(subtitle)

        self.viewLayout.addSpacing(6)

        # Video format row
        vid_layout = QHBoxLayout()
        vid_layout.addWidget(BodyLabel("Video Format:"))
        self.video_combo = ComboBox()
        if video_formats:
            for f in video_formats:
                self.video_combo.addItem(f["desc"], userData=f["id"])
        else:
            self.video_combo.addItem("Best Available (auto)", userData="bestvideo")
        vid_layout.addWidget(self.video_combo, 1)
        self.viewLayout.addLayout(vid_layout)

        # Audio format row
        aud_layout = QHBoxLayout()
        aud_layout.addWidget(BodyLabel("Audio Format:"))
        self.audio_combo = ComboBox()
        if audio_formats:
            for f in audio_formats:
                self.audio_combo.addItem(f["desc"], userData=f["id"])
        else:
            self.audio_combo.addItem("Best Available (auto)", userData="bestaudio")
        aud_layout.addWidget(self.audio_combo, 1)
        self.viewLayout.addLayout(aud_layout)

        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._on_confirm)

    def _on_confirm(self):
        self.video_fmt_id = self.video_combo.currentData() or "bestvideo"
        self.audio_fmt_id = self.audio_combo.currentData() or "bestaudio"
        self.accept()

    def get_selected_formats(self) -> tuple[str, str]:
        return self.video_fmt_id, self.audio_fmt_id
