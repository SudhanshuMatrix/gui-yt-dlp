"""Appearance helpers for the Fluent-Design UI (qfluentwidgets).

The hand-rolled QSS theme system this module used to contain has been
replaced by PySide6-Fluent-Widgets, which ships its own native dark/light
theming and per-widget elevation/animation — there's no custom stylesheet
to generate anymore. This module just persists/applies the user's
theme-mode + accent-color preference through the app's existing
`config_manager` (no new config system introduced).
"""

from PySide6.QtGui import QColor
from qfluentwidgets import Theme, setTheme, setThemeColor

# Curated accent presets shown as swatches in Settings → Personalization.
ACCENT_PRESETS: dict[str, str] = {
    "Purple": "#8b5cf6",
    "Blue": "#3b82f6",
    "Green": "#059669",
    "Orange": "#ea580c",
    "Pink": "#ec4899",
    "Red": "#ef4444",
}

THEME_MODES: dict[str, Theme] = {
    "dark": Theme.DARK,
    "light": Theme.LIGHT,
    "auto": Theme.AUTO,  # follows the OS light/dark setting (via darkdetect)
}


def get_saved_theme_mode(config_manager) -> str:
    """Return the persisted theme mode ('dark'/'light'/'auto'), migrating the
    older boolean 'dark_mode' setting the first time it's read."""
    mode = config_manager.get("theme_mode")
    if mode not in THEME_MODES:
        mode = "dark" if config_manager.get("dark_mode", True) else "light"
    return mode


def apply_saved_appearance(config_manager) -> None:
    """Apply the persisted theme-mode + accent-color preference at startup."""
    setTheme(THEME_MODES.get(get_saved_theme_mode(config_manager), Theme.DARK))
    accent = config_manager.get("accent_color", "#8b5cf6")
    try:
        setThemeColor(QColor(accent))
    except Exception:
        setThemeColor(QColor(ACCENT_PRESETS["Purple"]))
