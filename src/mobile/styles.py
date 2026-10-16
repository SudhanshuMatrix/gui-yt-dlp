"""Minimal, touch-friendly QSS for the Android UI.

PySide6-Fluent-Widgets (used by the desktop app) is built on Win32 APIs and
cannot run on Android, so the mobile UI uses plain QtWidgets with a small
hand-written stylesheet instead — larger tap targets, bigger fonts, no
hover-dependent states.
"""

MOBILE_QSS = """
QWidget {
    background-color: #121214;
    color: #f4f4f5;
    font-size: 15px;
}

QLabel#screenTitle {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 4px;
}

QLabel#cardTitle {
    font-size: 15px;
    font-weight: 600;
}

QLabel#mutedLabel {
    color: #a1a1aa;
    font-size: 12px;
}

QFrame#card {
    background-color: #1e1e23;
    border: 1px solid #35353f;
    border-radius: 10px;
}

QLineEdit {
    background-color: #1a1a1e;
    border: 1px solid #35353f;
    border-radius: 8px;
    padding: 12px 14px;
    min-height: 26px;
}
QLineEdit:focus {
    border: 1px solid #8b5cf6;
}

QComboBox, QSpinBox {
    background-color: #1a1a1e;
    border: 1px solid #35353f;
    border-radius: 8px;
    padding: 10px 12px;
    min-height: 26px;
}

QPushButton {
    background-color: #28282f;
    border: none;
    border-radius: 8px;
    padding: 14px 18px;
    font-weight: 600;
    min-height: 24px;
}
QPushButton:pressed {
    background-color: #35353f;
}
QPushButton:disabled {
    color: #71717a;
}

QPushButton#primaryButton {
    background-color: #8b5cf6;
    color: #ffffff;
}
QPushButton#primaryButton:pressed {
    background-color: #7c3aed;
}
QPushButton#primaryButton:disabled {
    background-color: #28282f;
    color: #71717a;
}

QPushButton#dangerButton {
    background-color: transparent;
    border: 1px solid #ef4444;
    color: #ef4444;
}
QPushButton#dangerButton:pressed {
    background-color: #ef4444;
    color: #ffffff;
}

QProgressBar {
    border: none;
    border-radius: 7px;
    background-color: #28282f;
    text-align: center;
    min-height: 18px;
    font-weight: 600;
}
QProgressBar::chunk {
    background-color: #8b5cf6;
    border-radius: 7px;
}

QListWidget {
    background-color: transparent;
    border: none;
}
QListWidget::item {
    background-color: transparent;
    border: none;
    margin-bottom: 8px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QWidget#navBar {
    background-color: #1a1a1e;
    border-top: 1px solid #35353f;
}
QPushButton#navButton {
    background-color: transparent;
    border: none;
    border-radius: 0px;
    font-size: 11px;
    font-weight: 600;
    padding: 8px 4px;
    color: #a1a1aa;
}
QPushButton#navButton:checked {
    color: #a78bfa;
}

QCheckBox {
    spacing: 10px;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 1px solid #35353f;
    border-radius: 5px;
    background: #1a1a1e;
}
QCheckBox::indicator:checked {
    background-color: #8b5cf6;
    border: 1px solid #8b5cf6;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #35353f;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
