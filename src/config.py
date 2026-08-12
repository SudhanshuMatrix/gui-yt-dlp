import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from .constants import DEFAULT_SETTINGS
from .utils.logger import get_logger

logger = get_logger("config")


class AppConfig:
    def __init__(self):
        self.config_dir: Path = Path.home() / ".config" / "gui-yt-dlp"
        self.config_file: Path = self.config_dir / "settings.json"
        self.settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self._dirty: bool = False
        self._save_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self.load()

    def load(self) -> None:
        """Load settings from JSON file. Creates default file if missing."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    for k, v in DEFAULT_SETTINGS.items():
                        if k not in loaded_data:
                            loaded_data[k] = v
                    self.settings = loaded_data
                    logger.info("Settings loaded successfully.")
            else:
                self.save()
                logger.info("Created default settings file.")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self.settings = DEFAULT_SETTINGS.copy()

    def save(self) -> None:
        """Save current settings to JSON file atomically."""
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None

            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
                tmp_file = self.config_file.with_suffix(".tmp")
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(self.settings, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())

                os.replace(tmp_file, self.config_file)
                self._dirty = False
                logger.info("Settings saved atomically.")
            except Exception as e:
                logger.error(f"Error saving settings: {e}")

    def schedule_save(self, delay: float = 1.0) -> None:
        """Schedule a debounced save operation."""
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(delay, self.save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting by key."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any, save_immediately: bool = False) -> None:
        """Set a setting by key and queue save."""
        self.settings[key] = value
        self._dirty = True
        if save_immediately:
            self.save()
        else:
            self.schedule_save()

    def flush(self) -> None:
        """Flush pending dirty settings immediately."""
        if self._dirty:
            self.save()


# Global config instance
config_manager = AppConfig()
