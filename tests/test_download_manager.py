from pathlib import Path
from unittest.mock import MagicMock
from src.download_manager import DownloadManager


def test_download_manager_add_task(tmp_path: Path):
    dm = DownloadManager()
    dm.config_dir = tmp_path
    dm.queue_file = tmp_path / "queue.json"
    dm.tasks = {}

    ydl_opts = {"outtmpl": {"default": str(tmp_path)}}
    task_id = dm.add_task(
        url="https://www.youtube.com/watch?v=sample123",
        title="Sample Video",
        ydl_opts=ydl_opts,
    )

    assert task_id in dm.tasks
    task = dm.tasks[task_id]
    assert task["url"] == "https://www.youtube.com/watch?v=sample123"
    assert task["title"] == "Sample Video"
    assert task["status"] in ("Queued", "Downloading")

    # Cancel task
    dm.cancel_task(task_id)
    assert dm.tasks[task_id]["status"] == "Cancelled"

    # Clear completed/cancelled
    dm.clear_completed()
    assert task_id not in dm.tasks
