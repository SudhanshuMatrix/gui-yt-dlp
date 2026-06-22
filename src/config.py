import os
import json
from typing import Any, Dict
from .utils.logger import get_logger

logger = get_logger("config")

DEFAULT_SETTINGS = {
    "download_directory": os.path.expanduser("~/Downloads"),
    "ffmpeg_path": "",
    "concurrency": 3,
    "theme": "Midnight Obsidian",
    "auto_update": True,
    "embed_subtitles": False,
    "embed_thumbnail": False,
    "add_metadata": False,
    "preferred_audio_format": "mp3",
    "audio_quality": "192",
    "write_auto_subs": False,
    "subtitle_lang": "en"
}

class AppConfig:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/gui-yt-dlp")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> None:
        """Load settings from JSON file. Creates one if it doesn't exist."""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir, exist_ok=True)
            
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    # Merge default settings to ensure new fields are populated
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
        """Save current settings to JSON file."""
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir, exist_ok=True)
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            logger.info("Settings saved successfully.")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting by key."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting by key and save."""
        self.settings[key] = value
        self.save()

# Global config instance
config_manager = AppConfig()
