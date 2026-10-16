from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..download_manager import download_manager
from ..utils.logger import get_logger

logger = get_logger("mobile_queue_tab")


class TaskRowWidget(QFrame):
    """One queue row — title, progress, status line, and 3 action buttons.
    A vertical card instead of the desktop's wide table, since that's the
    layout that actually fits a narrow phone screen."""

    def __init__(self, task_id: str, task: dict):
        super().__init__()
        self.task_id = task_id
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self.title_label = QLabel(task.get("title", "Unknown"))
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        self.status_label.setObjectName("mutedLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._on_pause)
        btn_row.addWidget(self.pause_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("dangerButton")
        self.remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(self.remove_btn)
        layout.addLayout(btn_row)

        self.update_from_task(task)

    def update_from_task(self, task: dict):
        self.progress_bar.setValue(int(task.get("progress", 0)))
        status = task.get("status", "")
        self.status_label.setText(
            f"{status}  ·  {task.get('downloaded', '0 B')}/{task.get('total', 'Unknown')}"
            f"  ·  {task.get('speed', '0 B/s')}"
        )
        if status == "Downloading":
            self.pause_btn.setText("Pause")
            self.pause_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
        elif status == "Paused":
            self.pause_btn.setText("Resume")
            self.pause_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
        elif status in ("Completed", "Failed", "Cancelled"):
            self.pause_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)

    def _on_pause(self):
        task = download_manager.tasks.get(self.task_id)
        if not task:
            return
        if task["status"] == "Downloading":
            download_manager.pause_task(self.task_id)
        elif task["status"] == "Paused":
            download_manager.resume_task(self.task_id)

    def _on_cancel(self):
        download_manager.cancel_task(self.task_id)

    def _on_remove(self):
        download_manager.remove_task(self.task_id)


class QueueTab(QWidget):
    def __init__(self):
        super().__init__()
        self.row_widgets: dict[str, TaskRowWidget] = {}
        self.list_items: dict[str, QListWidgetItem] = {}

        self._init_ui()

        download_manager.task_added.connect(self._on_task_added)
        download_manager.task_updated.connect(self._on_task_updated)
        download_manager.task_removed.connect(self._on_task_removed)

        for task_id, task in download_manager.tasks.items():
            self._add_row(task_id, task)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Download Queue")
        title.setObjectName("screenTitle")
        layout.addWidget(title)

        ctrl_row = QHBoxLayout()
        pause_all_btn = QPushButton("Pause All")
        pause_all_btn.clicked.connect(download_manager.pause_all)
        ctrl_row.addWidget(pause_all_btn)

        resume_all_btn = QPushButton("Resume All")
        resume_all_btn.clicked.connect(download_manager.resume_all)
        ctrl_row.addWidget(resume_all_btn)

        clear_btn = QPushButton("Clear Done")
        clear_btn.clicked.connect(download_manager.clear_completed)
        ctrl_row.addWidget(clear_btn)
        layout.addLayout(ctrl_row)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        self.empty_label = QLabel("No downloads yet.")
        self.empty_label.setObjectName("mutedLabel")
        layout.addWidget(self.empty_label)
        self._update_empty_state()

    def _update_empty_state(self):
        self.empty_label.setVisible(self.list_widget.count() == 0)

    def _add_row(self, task_id: str, task: dict):
        if task_id in self.row_widgets:
            return
        item = QListWidgetItem(self.list_widget)
        row = TaskRowWidget(task_id, task)
        item.setSizeHint(row.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, row)
        self.row_widgets[task_id] = row
        self.list_items[task_id] = item
        self._update_empty_state()

    @Slot(str)
    def _on_task_added(self, task_id: str):
        task = download_manager.tasks.get(task_id)
        if task:
            self._add_row(task_id, task)

    @Slot(str, dict)
    def _on_task_updated(self, task_id: str, data: dict):
        row = self.row_widgets.get(task_id)
        task = download_manager.tasks.get(task_id)
        if row and task:
            row.update_from_task(task)
            item = self.list_items.get(task_id)
            if item:
                item.setSizeHint(row.sizeHint())

    @Slot(str)
    def _on_task_removed(self, task_id: str):
        item = self.list_items.pop(task_id, None)
        self.row_widgets.pop(task_id, None)
        if item:
            self.list_widget.takeItem(self.list_widget.row(item))
        self._update_empty_state()
