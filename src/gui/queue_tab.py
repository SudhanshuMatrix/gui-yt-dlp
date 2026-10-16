import os
from typing import Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QSplitter,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    CardWidget,
    FluentIcon,
    MessageBox,
    ProgressBar,
    PushButton,
    SearchLineEdit,
    StrongBodyLabel,
    TableWidget,
    TextEdit,
    ToolButton,
    TransparentToolButton,
)

from ..config import config_manager
from ..download_manager import download_manager
from ..utils.logger import get_logger
from ..utils.open_path import open_path
from .widgets.format_selection_dialog import SingleVideoFormatSelectionDialog

logger = get_logger("queue_tab")


class QueueTab(QWidget):
    def __init__(self):
        super().__init__()
        # Keep track of task ID to table row index mapping
        self.task_row_map: dict[str, int] = {}
        # Keep track of widgets created per task
        self.task_widgets: dict[str, dict[str, Any]] = {}
        # Currently selected task ID for logs
        self.active_log_task_id: str | None = None

        self._init_ui()

        # Connect download manager signals
        download_manager.task_added.connect(self._on_task_added)
        download_manager.task_updated.connect(self._on_task_updated)
        download_manager.task_removed.connect(self._on_task_removed)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Splitter to separate Queue Table (top) and Log Console (bottom)
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # 1. Top Panel: Queue Table & Controls
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        # Controls Row
        ctrl_layout = QHBoxLayout()
        self.pause_all_btn = PushButton(FluentIcon.PAUSE, "Pause All")
        self.pause_all_btn.clicked.connect(self._pause_all)
        ctrl_layout.addWidget(self.pause_all_btn)

        self.resume_all_btn = PushButton(FluentIcon.PLAY, "Resume All")
        self.resume_all_btn.clicked.connect(self._resume_all)
        ctrl_layout.addWidget(self.resume_all_btn)

        self.clear_completed_btn = PushButton(FluentIcon.DELETE, "Clear Completed")
        self.clear_completed_btn.clicked.connect(self._clear_completed)
        ctrl_layout.addWidget(self.clear_completed_btn)

        ctrl_layout.addStretch()

        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("Filter by title or status...")
        self.search_input.setFixedWidth(260)
        self.search_input.textChanged.connect(self._apply_filter)
        self.search_input.searchSignal.connect(self._apply_filter)
        self.search_input.clearSignal.connect(lambda: self._apply_filter(""))
        ctrl_layout.addWidget(self.search_input)

        top_layout.addLayout(ctrl_layout)

        # Queue Table
        self.table = TableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Thumbnail", "Title", "Size", "Progress", "Speed", "ETA", "Actions"]
        )
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)

        # Set selection behavior
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        # Header configuration
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Thumbnail
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Size
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Progress
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Speed
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # ETA
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Actions

        self.table.setColumnWidth(0, 90)  # Thumbnail width
        self.table.setColumnWidth(3, 140)  # Progress width
        self.table.setColumnWidth(6, 230)  # Actions width
        self.table.verticalHeader().setDefaultSectionSize(60)  # Height of rows
        self.table.verticalHeader().setVisible(False)  # Hide vertical row numbers header

        top_layout.addWidget(self.table)
        splitter.addWidget(top_container)

        # 2. Bottom Panel: Log Console
        self.log_container = CardWidget()
        log_layout = QVBoxLayout(self.log_container)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(8)

        log_header_layout = QHBoxLayout()
        self.log_title_label = StrongBodyLabel("Download Console Logs (Select an item to view)")
        log_header_layout.addWidget(self.log_title_label)

        log_header_layout.addStretch()
        self.clear_log_btn = PushButton(FluentIcon.BROOM, "Clear Console")
        self.clear_log_btn.clicked.connect(self._clear_console)
        log_header_layout.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_header_layout)

        self.console = TextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.console)

        splitter.addWidget(self.log_container)

        # Set split ratios: 65% table, 35% logs
        splitter.setSizes([450, 200])
        layout.addWidget(splitter)

    def _rebuild_table_mapping(self):
        """Re-map task IDs to row indices because deleting shifts rows."""
        self.task_row_map.clear()
        for row in range(self.table.rowCount()):
            # Grab task_id stored in the Title item's UserRole
            title_item = self.table.item(row, 1)
            if title_item:
                task_id = title_item.data(Qt.UserRole)
                if task_id:
                    self.task_row_map[task_id] = row

    @Slot(str)
    def _on_task_added(self, task_id: str):
        task = download_manager.tasks.get(task_id)
        if not task:
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.task_row_map[task_id] = row

        # Column 0: Thumbnail
        thumb_label = CaptionLabel()
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setFixedSize(80, 45)
        self._set_thumbnail_on_label(thumb_label, task.get("thumbnail_local_path"))
        self.table.setCellWidget(row, 0, thumb_label)

        # Column 1: Title (holds task_id in UserRole)
        title_item = QTableWidgetItem(task["title"])
        title_item.setData(Qt.UserRole, task_id)
        title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
        title_item.setToolTip(task["url"])
        title_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.setItem(row, 1, title_item)

        # Column 2: Size
        size_item = QTableWidgetItem("Unknown")
        size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)
        size_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.table.setItem(row, 2, size_item)

        # Column 3: Progress
        progress_bar = ProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        self.table.setCellWidget(row, 3, progress_bar)

        # Column 4: Speed
        speed_item = QTableWidgetItem("0 B/s")
        speed_item.setFlags(speed_item.flags() & ~Qt.ItemIsEditable)
        speed_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.table.setItem(row, 4, speed_item)

        # Column 5: ETA
        eta_item = QTableWidgetItem("Queued")
        eta_item.setFlags(eta_item.flags() & ~Qt.ItemIsEditable)
        eta_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.table.setItem(row, 5, eta_item)

        # Column 6: Actions Widget (Pause/Resume, Cancel, Remove)
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(4, 4, 4, 4)
        actions_layout.setSpacing(4)

        pause_btn = ToolButton(FluentIcon.PAUSE)
        pause_btn.setToolTip("Pause")
        pause_btn.clicked.connect(lambda _, tid=task_id: self._pause_task(tid))

        cancel_btn = ToolButton(FluentIcon.CANCEL)
        cancel_btn.setToolTip("Cancel")
        cancel_btn.clicked.connect(lambda _, tid=task_id: self._cancel_task(tid))

        remove_btn = TransparentToolButton(FluentIcon.DELETE)
        remove_btn.setToolTip("Remove")
        remove_btn.clicked.connect(lambda _, tid=task_id: self._remove_task(tid))

        open_folder_btn = TransparentToolButton(FluentIcon.FOLDER)
        open_folder_btn.setToolTip("Open containing folder")
        open_folder_btn.clicked.connect(lambda _, tid=task_id: self._open_folder(tid))

        actions_layout.addWidget(pause_btn)
        actions_layout.addWidget(cancel_btn)
        actions_layout.addWidget(open_folder_btn)
        actions_layout.addWidget(remove_btn)
        actions_layout.addStretch()
        self.table.setCellWidget(row, 6, actions_widget)

        # Keep track of widgets for quick updates
        self.task_widgets[task_id] = {
            "thumb_label": thumb_label,
            "size_item": size_item,
            "progress_bar": progress_bar,
            "speed_item": speed_item,
            "eta_item": eta_item,
            "pause_btn": pause_btn,
            "cancel_btn": cancel_btn,
            "remove_btn": remove_btn,
            "open_folder_btn": open_folder_btn,
        }

        self._apply_filter(self.search_input.text())

    @Slot(str, dict)
    def _on_task_updated(self, task_id: str, data: dict):
        if task_id not in self.task_widgets or task_id not in self.task_row_map:
            return

        widgets = self.task_widgets[task_id]

        # Update progress bar
        if "progress" in data:
            widgets["progress_bar"].setValue(int(data["progress"]))

        # Update sizes
        if "downloaded" in data or "total" in data:
            task = download_manager.tasks.get(task_id, {})
            widgets["size_item"].setText(
                f"{task.get('downloaded', '0 B')} / {task.get('total', 'Unknown')}"
            )

        # Update speed
        if "speed" in data:
            widgets["speed_item"].setText(data["speed"])

        # Update ETA / status string
        if "eta" in data:
            widgets["eta_item"].setText(data["eta"])

        # Update status-driven actions
        if "status" in data:
            status = data["status"]
            widgets["eta_item"].setText(
                status if status != "Downloading" else data.get("eta", "Downloading")
            )

            # Update action buttons state
            if status == "Downloading":
                widgets["pause_btn"].setIcon(FluentIcon.PAUSE)
                widgets["pause_btn"].setToolTip("Pause")
                widgets["pause_btn"].setEnabled(True)
                widgets["cancel_btn"].setEnabled(True)
            elif status == "Paused":
                widgets["pause_btn"].setIcon(FluentIcon.PLAY)
                widgets["pause_btn"].setToolTip("Resume")
                widgets["pause_btn"].setEnabled(True)
                widgets["cancel_btn"].setEnabled(True)
            elif status == "Format Unavailable":
                widgets["pause_btn"].setIcon(FluentIcon.SETTING)
                widgets["pause_btn"].setToolTip("Select Format")
                widgets["pause_btn"].setEnabled(True)
                widgets["cancel_btn"].setEnabled(True)
            elif status in ("Completed", "Failed", "Cancelled"):
                widgets["pause_btn"].setIcon(FluentIcon.PAUSE)
                widgets["pause_btn"].setEnabled(False)
                widgets["cancel_btn"].setEnabled(False)
                widgets["speed_item"].setText("0 B/s")
                if status == "Completed":
                    widgets["progress_bar"].setValue(100)

        # Append new log line to console if this task is currently viewed
        if "new_log" in data and self.active_log_task_id == task_id:
            self.console.append(data["new_log"])

    @Slot(str)
    def _on_task_removed(self, task_id: str):
        if task_id not in self.task_row_map:
            return

        row = self.task_row_map[task_id]
        self.table.removeRow(row)

        # Clean cache
        if task_id in self.task_widgets:
            del self.task_widgets[task_id]

        if self.active_log_task_id == task_id:
            self.active_log_task_id = None
            self.console.clear()
            self.log_title_label.setText("Download Console Logs (Select an item to view)")

        self._rebuild_table_mapping()

    def _apply_filter(self, text: str = ""):
        """Hide rows whose title/status don't match the search box text."""
        text = text.strip().lower()
        for task_id, row in self.task_row_map.items():
            if row >= self.table.rowCount():
                continue
            if not text:
                self.table.setRowHidden(row, False)
                continue
            task = download_manager.tasks.get(task_id, {})
            haystack = f"{task.get('title', '')} {task.get('status', '')}".lower()
            self.table.setRowHidden(row, text not in haystack)

    def _open_folder(self, task_id: str):
        task = download_manager.tasks.get(task_id)
        if not task:
            return
        download_dir = task.get("ydl_opts", {}).get("_download_dir") or config_manager.get(
            "download_directory"
        )
        if not open_path(download_dir):
            logger.warning(f"Could not open download folder for task {task_id}: {download_dir}")

    def _set_thumbnail_on_label(self, label: CaptionLabel, path: str | None):
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            label.setPixmap(
                pixmap.scaled(
                    label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            label.setText("No Preview")

    # Task Operations
    def _pause_task(self, task_id: str):
        task = download_manager.tasks.get(task_id)
        if not task:
            return

        if task["status"] == "Downloading":
            download_manager.pause_task(task_id)
        elif task["status"] == "Paused":
            download_manager.resume_task(task_id)
        elif task["status"] == "Format Unavailable":
            self._select_format_for_task(task_id)

    def _select_format_for_task(self, task_id: str):
        task = download_manager.tasks.get(task_id)
        if not task or not task.get("video_info"):
            return

        info = task["video_info"]
        from ..yt_dlp_worker import _build_format_lists

        video_formats, audio_formats = _build_format_lists(info.get("formats", []))

        dlg = SingleVideoFormatSelectionDialog(task["title"], video_formats, audio_formats, self)
        if dlg.exec():
            video_fmt, audio_fmt = dlg.get_selected_formats()

            # Update formats in task options
            ydl_opts = task["ydl_opts"]

            # Check if selected video format is combined
            selected_is_combined = False
            for f in info.get("formats", []):
                if f.get("format_id") == video_fmt:
                    vcodec = str(f.get("vcodec") or "none").lower()
                    acodec = str(f.get("acodec") or "none").lower()
                    selected_is_combined = vcodec != "none" and acodec != "none"
                    break

            if video_fmt and audio_fmt and not selected_is_combined:
                ydl_opts["format"] = f"{video_fmt}+{audio_fmt}/best"
            elif video_fmt:
                ydl_opts["format"] = video_fmt
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/best"

            # Remove the check flag since the user has now selected a valid/available format
            ydl_opts["_check_format_availability"] = False
            ydl_opts.pop("_requested_video_format", None)
            ydl_opts.pop("_requested_audio_format", None)

            # Put the task back in the queue
            task["status"] = "Queued"
            task["eta"] = "Queued"
            task["error_msg"] = ""

            download_manager.task_updated.emit(task_id, {"status": "Queued", "eta": "Queued"})
            logger.info(f"Updated format for task {task_id} and re-queued.")
            download_manager.process_queue()

    def _cancel_task(self, task_id: str):
        box = MessageBox(
            "Cancel Download", "Are you sure you want to cancel this download?", self
        )
        if box.exec():
            download_manager.cancel_task(task_id)

    def _remove_task(self, task_id: str):
        task = download_manager.tasks.get(task_id)
        if not task:
            return

        # If download is active, confirm first
        if task["status"] == "Downloading":
            box = MessageBox(
                "Remove Task",
                "This download is in progress. Are you sure you want to abort and remove it?",
                self,
            )
            if not box.exec():
                return

        download_manager.remove_task(task_id)

    # Queue-wide Operations
    def _pause_all(self):
        download_manager.pause_all()

    def _resume_all(self):
        download_manager.resume_all()

    def _clear_completed(self):
        download_manager.clear_completed()

    # Log console handling
    def _on_selection_changed(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return

        row = selected_ranges[0].topRow()
        title_item = self.table.item(row, 1)
        if not title_item:
            return

        task_id = title_item.data(Qt.UserRole)
        if task_id == self.active_log_task_id:
            return

        self.active_log_task_id = task_id
        task = download_manager.tasks.get(task_id)

        if task:
            self.log_title_label.setText(f"Download Console Logs: {task['title']}")
            self.console.clear()
            self.console.setPlainText("\n".join(task["logs"]))
            # Scroll to bottom
            self.console.moveCursor(self.console.textCursor().End)
        else:
            self.active_log_task_id = None
            self.console.clear()
            self.log_title_label.setText("Download Console Logs (Select an item to view)")

    def _clear_console(self):
        if self.active_log_task_id and self.active_log_task_id in download_manager.tasks:
            download_manager.tasks[self.active_log_task_id]["logs"] = []
        self.console.clear()
