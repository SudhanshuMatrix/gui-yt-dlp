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


def test_format_eta_float():
    assert DownloadManager._format_eta(12.5) == "00:12"
    assert DownloadManager._format_eta(3665.8) == "01:01:05"
    assert DownloadManager._format_eta(None) == "Unknown"
    assert DownloadManager._format_eta(0) == "Unknown"


def test_on_progress_ignores_stream_finished_reset(tmp_path: Path):
    """A per-stream 'finished' event (video done, audio still pending) must not
    reset the combined progress/size/speed/eta display back to zero."""
    from unittest.mock import patch

    dm = DownloadManager()
    dm.config_dir = tmp_path
    dm.queue_file = tmp_path / "queue.json"
    dm.tasks = {}

    ydl_opts = {"outtmpl": {"default": str(tmp_path)}}
    with patch("src.download_manager.DownloadWorker"):
        task_id = dm.add_task(
            url="https://www.youtube.com/watch?v=sample_progress",
            title="Sample Progress Test",
            ydl_opts=ydl_opts,
        )

    # Simulate mid-download progress (video stream, 50% of combined total)
    dm._on_progress(
        task_id,
        {
            "status": "downloading",
            "downloaded": 50_000_000,
            "total": 100_000_000,
            "speed": 1_000_000,
            "eta": 50,
            "filename": "video.f137.mp4",
        },
    )
    assert dm.tasks[task_id]["progress"] == 50.0
    assert dm.tasks[task_id]["downloaded"] != "0 B"

    # Video stream finishes; worker emits a bare status-only event
    dm._on_progress(task_id, {"status": "finished", "filename": "video.f137.mp4"})

    # Progress/size/speed must be unaffected by the stream-finished marker
    assert dm.tasks[task_id]["progress"] == 50.0
    assert dm.tasks[task_id]["downloaded"] != "0 B"
    assert dm.tasks[task_id]["total"] != "Unknown"

