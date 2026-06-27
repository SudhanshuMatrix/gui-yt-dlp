import time
import requests
from PySide6.QtCore import QThread, Signal
from .logger import get_logger

logger = get_logger("speed_test")

class SpeedTestWorker(QThread):
    progress = Signal(int)         # Progress percent (0-100)
    finished = Signal(float, str)   # speed in bytes/sec, formatted string
    error = Signal(str)

    def run(self):
        # 5 MB test file from Cloudflare
        url = "https://speed.cloudflare.com/__down?bytes=5242880"
        try:
            logger.info("Starting speed test...")
            start_time = time.time()
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            
            total_length = response.headers.get('content-length')
            if total_length is None:
                total_length = 5242880
            else:
                total_length = int(total_length)

            downloaded = 0
            chunk_size = 1024 * 32 # 32 KB chunks
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                downloaded += len(chunk)
                percent = int((downloaded / total_length) * 100)
                self.progress.emit(min(percent, 100))

            duration = time.time() - start_time
            if duration <= 0:
                duration = 0.001
                
            speed_bps = downloaded / duration
            
            # Format speed using simple utility
            speed_str = self._format_speed(speed_bps)
            logger.info(f"Speed test completed: {speed_str}")
            self.finished.emit(speed_bps, speed_str)
        except Exception as e:
            logger.error(f"Speed test failed: {e}")
            self.error.emit(str(e))

    @staticmethod
    def _format_speed(speed_bytes_sec: float) -> str:
        if speed_bytes_sec <= 0:
            return "0 B/s"
        size_name = ("B/s", "KB/s", "MB/s", "GB/s")
        import math
        i = int(math.floor(math.log(speed_bytes_sec, 1024)))
        p = math.pow(1024, i)
        s = round(speed_bytes_sec / p, 2)
        return f"{s} {size_name[i]}"
