from pathlib import Path

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


def test_download_manager_temp_paths_and_ffmpeg(tmp_path: Path):
    import os
    from unittest.mock import patch

    dm = DownloadManager()
    dm.config_dir = tmp_path
    dm.queue_file = tmp_path / "queue.json"
    dm.tasks = {}

    ydl_opts = {"outtmpl": {"default": str(tmp_path)}}

    mock_ffmpeg_file = os.path.join(
        "mock_ffmpeg", "bin", "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    )
    expected_ffmpeg_dir = os.path.dirname(mock_ffmpeg_file)

    # We mock find_ffmpeg to return a dummy path
    with (
        patch("src.utils.ffmpeg_check.find_ffmpeg", return_value=(mock_ffmpeg_file, None)),
        patch("src.download_manager.DownloadWorker") as MockWorker,
    ):

        task_id = dm.add_task(
            url="https://www.youtube.com/watch?v=sample_temp_test",
            title="Sample Temp Test",
            ydl_opts=ydl_opts,
        )

        # Make sure the task started
        assert task_id in dm.tasks

        # Verify ydl_opts passed to DownloadWorker
        MockWorker.assert_called_once()
        called_args, _ = MockWorker.call_args
        called_opts = called_args[1]

        # Check ffmpeg_location is set to directory of mocked ffmpeg path
        assert called_opts.get("ffmpeg_location") == expected_ffmpeg_dir

        # Check paths configuration
        assert "paths" in called_opts
        assert called_opts["paths"]["home"] == str(tmp_path)
        assert "temp" in called_opts["paths"]
        assert task_id in called_opts["paths"]["temp"]
