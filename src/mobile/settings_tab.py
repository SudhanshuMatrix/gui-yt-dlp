from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..config import config_manager
from ..constants import APP_NAME, APP_VERSION


class SettingsTab(QWidget):
    def __init__(self, main_window: QWidget):
        super().__init__()
        self.main_window = main_window
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("screenTitle")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(14)

        self.dir_label = QLabel(config_manager.get("download_directory"))
        self.dir_label.setWordWrap(True)
        self.dir_label.setObjectName("mutedLabel")
        form.addRow("Download folder:", self.dir_label)

        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 5)
        self.concurrency_spin.setValue(config_manager.get("concurrency", 2))
        self.concurrency_spin.valueChanged.connect(
            lambda v: config_manager.set("concurrency", v)
        )
        form.addRow("Concurrent downloads:", self.concurrency_spin)

        self.auto_update_check = QCheckBox("Auto-check yt-dlp updates on startup")
        self.auto_update_check.setChecked(config_manager.get("auto_update", True))
        self.auto_update_check.stateChanged.connect(
            lambda s: config_manager.set("auto_update", s == Qt.Checked.value)
        )
        form.addRow(self.auto_update_check)

        layout.addWidget(card)

        note = QLabel(
            "FFmpeg isn't bundled in this Android build yet, so video+audio "
            "merging and MP3 conversion aren't available: \"Best Quality\" downloads "
            "a single pre-combined stream when YouTube offers one, and \"Audio Only\" "
            "saves the native audio file (m4a/webm/opus) without converting it."
        )
        note.setObjectName("mutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)

        version_label = QLabel(f"{APP_NAME} v{APP_VERSION} (Android)")
        version_label.setObjectName("mutedLabel")
        layout.addWidget(version_label)

        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
