import json
from pathlib import Path

from src.config import AppConfig


def test_config_load_and_save(tmp_path: Path):
    config = AppConfig()
    config.config_dir = tmp_path
    config.config_file = tmp_path / "settings.json"

    # Set new value and save immediately
    config.set("concurrency", 5, save_immediately=True)
    assert config.get("concurrency") == 5

    # Check file contents
    assert config.config_file.exists()
    with open(config.config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["concurrency"] == 5


def test_config_debounced_save(tmp_path: Path):
    config = AppConfig()
    config.config_dir = tmp_path
    config.config_file = tmp_path / "settings.json"

    config.set("theme", "Neon Cyberpunk")
    assert config._dirty is True

    # Flush saves immediately
    config.flush()
    assert config._dirty is False
    assert config.config_file.exists()
