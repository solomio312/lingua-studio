"""
Global Theme Manager for Lingua Day/Night Modes.
"""
from lingua.core.config import get_config
import os

# Resource path for local SVGs
THEME_DIR = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
RES_PATH = f"{THEME_DIR}/resources"

DARK_THEME = """
/* Global Dark Theme - Grey & Black Masterclass Edition (Maximum Contrast) */
QMainWindow, QWidget, QDialog {
    background-color: #2b2b2b; /* Professional Medium-Dark Grey */
    color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Toolbar & Control Groups */
QFrame#settingsBar {
    background-color: #252525;
    border-bottom: 2px solid #3d3d3d;
}

QFrame#settingsGroup {
    background-color: #333333; /* Distinct Grey Panel */
    border: 1px solid #444444;
    border-radius: 8px;
    margin: 2px 0;
}

QFrame#settingsGroup QLabel {
    color: #a1a1aa;
}

QFrame#settingsGroup:hover {
    background-color: #3d3d3d;
    border: 1px solid #007acc;
}

/* Labels - High Contrast White */
QLabel {
    color: #f5f5f5;
}
QLabel#mainTitle {
    font-size: 34px;
    font-weight: bold;
    color: #ffffff;
    letter-spacing: -0.5px;
}

QLabel#title {
    color: #ffffff;
    font-weight: bold;
}

QLabel#subtitle {
    color: #888888;
}

QLabel#motto {
    font-family: "Georgia", "Times New Roman", serif;
    font-style: italic;
    font-size: 14px;
    color: #888;
    margin-top: 2px;
}

QFrame#headerFrame {
    margin-bottom: 5px;
}

/* Buttons - Intense Grey Style */
QPushButton {
    background-color: #454545; /* Solid Grey Button */
    border: 1px solid #555555;
    color: #ffffff;
    border-radius: 4px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: bold;
    min-height: 26px;
}
QPushButton:hover { 
    background-color: #555555; 
    border: 1px solid #007acc; 
}
QPushButton:pressed { 
    background-color: #1a1a1a; 
}
QPushButton:disabled { 
    background-color: #333333; 
    color: #777777; 
    border: 1px solid #444444; 
}

QPlainTextEdit#testOutput {
    color: #4ade80;
    font-weight: bold;
    background-color: #1a1a1a;
}

QPushButton#primary { 
    background-color: #0e639c; 
    color: white; 
    border: 1px solid #1177bb;
    font-weight: bold; 
    min-height: 30px;
}
QPushButton#primary:hover { 
    background-color: #1177bb; 
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 10px;
    margin: 0px 0 0px 0;
}
QScrollBar::handle:vertical {
    background: #444;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Group Boxes - Bold Headers and Grey Fill */
QGroupBox {
    background-color: #333333; /* Grey background for the group box */
    border: 1px solid #4a4a4a;
    border-radius: 6px;
    margin-top: 1.8ex;
    font-weight: bold;
    color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 8px;
    background-color: transparent;
}

/* Inputs & Combos - Deep Black for Maximum Contrast against Grey */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background-color: #1a1a1b; /* Deep Black Input */
    border: 1px solid #3d3d42;
    color: #ffffff;
    border-radius: 3px;
    padding: 4px 24px 4px 8px;
    font-size: 11px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { 
    border: 1px solid #007acc;
    background-color: #000000;
}
QComboBox::drop-down { 
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
}
QComboBox::down-arrow {
    image: url("REPLACE_CHEVRON_DOWN");
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background-color: #222222;
    border: 1px solid #444444;
    color: #ffffff;
    selection-background-color: #007acc;
}

/* Tabs - Professional High Contrast */
QTabWidget::pane { 
    border: 1px solid #3d3d3d;
    background-color: #2b2b2b;
    top: -1px;
}
QTabBar::tab {
    background-color: #333333;
    color: #aaaaaa;
    border: 1px solid #3d3d3d;
    border-bottom: none;
    padding: 10px 24px;
    min-width: 110px;
}
QTabBar::tab:selected {
    background-color: #2b2b2b;
    color: #ffffff;
    border-bottom: 3px solid #007acc;
    font-weight: bold;
}
QTabBar::tab:hover {
    background-color: #3d3d3d;
}

/* Table */
QTableView {
    background-color: #1e1e1e;
    alternate-background-color: #252526;
    border: 1px solid #333;
    gridline-color: #333;
    color: #d4d4d4;
    selection-background-color: #094771;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #2d2d30;
    color: #cccccc;
    padding: 5px;
    border: 1px solid #3e3e42;
    border-left: none;
    border-top: none;
    font-weight: bold;
}
QTableView::item {
    border-bottom: 1px solid #333;
    padding: 4px;
}

/* Progress Bar */
QProgressBar { 
    border: none; 
    background-color: #1e1e23; 
    border-radius: 3px; 
}
QProgressBar::chunk { 
    background-color: #648cff; 
    border-radius: 3px; 
}

/* Dashboards Project Cards */
QFrame#projectCard {
    background-color: #2a2c33;
    border-radius: 12px;
    border: 1px solid #3f414a;
}
QFrame#projectCard:hover {
    border-color: #648cff;
    background-color: #303340;
}


/* Consoles */
QPlainTextEdit#logConsole {
    background-color: #1e1e1e;
    color: #dcdee4;
    font-family: Consolas, monospace;
    font-size: 11px;
}
QPlainTextEdit#errorConsole {
    background-color: #1e1e1e;
    color: #f87171;
    font-family: Consolas, monospace;
    font-size: 11px;
}

/* Sidebar Navigation (Piano Effect) */
QListWidget {
    background-color: #222222;
    border: none;
    border-right: 1px solid #333;
    outline: none;
    padding-top: 15px;
}

QListWidget::item {
    color: #888;
    padding-left: 15px;
    margin: 2px 0px;
    height: 44px;
    border-left: 3px solid transparent;
    transition: all 0.2s ease; /* Note: QSS transition support is limited, but padding works */
}

QListWidget::item:hover {
    background-color: #2d2d2d;
    color: #4ade80;
    padding-left: 25px; /* Piano slide out */
    border-left: 3px solid #4ade80;
}

QListWidget::item:selected {
    background-color: #333d33;
    color: #ffffff;
    padding-left: 25px;
    border-left: 3px solid #4ade80;
    font-weight: bold;
}
"""

LIGHT_THEME = """
/* Global Light Theme */
QMainWindow, QWidget, QDialog {
    background-color: #f3f4f6;
    color: #111827;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Scroll Areas and Stacked Widgets */
QScrollArea, QStackedWidget {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* List Widgets (Sidebar Piano Effect) */
QListWidget {
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
    padding-top: 20px;
    outline: none;
}
QListWidget::item {
    color: #4b5563;
    padding-left: 20px;
    border-radius: 0px; /* Piano looks better with straight edges or full block */
    margin: 2px 0px;
    height: 44px;
    border-left: 4px solid transparent;
}
QListWidget::item:hover {
    background-color: #f9fafb;
    color: #2563eb;
    padding-left: 32px; /* Piano slide out */
    border-left: 4px solid #2563eb;
}
QListWidget::item:selected {
    background-color: #eff6ff;
    color: #2563eb;
    padding-left: 32px;
    border-left: 4px solid #2563eb;
    font-weight: bold;
}

/* Labels */
QLabel {
    color: #111827;
}
QLabel#mainTitle {
    font-size: 34px;
    font-weight: bold;
    color: #000;
    letter-spacing: -0.5px;
}

QLabel#title {
    color: #000000;
    font-weight: bold;
}

QLabel#subtitle {
    color: #6b7280;
}

QLabel#motto {
    font-family: "Georgia", "Times New Roman", serif;
    font-style: italic;
    font-size: 14px;
    color: #6b7280;
    margin-top: 2px;
}

QFrame#headerFrame {
    margin-bottom: 5px;
}

QLabel#subtitle {
    font-size: 14px;
    color: #6b7280;
}

/* Buttons */
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    color: #374151;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 11px;
    min-height: 22px;
}
QPushButton:hover { background-color: #f9fafb; border: 1px solid #9ca3af; }
QPushButton:pressed { background-color: #e5e7eb; }
QPushButton:disabled { background-color: #f3f4f6; color: #9ca3af; border: 1px solid #e5e7eb; }

QPushButton#primary { background-color: #2563eb; color: white; border: none; font-weight: bold; }
QPushButton#primary:hover { background-color: #1d4ed8; }
QPushButton#primary:pressed { background-color: #1e40af; }

QPushButton#output_btn { background-color: #e5e7eb; border: 1px solid #d1d5db; font-weight: bold; }
QPushButton#output_btn:hover { background-color: #d1d5db; border: 1px solid #9ca3af; }

QPushButton#enabled_btn { background-color: #16a34a; border: 1px solid #14532d; color: white; font-weight: bold; }
QPushButton#enabled_btn:hover { background-color: #15803d; border: 1px solid #16a34a; }
QPushButton#enabled_btn:pressed { background-color: #166534; }

QPushButton#danger_btn:hover { background-color: #ef4444; border: 1px solid #b91c1c; color: white; }
QPushButton#danger_btn:pressed { background-color: #dc2626; }

/* Group Boxes */
QGroupBox {
    border: 1px solid #d1d5db;
    border-radius: 6px;
    margin-top: 1ex;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
    color: #6b7280;
    font-weight: bold;
}

/* Inputs & Combos */
QLineEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    color: #111827;
    border-radius: 4px;
    padding: 4px 22px 4px 8px;
    font-size: 11px;
    min-height: 26px;
}
QComboBox::drop-down { 
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
}
QComboBox::down-arrow {
    image: url("REPLACE_CHEVRON_DOWN");
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    color: #111827;
    selection-background-color: #f3f4f6;
    selection-color: #111827;
}

/* Table */
QTableView {
    background-color: #ffffff;
    alternate-background-color: #f9fafb;
    border: 1px solid #d1d5db;
    gridline-color: #e5e7eb;
    color: #111827;
    selection-background-color: #bfdbfe;
    selection-color: #1e3a8a;
}
QHeaderView::section {
    background-color: #f3f4f6;
    color: #374151;
    padding: 5px;
    border: 1px solid #d1d5db;
    border-left: none;
    border-top: none;
    font-weight: bold;
}
QTableView::item {
    border-bottom: 1px solid #e5e7eb;
    padding: 4px;
}

/* Radio & Checkbox Indicators */
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #9ca3af;
    background-color: #ffffff;
    border-radius: 3px;
}
QRadioButton::indicator {
    border-radius: 9px;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #2563eb;
    border: 2px solid #1d4ed8;
}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {
    border: 2px solid #6b7280;
}

/* Progress Bar */
QProgressBar { 
    border: none; 
    background-color: #f3f4f6; 
    border-radius: 3px; 
}
QProgressBar::chunk { 
    background-color: #2563eb; 
    border-radius: 3px; 
}

/* Dashboards Project Cards */
QFrame#projectCard {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #d1d5db;
}
QFrame#projectCard:hover {
    border-color: #4f46e5;
    background-color: #f9fafb;
    /* Box shadows are trickier in pure QSS, relying on border changes primarily */
}

/* Settings Bar & Groups (Premium Styling - Phase 13 Light) */
QFrame#settingsBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e7eb;
}

QFrame#settingsGroup {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-top: 1px solid #ffffff; /* Contrast highlight */
    border-bottom: 2px solid #e5e7eb; /* 3D depth */
    border-radius: 10px;
    margin: 2px 0;
}

QFrame#settingsGroup QLabel {
    color: #4b5563;
}

QFrame#settingsGroup:hover {
    background-color: #f0fdf4; /* Subtle green wash */
    border: 2px solid #22c55e; /* Stronger green glow */
    border-top: 1px solid #4ade80;
}

/* Consoles */
QPlainTextEdit#logConsole {
    background-color: #f9fafb;
    color: #374151;
    font-family: Consolas, monospace;
    font-size: 11px;
}
QPlainTextEdit#errorConsole {
    background-color: #fef2f2;
    color: #dc2626;
    font-family: Consolas, monospace;
    font-size: 11px;
}

/* Right Tabs & Re-Chunk */
QTabWidget#workspaceTabs::pane { 
    border: 1px solid #d1d5db; 
}
QTabWidget#workspaceTabs > QTabBar::tab { 
    background: #f3f4f6; 
    color: #6b7280; 
    padding: 6px 16px; 
    border: 1px solid #d1d5db; 
    border-bottom: none; 
    border-top-left-radius: 4px; 
    border-top-right-radius: 4px; 
}
QTabWidget#workspaceTabs > QTabBar::tab:selected { 
    background: #ffffff; 
    color: #111827; 
    font-weight: bold; 
}

QGroupBox#rechunkPanel { 
    font-weight: bold; 
    border: 1px solid #d1d5db; 
    border-radius: 4px; 
    margin-top: 6px; 
    padding-top: 14px; 
    color: #d97706; 
}
QGroupBox#rechunkPanel::title { 
    subcontrol-origin: margin; 
    left: 10px; 
    padding: 0 4px; 
}
"""

SEPIA_THEME = """
/* Warm Sepia Theme - Restful and Elegant */
QMainWindow, QWidget, QDialog {
    background-color: #f4ece1; /* Warm creamy background */
    color: #433422; /* Dark Brown text */
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Toolbar & Control Groups */
QFrame#settingsBar {
    background-color: #ede2cf;
    border-bottom: 2px solid #dcc9af;
}

QFrame#settingsGroup {
    background-color: #e9dec9;
    border: 1px solid #dcc9af;
    border-radius: 8px;
    margin: 2px 0;
}

QFrame#settingsGroup QLabel {
    color: #7b6343;
}

/* Labels */
QLabel {
    color: #433422;
}
QLabel#mainTitle {
    font-size: 34px;
    font-weight: bold;
    color: #2d2419;
}

QLabel#title {
    color: #2d2419;
    font-weight: bold;
}

QLabel#subtitle {
    color: #7b6343;
}

/* Buttons */
QPushButton {
    background-color: #e6dac3;
    border: 1px solid #dcc9af;
    color: #433422;
    border-radius: 4px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover { 
    background-color: #dfd0b5; 
    border: 1px solid #c9b38c; 
}
QPushButton#primary { 
    background-color: #8b5e3c; 
    color: white; 
}

/* Inputs */
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit {
    background-color: #fdfaf4;
    border: 1px solid #dcc9af;
    color: #433422;
    padding: 4px 8px;
    font-size: 11px;
}
QComboBox::drop-down { 
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
}
QComboBox::down-arrow {
    image: url("REPLACE_CHEVRON_DOWN");
    width: 10px;
    height: 10px;
}

/* Table */
QTableView {
    background-color: #faf7ef;
    alternate-background-color: #f3eee3;
    color: #433422;
    selection-background-color: #dcc9af;
    selection-color: #2d2419;
}

/* Tabs */
QTabBar::tab {
    background-color: #e9dec9;
    color: #7b6343;
}
QTabBar::tab:selected {
    background-color: #f4ece1;
    color: #433422;
    border-bottom: 3px solid #8b5e3c;
}

/* Project Cards */
QFrame#projectCard {
    background-color: #faf7ef;
    border: 1px solid #dcc9af;
}

/* Consoles */
QPlainTextEdit#logConsole, QPlainTextEdit#errorConsole {
    background-color: #1a1a1b;
    color: #e0e0e0;
}

/* Radio & Checkbox Indicators */
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #8b5e3c;
    background-color: #fdfaf4;
    border-radius: 3px;
}
QRadioButton::indicator {
    border-radius: 9px;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #8b5e3c;
    image: none; /* remove default checkmark if any */
}
QRadioButton::indicator:checked {
    border: 4px solid #fdfaf4; /* Inset look */
    background-color: #8b5e3c;
}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {
    border: 2px solid #5d3f28;
}

/* Sidebar Navigation (Piano Effect) */
QListWidget {
    background-color: #ede2cf;
    border: none;
    border-right: 1px solid #dcc9af;
    outline: none;
    padding-top: 20px;
}

QListWidget::item {
    color: #7b6343;
    padding-left: 20px;
    margin: 2px 0px;
    height: 44px;
    border-left: 4px solid transparent;
}

QListWidget::item:hover {
    background-color: #e6dac3;
    color: #433422;
    padding-left: 32px; /* Piano slide out */
    border-left: 4px solid #8b5e3c;
}

QListWidget::item:selected {
    background-color: #dfd0b5;
    color: #2d2419;
    padding-left: 32px;
    border-left: 4px solid #8b5e3c;
    font-weight: bold;
}
"""


class ThemeManager:
    """Manages application-wide styles."""
    
    @staticmethod
    def apply_theme(app, theme_name="dark"):
        name = str(theme_name).lower()
        if name == "light":
            style = LIGHT_THEME.replace("REPLACE_CHEVRON_DOWN", f"{RES_PATH}/chevron_down_light.svg")
            app.setStyleSheet(style)
        elif name == "sepia":
            style = SEPIA_THEME.replace("REPLACE_CHEVRON_DOWN", f"{RES_PATH}/chevron_down_sepia.svg")
            app.setStyleSheet(style)
        else:
            style = DARK_THEME.replace("REPLACE_CHEVRON_DOWN", f"{RES_PATH}/chevron_down_dark.svg")
            app.setStyleSheet(style)
