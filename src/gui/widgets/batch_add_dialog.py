from PySide6.QtWidgets import QHBoxLayout
from qfluentwidgets import BodyLabel, ComboBox, MessageBoxBase, SubtitleLabel, TextEdit


class BatchAddDialog(MessageBoxBase):
    """Paste many URLs (one per line) and queue them all at once.

    Deliberately offers only format choices that don't require per-video
    analysis (Best Quality / Audio Only) — a specific format ID picked for
    one video usually doesn't exist on another, so "Video Only"/"Custom
    Formats" stay a single-URL, analyze-first flow.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget.setMinimumWidth(520)
        self.yesButton.setText("Add All to Queue")

        self.viewLayout.addWidget(SubtitleLabel("Batch Add URLs"))
        self.viewLayout.addWidget(
            BodyLabel("Paste one URL per line. Each is queued with the quality below.")
        )

        self.url_text = TextEdit()
        self.url_text.setPlaceholderText(
            "https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...\n..."
        )
        self.url_text.setMinimumHeight(180)
        self.viewLayout.addWidget(self.url_text)

        quality_row = QHBoxLayout()
        quality_row.addWidget(BodyLabel("Quality:"))
        self.quality_combo = ComboBox()
        self.quality_combo.addItem("Best Quality (Video + Audio)", userData="best")
        self.quality_combo.addItem("Audio Only (MP3)", userData="audio")
        quality_row.addWidget(self.quality_combo, 1)
        self.viewLayout.addLayout(quality_row)

    def get_urls(self) -> list[str]:
        raw = self.url_text.toPlainText()
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def get_quality_mode(self) -> str:
        return self.quality_combo.currentData() or "best"
