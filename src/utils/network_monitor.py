import socket
import time
from PySide6.QtCore import QThread, Signal
from .logger import get_logger

logger = get_logger("network_monitor")

class NetworkMonitor(QThread):
    status_changed = Signal(bool) # Emits True if online, False if offline

    def __init__(self, check_interval=4, timeout=2):
        super().__init__()
        self.check_interval = check_interval
        self.timeout = timeout
        self.is_online = True
        self.running = True

    def check_connection(self) -> bool:
        # Try primary DNS servers on port 53 (TCP connection check is fast and doesn't require root privileges)
        hosts = [("8.8.8.8", 53), ("1.1.1.1", 53), ("google.com", 80)]
        for host, port in hosts:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.timeout)
                s.connect((host, port))
                s.close()
                return True
            except OSError:
                continue
        return False

    def stop(self):
        self.running = False

    def run(self):
        # Initial check
        self.is_online = self.check_connection()
        self.status_changed.emit(self.is_online)
        
        while self.running:
            for _ in range(int(self.check_interval * 10)):
                if not self.running:
                    break
                time.sleep(0.1)
                
            if not self.running:
                break
                
            current_status = self.check_connection()
            if current_status != self.is_online:
                self.is_online = current_status
                logger.info(f"Network status changed: {'Online' if self.is_online else 'Offline'}")
                self.status_changed.emit(self.is_online)
