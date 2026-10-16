from src.yt_dlp_worker import DownloadWorker


def test_download_worker_progress_hook_multistream():
    worker = DownloadWorker("https://www.youtube.com/watch?v=test", {})

    emitted_progress = []
    worker.progress_updated.connect(lambda data: emitted_progress.append(data))

    # Phase 1: Video stream downloading (100 MB total, downloaded 40 MB)
    d1 = {
        "status": "downloading",
        "filename": "video.f137.mp4",
        "total_bytes": 100_000_000,
        "downloaded_bytes": 40_000_000,
        "speed": 1_000_000,
        "eta": 60,
        "info_dict": {
            "requested_formats": [
                {"format_id": "137", "filesize": 100_000_000},
                {"format_id": "140", "filesize": 10_000_000},
            ]
        },
    }
    worker._progress_hook(d1)

    assert len(emitted_progress) == 1
    assert emitted_progress[0]["downloaded"] == 40_000_000
    assert emitted_progress[0]["total"] == 110_000_000

    # Phase 2: Video stream finishes
    d2 = {
        "status": "finished",
        "filename": "video.f137.mp4",
        "total_bytes": 100_000_000,
        "downloaded_bytes": 100_000_000,
    }
    worker._progress_hook(d2)

    # Phase 3: Audio stream downloading (10 MB total, downloaded 5 MB)
    d3 = {
        "status": "downloading",
        "filename": "video.f140.m4a",
        "total_bytes": 10_000_000,
        "downloaded_bytes": 5_000_000,
        "speed": 500_000,
        "eta": 10,
        "info_dict": {
            "requested_formats": [
                {"format_id": "137", "filesize": 100_000_000},
                {"format_id": "140", "filesize": 10_000_000},
            ]
        },
    }
    worker._progress_hook(d3)

    assert len(emitted_progress) == 3
    # Check that audio stream progress adds completed video size (100 MB + 5 MB = 105 MB out of 110 MB)
    assert emitted_progress[2]["downloaded"] == 105_000_000
    assert emitted_progress[2]["total"] == 110_000_000


def test_download_worker_progress_hook_partial_requested_formats_size():
    worker = DownloadWorker("https://www.youtube.com/watch?v=test", {})

    emitted_progress = []
    worker.progress_updated.connect(lambda data: emitted_progress.append(data))

    # Audio stream downloading first (89 MB total, downloaded 40 MB). Video format has filesize: None
    d1 = {
        "status": "downloading",
        "filename": "audio.f251.webm",
        "total_bytes": 89_000_000,
        "downloaded_bytes": 40_000_000,
        "speed": 1_000_000,
        "eta": 60,
        "info_dict": {
            "requested_formats": [
                {"format_id": "399", "filesize": None},
                {"format_id": "251", "filesize": 89_000_000},
            ]
        },
    }
    worker._progress_hook(d1)

    assert emitted_progress[0]["downloaded"] == 40_000_000
    assert emitted_progress[0]["total"] == 89_000_000

    # Audio stream finishes
    d2 = {
        "status": "finished",
        "filename": "audio.f251.webm",
        "total_bytes": 89_000_000,
        "downloaded_bytes": 89_000_000,
    }
    worker._progress_hook(d2)

    # Video stream starts downloading (213 MB total, downloaded 109 MB -> total downloaded 89 + 109 = 198 MB)
    d3 = {
        "status": "downloading",
        "filename": "video.f399.mp4",
        "total_bytes": 213_000_000,
        "downloaded_bytes": 109_000_000,
        "speed": 5_000_000,
        "eta": 20,
        "info_dict": {
            "requested_formats": [
                {"format_id": "399", "filesize": 213_000_000},
                {"format_id": "251", "filesize": 89_000_000},
            ]
        },
    }
    worker._progress_hook(d3)

    last_prog = emitted_progress[-1]
    assert last_prog["downloaded"] == 198_000_000
    assert last_prog["total"] == 302_000_000  # Total size expanded to 89 MB + 213 MB = 302 MB!
    assert last_prog["downloaded"] <= last_prog["total"]

