import os

from src.constants import APP_NAME, APP_VERSION, DEFAULT_SETTINGS, get_asset_path


def test_constants_version():
    assert APP_NAME == "gui-yt-dlp"
    assert isinstance(APP_VERSION, str)
    assert len(APP_VERSION) > 0


def test_default_settings_keys():
    assert "download_directory" in DEFAULT_SETTINGS
    assert "concurrency" in DEFAULT_SETTINGS
    assert "bypass_throttling" in DEFAULT_SETTINGS
    assert "socket_timeout" in DEFAULT_SETTINGS


def test_asset_path_resolution():
    logo_path = get_asset_path("logo.jpeg")
    assert logo_path != ""
    assert os.path.exists(logo_path)
