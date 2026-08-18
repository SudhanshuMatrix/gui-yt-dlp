import json
import os
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from .config import config_manager
from .utils.logger import get_logger
from .utils.url_sanitizer import sanitize_url
from .yt_dlp_worker import DownloadWorker

logger = get_logger("download_manager")


class DownloadManager(QObject):
    task_added = Signal(str)
    task_updated = Signal(str, dict)
    task_removed = Signal(str)
    queue_updated = Signal()

    def __init__(self):
        super().__init__()
        self.config_dir: Path = Path.home() / ".config" / "gui-yt-dlp"
        self.queue_file: Path = self.config_dir / "queue.json"
        self.tasks: dict[str, dict[str, Any]] = OrderedDict()
        self.active_workers: dict[str, DownloadWorker] = {}
        self.terminating_workers: list[DownloadWorker] = []
        self.is_network_online = True
        self.paused_by_network: list[str] = []

        self.load_queue()

    def load_queue(self) -> None:
        """Load saved queue state from queue.json."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if self.queue_file.exists():
                with open(self.queue_file, "r", encoding="utf-8") as f:
                    saved_tasks = json.load(f)
                    for task_id, task in saved_tasks.items():
                        # Restore active/downloading tasks as Queued or Paused for resumption
                        if task.get("status") in ("Downloading", "Queued"):
                            task["status"] = "Paused"
                            task["eta"] = "Paused"
                            task["speed"] = "0 B/s"
                        self.tasks[task_id] = task
                logger.info(f"Loaded {len(self.tasks)} tasks from saved queue.")
        except Exception as e:
            logger.error(f"Error loading queue state: {e}")
            self.tasks.clear()

    def save_queue(self) -> None:
        """Save non-completed tasks to queue.json atomically."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            serializable_tasks = {}
            for task_id, task in self.tasks.items():
                # Store task without runtime logger handles or worker pointers
                task_copy = task.copy()
                task_copy.pop("video_info", None)
                serializable_tasks[task_id] = task_copy

            tmp_file = self.queue_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(serializable_tasks, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_file, self.queue_file)
            logger.debug("Queue state saved atomically.")
        except Exception as e:
            logger.error(f"Error saving queue state: {e}")

    def add_task(
        self,
        url: str,
        title: str,
        ydl_opts: dict[str, Any],
        thumbnail_local_path: str | None = None,
    ) -> str:
        """Add a new download task to the queue."""
        clean_url = sanitize_url(url)
        task_id = str(uuid.uuid4())

        download_dir = ydl_opts.get("outtmpl", {}).get(
            "default", config_manager.get("download_directory")
        )
        if not isinstance(download_dir, str):
            download_dir = config_manager.get("download_directory")

        os.makedirs(download_dir, exist_ok=True)

        task_opts = ydl_opts.copy()
        task_opts["outtmpl"] = "%(title)s.%(ext)s"
        task_opts["_download_dir"] = download_dir

        ffmpeg_path = config_manager.get("ffmpeg_path")
        if ffmpeg_path:
            task_opts["ffmpeg_location"] = ffmpeg_path

        task: dict[str, Any] = {
            "id": task_id,
            "url": clean_url,
            "title": title,
            "thumbnail_local_path": thumbnail_local_path,
            "status": "Queued",
            "progress": 0.0,
            "downloaded": "0 B",
            "total": "Unknown",
            "speed": "0 B/s",
            "eta": "Unknown",
            "filename": "",
            "error_msg": "",
            "logs": [],
            "ydl_opts": task_opts,
        }

        self.tasks[task_id] = task
        logger.info(f"Added task {task_id} for URL: {clean_url}")

        self.save_queue()
        self.task_added.emit(task_id)
        self.queue_updated.emit()

        self.process_queue()
        return task_id

    def process_queue(self):
        """Schedule and run queued downloads based on concurrency limits."""
        max_concurrency = config_manager.get("concurrency", 3)
        active_count = sum(1 for t in self.tasks.values() if t["status"] == "Downloading")

        if active_count >= max_concurrency:
            logger.debug("Max concurrency reached. Skipping scheduling.")
            return

        for task_id, task in self.tasks.items():
            if task["status"] == "Queued":
                self._start_task(task_id)
                active_count += 1
                if active_count >= max_concurrency:
                    break

    def handle_network_status(self, is_online: bool):
        """Called when network status changes."""
        self.is_network_online = is_online
        if not is_online:
            downloading_ids = [tid for tid, t in self.tasks.items() if t["status"] == "Downloading"]
            if downloading_ids:
                logger.info(
                    f"Network disconnected. Automatically pausing active tasks: {downloading_ids}"
                )
                for tid in downloading_ids:
                    if tid not in self.paused_by_network:
                        self.paused_by_network.append(tid)
                    if tid in self.tasks:
                        self.tasks[tid]["logs"].append(
                            "[App] Network disconnected. Pausing download automatically."
                        )
                        self.task_updated.emit(
                            tid,
                            {
                                "new_log": "[App] Network disconnected. Pausing download automatically."
                            },
                        )
                    self.pause_task(tid)
        else:
            if self.paused_by_network:
                logger.info(
                    f"Network restored. Automatically resuming tasks: {self.paused_by_network}"
                )
                to_resume = self.paused_by_network.copy()
                self.paused_by_network.clear()
                for tid in to_resume:
                    if tid in self.tasks and self.tasks[tid]["status"] == "Paused":
                        self.tasks[tid]["logs"].append(
                            "[App] Network restored. Resuming download automatically."
                        )
                        self.task_updated.emit(
                            tid,
                            {"new_log": "[App] Network restored. Resuming download automatically."},
                        )
                        self.resume_task(tid)

    def _start_task(self, task_id: str):
        """Start a specific download task."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        url = task["url"]
        ydl_opts = task["ydl_opts"].copy()

        # Dynamically resolve ffmpeg location at start time
        from .utils.ffmpeg_check import find_ffmpeg

        custom_path = config_manager.get("ffmpeg_path")
        ff_path, _ = find_ffmpeg(custom_path or None)
        if ff_path:
            ydl_opts["ffmpeg_location"] = os.path.dirname(ff_path)

        # Set task-specific temp folder for temporary files
        temp_dir = task.get("temp_dir")
        if not temp_dir:
            import tempfile

            temp_dir = os.path.join(tempfile.gettempdir(), "gui-yt-dlp", task_id)
            task["temp_dir"] = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

        # Get final output destination
        save_dir = ydl_opts.get("_download_dir") or config_manager.get("download_directory")

        ydl_opts["paths"] = {
            "home": save_dir,
            "temp": temp_dir,
            "thumbnail": temp_dir,
            "subtitle": temp_dir,
        }

        worker = DownloadWorker(url, ydl_opts)
        self.active_workers[task_id] = worker

        task["status"] = "Downloading"
        self.task_updated.emit(task_id, {"status": "Downloading"})

        worker.progress_updated.connect(lambda data, tid=task_id: self._on_progress(tid, data))
        worker.log_received.connect(lambda log, tid=task_id: self._on_log(tid, log))
        worker.download_finished.connect(
            lambda filename, tid=task_id: self._on_finished(tid, filename)
        )
        worker.error.connect(lambda err, tid=task_id: self._on_error(tid, err))
        worker.format_unavailable.connect(
            lambda info, tid=task_id: self._on_format_unavailable(tid, info)
        )

        logger.info(f"Starting worker for task {task_id}")
        worker.start()
        self.save_queue()

    def _handle_worker_terminated(self, worker: DownloadWorker):
        if worker in self.terminating_workers:
            self.terminating_workers.remove(worker)
            logger.info("Cleaned up terminating worker thread.")

    def pause_task(self, task_id: str):
        """Pause a running task."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        if task["status"] == "Downloading" and task_id in self.active_workers:
            worker = self.active_workers.pop(task_id)
            task["status"] = "Paused"
            task["speed"] = "0 B/s"
            task["eta"] = "Paused"

            try:
                worker.progress_updated.disconnect()
                worker.log_received.disconnect()
                worker.download_finished.disconnect()
                worker.error.disconnect()
                worker.format_unavailable.disconnect()
            except Exception:
                pass

            if worker not in self.terminating_workers:
                self.terminating_workers.append(worker)
            worker.finished.connect(lambda w=worker: self._handle_worker_terminated(w))
            worker.cancel()

            self.task_updated.emit(
                task_id,
                {
                    "status": "Paused",
                    "speed": "0 B/s",
                    "eta": "Paused",
                },
            )
            logger.info(f"Paused task {task_id}")
            self.save_queue()
            self.process_queue()

    def resume_task(self, task_id: str):
        """Resume a paused task."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        if task["status"] in ("Paused", "Failed", "Cancelled"):
            task["status"] = "Queued"
            task["eta"] = "Queued"
            self.task_updated.emit(
                task_id,
                {
                    "status": "Queued",
                    "eta": "Queued",
                },
            )
            logger.info(f"Resumed task {task_id} to Queued")
            self.save_queue()
            self.process_queue()

    def cancel_task(self, task_id: str):
        """Cancel a running or queued task."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        status = task["status"]

        if status == "Downloading" and task_id in self.active_workers:
            worker = self.active_workers.pop(task_id)
            try:
                worker.progress_updated.disconnect()
                worker.log_received.disconnect()
                worker.download_finished.disconnect()
                worker.error.disconnect()
                worker.format_unavailable.disconnect()
            except Exception:
                pass
            if worker not in self.terminating_workers:
                self.terminating_workers.append(worker)
            worker.finished.connect(lambda w=worker: self._handle_worker_terminated(w))
            worker.cancel()

        task["status"] = "Cancelled"
        task["speed"] = "0 B/s"
        task["eta"] = "Cancelled"

        self._cleanup_temp_files(task_id)

        self.task_updated.emit(
            task_id,
            {
                "status": "Cancelled",
                "speed": "0 B/s",
                "eta": "Cancelled",
            },
        )
        logger.info(f"Cancelled task {task_id}")
        self.save_queue()
        self.process_queue()

    def remove_task(self, task_id: str):
        """Remove a task from the list and clean up its resources."""
        if task_id not in self.tasks:
            return

        self.cancel_task(task_id)
        del self.tasks[task_id]
        logger.info(f"Removed task {task_id}")
        self.save_queue()
        self.task_removed.emit(task_id)
        self.queue_updated.emit()

    def pause_all(self):
        """Pause all currently downloading tasks."""
        downloading_ids = [tid for tid, t in self.tasks.items() if t["status"] == "Downloading"]
        for tid in downloading_ids:
            self.pause_task(tid)

    def resume_all(self):
        """Resume all paused tasks."""
        paused_ids = [
            tid for tid, t in self.tasks.items() if t["status"] in ("Paused", "Failed", "Cancelled")
        ]
        for tid in paused_ids:
            self.resume_task(tid)

    def clear_completed(self):
        """Remove all completed, cancelled, or failed tasks from the list."""
        to_remove = [
            tid
            for tid, t in self.tasks.items()
            if t["status"] in ("Completed", "Cancelled", "Failed")
        ]
        for tid in to_remove:
            self.remove_task(tid)

    def _cleanup_worker(self, task_id: str):
        """Clean up the worker reference for a task."""
        if task_id in self.active_workers:
            del self.active_workers[task_id]

    def _cleanup_temp_files(self, task_id: str):
        """Clean up the temporary download directory and pre-downloaded thumbnail."""
        if task_id not in self.tasks:
            return
        task = self.tasks[task_id]

        # 1. Clean up temp_dir
        temp_dir = task.get("temp_dir")
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temp directory {temp_dir}: {e}")

        # 2. Clean up pre-downloaded thumbnail in gui-yt-dlp/thumbnails
        thumb_path = task.get("thumbnail_local_path")
        if thumb_path and os.path.exists(thumb_path):
            try:
                if "library_thumbnails" not in thumb_path:
                    os.remove(thumb_path)
                    logger.info(f"Cleaned up pre-downloaded thumbnail: {thumb_path}")
            except Exception as e:
                logger.error(f"Error deleting thumbnail {thumb_path}: {e}")

    def _on_progress(self, task_id: str, data: dict[str, Any]):
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        total = data.get("total", 0)
        downloaded = data.get("downloaded", 0)
        progress = 0.0
        if total > 0:
            progress = (downloaded / total) * 100

        downloaded_str = self._format_size(downloaded)
        total_str = self._format_size(total) if total > 0 else "Unknown"
        speed_str = self._format_speed(data.get("speed", 0))
        eta_str = self._format_eta(data.get("eta", 0))
        filename = data.get("filename", "")

        task.update(
            {
                "progress": progress,
                "downloaded": downloaded_str,
                "total": total_str,
                "speed": speed_str,
                "eta": eta_str,
                "filename": filename,
            }
        )

        self.task_updated.emit(
            task_id,
            {
                "progress": progress,
                "downloaded": downloaded_str,
                "total": total_str,
                "speed": speed_str,
                "eta": eta_str,
                "filename": filename,
            },
        )

    def _on_log(self, task_id: str, log_line: str):
        if task_id not in self.tasks:
            return
        task = self.tasks[task_id]
        task["logs"].append(log_line)
        self.task_updated.emit(task_id, {"new_log": log_line})

    def _on_finished(self, task_id: str, filename: str):
        if task_id not in self.tasks:
            return
        task = self.tasks[task_id]
        if task["status"] == "Cancelled":
            return
        task["status"] = "Completed"
        task["progress"] = 100.0
        task["speed"] = "0 B/s"
        task["eta"] = "Finished"
        task["filename"] = os.path.basename(filename)

        self.task_updated.emit(
            task_id,
            {
                "status": "Completed",
                "progress": 100.0,
                "speed": "0 B/s",
                "eta": "Finished",
                "filename": os.path.basename(filename),
            },
        )

        self._cleanup_worker(task_id)
        self._cleanup_temp_files(task_id)
        self.save_queue()
        logger.info(f"Task {task_id} completed. Saved as: {filename}")
        self.process_queue()

    def _on_error(self, task_id: str, error_msg: str):
        if task_id not in self.tasks:
            return
        task = self.tasks[task_id]

        if task["status"] == "Cancelled":
            return

        is_network_err = any(
            kw in error_msg.lower()
            for kw in [
                "connection refused",
                "connection timed out",
                "name or service not known",
                "temporary failure in name resolution",
                "network is unreachable",
                "timed out",
                "http error 503",
                "http error 502",
                "http error 504",
                "http error 408",
                "ssl: certificate_verify_failed",
                "urllib.error.urlerror",
                "gai error",
            ]
        )

        if is_network_err or not self.is_network_online:
            logger.info(f"Task {task_id} encountered a network error. Pausing it: {error_msg}")
            task["logs"].append(
                f"[App] Network error: {error_msg}. Pausing download automatically."
            )
            self.task_updated.emit(
                task_id,
                {"new_log": f"[App] Network error: {error_msg}. Pausing download automatically."},
            )

            if task_id not in self.paused_by_network:
                self.paused_by_network.append(task_id)

            task["status"] = "Paused"
            task["speed"] = "0 B/s"
            task["eta"] = "Paused"

            self.task_updated.emit(
                task_id,
                {
                    "status": "Paused",
                    "speed": "0 B/s",
                    "eta": "Paused",
                },
            )

            self._cleanup_worker(task_id)
            self.save_queue()
            self.process_queue()
            return

        task["status"] = "Failed"
        task["error_msg"] = error_msg
        task["speed"] = "0 B/s"
        task["eta"] = "Failed"

        self.task_updated.emit(
            task_id,
            {
                "status": "Failed",
                "error_msg": error_msg,
                "speed": "0 B/s",
                "eta": "Failed",
            },
        )

        self._cleanup_worker(task_id)
        self._cleanup_temp_files(task_id)
        self.save_queue()
        logger.error(f"Task {task_id} failed: {error_msg}")

    def _on_format_unavailable(self, task_id: str, info: dict):
        if task_id not in self.tasks:
            return
        task = self.tasks[task_id]
        task["status"] = "Format Unavailable"
        task["speed"] = "0 B/s"
        task["eta"] = "Format Unavailable"
        task["video_info"] = info

        self.task_updated.emit(
            task_id,
            {
                "status": "Format Unavailable",
                "speed": "0 B/s",
                "eta": "Format Unavailable",
            },
        )

        self._cleanup_worker(task_id)
        self.save_queue()
        logger.warning(f"Task {task_id} format unavailable.")
        self.process_queue()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        import math

        i = math.floor(math.log(size_bytes, 1024))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    @staticmethod
    def _format_speed(speed_bytes_sec: float | None) -> str:
        if not speed_bytes_sec or speed_bytes_sec <= 0:
            return "0 B/s"
        size_name = ("B/s", "KB/s", "MB/s", "GB/s")
        import math

        i = math.floor(math.log(speed_bytes_sec, 1024))
        p = math.pow(1024, i)
        s = round(speed_bytes_sec / p, 2)
        return f"{s} {size_name[i]}"

    @staticmethod
    def _format_eta(eta_seconds: int | None) -> str:
        if eta_seconds is None or eta_seconds <= 0:
            return "Unknown"
        minutes, seconds = divmod(eta_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


# Global manager instance
download_manager = DownloadManager()
