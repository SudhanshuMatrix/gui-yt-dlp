from typing import Dict, Any

# Define color palettes for themes
THEMES: Dict[str, Dict[str, str]] = {
    "Midnight Obsidian": {
        "bg_main": "#121214",
        "bg_card": "#1a1a1e",
        "bg_hover": "#26262b",
        "bg_selected": "#2e2e35",
        "border": "#2c2c35",
        "border_focus": "#a78bfa",  # Pastel Purple
        "text_primary": "#f4f4f5",
        "text_secondary": "#a1a1aa",
        "text_muted": "#71717a",
        "accent": "#8b5cf6",        # Purple
        "accent_hover": "#7c3aed",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9)",
        "success": "#10b981",       # Emerald Green
        "danger": "#ef4444",        # Red
        "warning": "#f59e0b"        # Amber
    },
    "Electric Indigo": {
        "bg_main": "#0b0f19",
        "bg_card": "#111827",
        "bg_hover": "#1f2937",
        "bg_selected": "#374151",
        "border": "#1f2937",
        "border_focus": "#60a5fa",  # Light Blue
        "text_primary": "#f9fafb",
        "text_secondary": "#9ca3af",
        "text_muted": "#6b7280",
        "accent": "#3b82f6",        # Blue
        "accent_hover": "#2563eb",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #1d4ed8)",
        "success": "#34d399",
        "danger": "#f87171",
        "warning": "#fbbf24"
    },
    "Emerald Forest": {
        "bg_main": "#0c1311",
        "bg_card": "#121f1c",
        "bg_hover": "#1d2e2b",
        "bg_selected": "#283f3a",
        "border": "#223531",
        "border_focus": "#34d399",  # Green
        "text_primary": "#f0fdf4",
        "text_secondary": "#a7f3d0",
        "text_muted": "#6ee7b7",
        "accent": "#059669",        # Forest Accent
        "accent_hover": "#047857",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #059669, stop:1 #064e3b)",
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b"
    },
    "Cyberpunk Rust": {
        "bg_main": "#181414",
        "bg_card": "#211c1c",
        "bg_hover": "#2e2727",
        "bg_selected": "#3d3232",
        "border": "#332a2a",
        "border_focus": "#f97316",  # Neon Orange
        "text_primary": "#fafaf9",
        "text_secondary": "#d6d3d1",
        "text_muted": "#78716c",
        "accent": "#ea580c",        # Orange
        "accent_hover": "#c2410c",
        "accent_gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ea580c, stop:1 #ea580c)",
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b"
    }
}

import os

def get_checkmark_svg_path() -> str:
    config_dir = os.path.expanduser("~/.config/gui-yt-dlp")
    os.makedirs(config_dir, exist_ok=True)
    svg_path = os.path.join(config_dir, "check.svg")
    if not os.path.exists(svg_path):
        svg_content = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="12px" height="12px">'
            '<path d="M0 0h24v24H0V0z" fill="none"/>'
            '<path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/>'
            '</svg>'
        )
        try:
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
        except Exception:
            pass
    return svg_path.replace(os.sep, '/')

def get_stylesheet(theme_name: str) -> str:
    """Generate and return QSS stylesheet for the given theme name."""
    palette = THEMES.get(theme_name, THEMES["Midnight Obsidian"])
    check_svg_path = get_checkmark_svg_path()
    
    qss = f"""
    /* Main Window & Base Widget Styles */
    QMainWindow {{
        background-color: {palette["bg_main"]};
    }}
    
    QWidget {{
        font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
        color: {palette["text_primary"]};
        font-size: 13px;
    }}
    
    QLabel {{
        color: {palette["text_primary"]};
        background: transparent;
    }}
    
    QLabel#titleLabel {{
        font-weight: bold;
        font-size: 18px;
    }}

    QLabel#subtitleLabel {{
        color: {palette["text_secondary"]};
        font-size: 12px;
    }}
    
    QLabel#sectionHeader {{
        font-weight: bold;
        font-size: 14px;
        color: {palette["border_focus"]};
    }}
    
    /* Layouts / Frames */
    QFrame#cardFrame {{
        background-color: {palette["bg_card"]};
        border: 1px solid {palette["border"]};
        border-radius: 8px;
    }}
    
    QFrame#sidebarFrame {{
        background-color: {palette["bg_card"]};
        border-right: 1px solid {palette["border"]};
    }}
    
    /* Inputs: Lines & Text Edits */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {palette["bg_main"]};
        border: 1px solid {palette["border"]};
        border-radius: 6px;
        padding: 8px 12px;
        color: {palette["text_primary"]};
        selection-background-color: {palette["accent"]};
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {palette["border_focus"]};
    }}
    
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
        background-color: {palette["bg_hover"]};
        color: {palette["text_muted"]};
    }}
    
    /* Combo Boxes & Spin Boxes */
    QComboBox, QSpinBox {{
        background-color: {palette["bg_card"]};
        border: 1px solid {palette["border"]};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 24px;
        color: {palette["text_primary"]};
    }}
    
    QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {palette["border_focus"]};
    }}
    
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 20px;
        border-left-width: 0px;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {palette["bg_card"]};
        border: 1px solid {palette["border"]};
        selection-background-color: {palette["bg_hover"]};
        selection-color: {palette["text_primary"]};
        padding: 4px;
    }}
    
    /* Push Buttons */
    QPushButton {{
        background-color: {palette["bg_hover"]};
        border: 1px solid {palette["border"]};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
        min-height: 20px;
        color: {palette["text_primary"]};
    }}
    
    QPushButton:hover {{
        background-color: {palette["bg_selected"]};
        border-color: {palette["text_secondary"]};
    }}
    
    QPushButton:pressed {{
        background-color: {palette["bg_main"]};
    }}
    
    QPushButton:disabled {{
        background-color: {palette["bg_hover"]};
        color: {palette["text_muted"]};
        border-color: {palette["border"]};
    }}
    
    /* Primary / Accent Buttons */
    QPushButton#primaryButton {{
        background: {palette["accent_gradient"]};
        color: #ffffff;
        font-weight: bold;
        border: none;
    }}
    
    QPushButton#primaryButton:hover {{
        background-color: {palette["accent_hover"]};
        border: 1px solid {palette["border_focus"]};
    }}
    
    QPushButton#primaryButton:pressed {{
        background-color: {palette["accent"]};
    }}
    
    /* Danger Buttons */
    QPushButton#dangerButton {{
        background-color: {palette["danger"]}40; /* 25% opacity */
        border: 1px solid {palette["danger"]};
        color: {palette["text_primary"]};
    }}
    
    QPushButton#dangerButton:hover {{
        background-color: {palette["danger"]};
        color: #ffffff;
    }}
    
    /* Tabs styling (flat modern look) */
    QTabWidget::pane {{
        border: none;
        top: 0px;
    }}
    
    QTabBar::tab {{
        background: {palette["bg_card"]};
        color: {palette["text_secondary"]};
        border-bottom: 2px solid {palette["border"]};
        padding: 10px 20px;
        font-weight: bold;
        min-width: 80px;
    }}
    
    QTabBar::tab:hover {{
        color: {palette["text_primary"]};
        background: {palette["bg_hover"]};
    }}
    
    QTabBar::tab:selected {{
        color: {palette["border_focus"]};
        border-bottom: 2px solid {palette["border_focus"]};
        background: {palette["bg_hover"]};
    }}
    
    /* Table Views */
    QTableWidget, QTableView {{
        background-color: {palette["bg_card"]};
        border: 1px solid {palette["border"]};
        gridline-color: {palette["border"]};
        border-radius: 8px;
        selection-background-color: {palette["bg_hover"]};
        selection-color: {palette["text_primary"]};
    }}
    
    QHeaderView::section {{
        background-color: {palette["bg_main"]};
        color: {palette["text_secondary"]};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {palette["border"]};
        font-weight: bold;
    }}
    
    QHeaderView::section:horizontal {{
        border-right: 1px solid {palette["border"]};
    }}

    /* Scroll Areas */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        border: none;
        background: {palette["bg_main"]};
        width: 10px;
        margin: 0px;
    }}
    
    QScrollBar::handle:vertical {{
        background: {palette["border"]};
        min-height: 20px;
        border-radius: 5px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: {palette["text_muted"]};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        border: none;
        background: {palette["bg_main"]};
        height: 10px;
        margin: 0px;
    }}
    
    QScrollBar::handle:horizontal {{
        background: {palette["border"]};
        min-width: 20px;
        border-radius: 5px;
    }}
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    
    /* Progress Bars (extremely smooth/glowing) */
    QProgressBar {{
        border: 1px solid {palette["border"]};
        border-radius: 6px;
        text-align: center;
        background-color: {palette["bg_main"]};
        color: {palette["text_primary"]};
        font-weight: bold;
    }}
    
    QProgressBar::chunk {{
        background-color: {palette["accent"]};
        border-radius: 5px;
    }}
    
    /* Checkbox & Radio Buttons */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {palette["text_primary"]};
    }}
    
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {palette["border"]};
        border-radius: 4px;
        background: {palette["bg_main"]};
    }}
    
    QCheckBox::indicator:unchecked:hover, QRadioButton::indicator:unchecked:hover {{
        border: 1px solid {palette["text_secondary"]};
    }}
    
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {palette["accent"]};
        border: 1px solid {palette["border_focus"]};
        image: url({check_svg_path});
    }}
    
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
        border-color: {palette["border"]};
        background: {palette["bg_hover"]};
    }}
    
    /* Group Boxes */
    QGroupBox {{
        background-color: {palette["bg_card"]};
        border: 1px solid {palette["border"]};
        border-radius: 8px;
        margin-top: 16px;
        font-weight: bold;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0px 5px;
        color: {palette["border_focus"]};
    }}

    /* Splitter Handles */
    QSplitter::handle {{
        background-color: {palette["border"]};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}
    """
    
    return qss
