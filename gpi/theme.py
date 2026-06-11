"""GPI dark Fusion theme — palette, QSS, and apply helper."""
import sys as _sys
from gpi import QtCore, QtGui, QtWidgets

_DARK_PALETTE = {
    # key: (QPalette.Group or None, hex)
    'Window':          (None,       '#353535'),
    'WindowText':      (None,       '#dcdcdc'),
    'Base':            (None,       '#1e1e1e'),
    'AlternateBase':   (None,       '#2d2d2d'),
    'ToolTipBase':     (None,       '#252525'),
    'ToolTipText':     (None,       '#dcdcdc'),
    'Text':            (None,       '#dcdcdc'),
    'Button':          (None,       '#3c3c3c'),
    'ButtonText':      (None,       '#dcdcdc'),
    'BrightText':      (None,       '#ff5555'),
    'Highlight':       (None,       '#2a82da'),
    'HighlightedText': (None,       '#ffffff'),
    'Link':            (None,       '#4a9eda'),
    'LinkVisited':     (None,       '#9a6fe0'),
    'Disabled_WindowText': ('Disabled', '#787878'),
    'Disabled_Text':       ('Disabled', '#787878'),
    'Disabled_ButtonText': ('Disabled', '#787878'),
    'Disabled_Highlight':  ('Disabled', '#505050'),
}

_ROLE_MAP = {
    'Window':          QtGui.QPalette.Window,
    'WindowText':      QtGui.QPalette.WindowText,
    'Base':            QtGui.QPalette.Base,
    'AlternateBase':   QtGui.QPalette.AlternateBase,
    'ToolTipBase':     QtGui.QPalette.ToolTipBase,
    'ToolTipText':     QtGui.QPalette.ToolTipText,
    'Text':            QtGui.QPalette.Text,
    'Button':          QtGui.QPalette.Button,
    'ButtonText':      QtGui.QPalette.ButtonText,
    'BrightText':      QtGui.QPalette.BrightText,
    'Highlight':       QtGui.QPalette.Highlight,
    'HighlightedText': QtGui.QPalette.HighlightedText,
    'Link':            QtGui.QPalette.Link,
    'LinkVisited':     QtGui.QPalette.LinkVisited,
}

GPI_QSS = """
QMainWindow, QDialog, QScrollArea { background: #353535; }
QScrollArea > QWidget > QWidget { background: #353535; }

QMenuBar {
    background: #2d2d2d;
    color: #dcdcdc;
    border-bottom: 1px solid #222;
    padding: 2px 4px;
    spacing: 2px;
}
QMenuBar::item { padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background: #2a82da; }

QMenu {
    background: #2a2a2a;
    color: #dcdcdc;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 4px 0;
}
QMenu::item { padding: 6px 28px 6px 14px; border-radius: 3px; }
QMenu::item:selected { background: #2a82da; }
QMenu::separator { height: 1px; background: #444; margin: 4px 10px; }
QMenu::indicator { width: 14px; height: 14px; }

QTabWidget::pane {
    border: 1px solid #444;
    border-radius: 4px;
    background: #2d2d2d;
    top: -1px;
}
QTabBar::tab {
    background: #2d2d2d;
    color: #aaaaaa;
    padding: 7px 20px;
    border: 1px solid transparent;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 70px;
}
QTabBar::tab:selected {
    background: #3c3c3c;
    color: #e0e0e0;
    border-color: #444;
    border-bottom-color: #3c3c3c;
}
QTabBar::tab:hover:!selected { background: #363636; color: #cccccc; }
QTabBar::close-button { subcontrol-position: right; }

QStatusBar {
    background: #2a2a2a;
    color: #909090;
    border-top: 1px solid #3a3a3a;
}
QStatusBar QLabel { color: #909090; }

QPushButton {
    background: #3c3c3c;
    color: #dcdcdc;
    border: 1px solid #555;
    border-radius: 5px;
    padding: 3px 10px;
    min-height: 18px;
}
QPushButton:hover   { background: #484848; border-color: #2a82da; }
QPushButton:pressed { background: #2d2d2d; }
QPushButton:default { border-color: #2a82da; border-width: 2px; }
QPushButton:disabled { color: #686868; border-color: #404040; background: #383838; }
QPushButton:checked         { background: #2a82da; color: #ffffff; border-color: #1a6ab0; font-weight: bold; }
QPushButton:checked:hover   { background: #3a92ea; border-color: #4a9eda; }
QPushButton:checked:pressed { background: #1a72ca; }

QLineEdit, QTextEdit, QPlainTextEdit {
    background: #252525;
    color: #dcdcdc;
    border: 1px solid #505050;
    border-radius: 4px;
    padding: 2px 6px;
    selection-background-color: #2a82da;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border-color: #2a82da; }

QComboBox {
    background: #3c3c3c;
    color: #dcdcdc;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 2px 6px;
    min-height: 18px;
}
QComboBox:hover { border-color: #2a82da; }
QComboBox::drop-down {
    width: 22px;
    border: none;
    border-left: 1px solid #555;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background: #484848;
}
QComboBox::drop-down:hover { background: #5a5a5a; }
QComboBox::down-arrow:disabled { color: #606060; }
QComboBox QAbstractItemView {
    background: #2a2a2a;
    color: #dcdcdc;
    selection-background-color: #2a82da;
    border: 1px solid #444;
    border-radius: 4px;
    outline: none;
}

QScrollBar:vertical {
    background: #252525; width: 9px; margin: 0; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #555; border-radius: 4px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #2a82da; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #252525; height: 9px; margin: 0; border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #555; border-radius: 4px; min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #2a82da; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QListWidget, QTreeWidget, QTableWidget {
    background: #252525;
    color: #dcdcdc;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    alternate-background-color: #2d2d2d;
    outline: none;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: #2a82da; color: white;
}
QListWidget::item:hover, QTreeWidget::item:hover { background: #363636; }

QCheckBox { color: #dcdcdc; spacing: 6px; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #555; border-radius: 3px; background: #3a3a3a;
}
QCheckBox::indicator:checked { background: #2a82da; border-color: #2a82da; }
QCheckBox::indicator:hover   { border-color: #2a82da; }

QGroupBox {
    color: #aaaaaa;
    border: 1px solid #424242;
    border-radius: 6px;
    margin-top: 12px;
    padding: 4px 4px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }

QSplitter::handle { background: #3a3a3a; }

QToolTip {
    background: #252525;
    color: #dcdcdc;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 4px 6px;
}

QDialogButtonBox QPushButton { min-width: 80px; }
QLabel { color: #dcdcdc; }

QSpinBox, QDoubleSpinBox {
    background: #252525;
    color: #dcdcdc;
    border: 1px solid #505050;
    border-radius: 4px;
    padding: 2px 5px;
    min-height: 18px;
    selection-background-color: #2a82da;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #2a82da; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 14px;
    border-left: 1px solid #505050;
    border-top-right-radius: 4px;
    background: #3c3c3c;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 14px;
    border-left: 1px solid #505050;
    border-bottom-right-radius: 4px;
    background: #3c3c3c;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: #484848; }

QSlider::groove:horizontal {
    height: 4px; background: #404040; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #2a82da; border: 1px solid #1a5fa0;
    width: 12px; height: 12px; margin: -4px 0; border-radius: 6px;
}
QSlider::sub-page:horizontal { background: #2a82da; border-radius: 2px; }
QSlider::groove:vertical {
    width: 4px; background: #404040; border-radius: 2px;
}
QSlider::handle:vertical {
    background: #2a82da; border: 1px solid #1a5fa0;
    width: 12px; height: 12px; margin: 0 -4px; border-radius: 6px;
}
QSlider::sub-page:vertical { background: #2a82da; border-radius: 2px; }

QRadioButton { color: #dcdcdc; spacing: 6px; }
QRadioButton::indicator {
    width: 13px; height: 13px;
    border: 1px solid #555; border-radius: 7px; background: #3a3a3a;
}
QRadioButton::indicator:checked { background: #2a82da; border-color: #2a82da; }
QRadioButton::indicator:hover   { border-color: #2a82da; }

QHeaderView::section {
    background: #2d2d2d; color: #aaaaaa;
    border: none;
    border-right: 1px solid #3d3d3d;
    border-bottom: 1px solid #3d3d3d;
    padding: 4px 8px; font-size: 11px;
}
QTableWidget::item { color: #dcdcdc; }
QTableWidget::item:selected { background: #2a82da; color: white; }
"""


def build_dark_palette():
    pal = QtGui.QPalette()
    for key, (group, hex_color) in _DARK_PALETTE.items():
        if key.startswith('Disabled_'):
            role = _ROLE_MAP[key[len('Disabled_'):]]
            pal.setColor(QtGui.QPalette.Disabled, role, QtGui.QColor(hex_color))
        else:
            pal.setColor(_ROLE_MAP[key], QtGui.QColor(hex_color))
    return pal


def win32_set_dark_titlebar(widget, dark=True):
    """Apply dark or light title bar on Windows 10 1903+ / Windows 11."""
    if _sys.platform != 'win32':
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        if hwnd == 0:
            return
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass


def _update_all_titlebars(dark):
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.isVisible():
            win32_set_dark_titlebar(w, dark)


def _apply_dark_theme(app):
    available = list(QtWidgets.QStyleFactory.keys())
    style_name = 'Fusion' if 'Fusion' in available else (available[0] if available else '')
    if style_name:
        app.setStyle(QtWidgets.QStyleFactory.create(style_name))
    app.setPalette(build_dark_palette())
    app.setStyleSheet(GPI_QSS)
    _update_all_titlebars(True)


def apply_classic_theme(app):
    """Standard Fusion light palette — no custom QSS."""
    available = list(QtWidgets.QStyleFactory.keys())
    style_name = 'Fusion' if 'Fusion' in available else (available[0] if available else '')
    if style_name:
        app.setStyle(QtWidgets.QStyleFactory.create(style_name))
    app.setPalette(app.style().standardPalette())
    app.setStyleSheet('')
    _update_all_titlebars(False)


def apply_gpi_theme(app, style_override=''):
    """Dispatch to 'Classic' (light Fusion) or 'Dark' (default) theme."""
    if style_override == 'Classic':
        apply_classic_theme(app)
    else:
        _apply_dark_theme(app)
