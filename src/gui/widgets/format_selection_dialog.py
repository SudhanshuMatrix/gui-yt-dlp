from typing import Any, Dict, List, Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QComboBox, QPushButton
)
from ..themes import get_stylesheet

class SingleVideoFormatSelectionDialog(QDialog):
    def __init__(self, title: str, video_formats: List[Dict[str, Any]], audio_formats: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Video/Audio Format")
        self.setMinimumSize(450, 220)
        self.resize(500, 250)
        
        self.video_fmt_id = ""
        self.audio_fmt_id = ""
        
        self._build_ui(title, video_formats, audio_formats)

    def _build_ui(self, title: str, video_formats: list, audio_formats: list):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title label
        title_label = QLabel(f"<b>Format Unavailable for:</b><br>{title}")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #e4e4e7; font-size: 13px;")
        layout.addWidget(title_label)

        # Container card
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # Video format row
        vid_layout = QHBoxLayout()
        vid_layout.addWidget(QLabel("Video Format:"))
        self.video_combo = QComboBox()
        if video_formats:
            for f in video_formats:
                self.video_combo.addItem(f["desc"], f["id"])
        else:
            self.video_combo.addItem("Best Available (auto)", "bestvideo")
        vid_layout.addWidget(self.video_combo, 1)
        card_layout.addLayout(vid_layout)

        # Audio format row
        aud_layout = QHBoxLayout()
        aud_layout.addWidget(QLabel("Audio Format:"))
        self.audio_combo = QComboBox()
        if audio_formats:
            for f in audio_formats:
                self.audio_combo.addItem(f["desc"], f["id"])
        else:
            self.audio_combo.addItem("Best Available (auto)", "bestaudio")
        aud_layout.addWidget(self.audio_combo, 1)
        card_layout.addLayout(aud_layout)

        layout.addWidget(card)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Apply and Queue")
        ok_btn.setObjectName("primaryButton")
        ok_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        self.video_fmt_id = self.video_combo.currentData() or "bestvideo"
        self.audio_fmt_id = self.audio_combo.currentData() or "bestaudio"
        self.accept()

    def get_selected_formats(self) -> Tuple[str, str]:
        return self.video_fmt_id, self.audio_fmt_id
