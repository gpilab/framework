from gpi import QtCore, QtGui, QtWidgets
from .config import Config

_SETTINGS_ORG = "GPI"
_SETTINGS_APP = "GPI"


def is_dark_theme():
    """True when the current QPalette window colour is dark (lightness < 128)."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QtGui.QPalette.Window).lightness() < 128


# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

def _dark_palette():
    p = QtGui.QPalette()
    c = QtGui.QColor
    p.setColor(QtGui.QPalette.Window,          c("#1e1e1e"))
    p.setColor(QtGui.QPalette.WindowText,      c("#cccccc"))
    p.setColor(QtGui.QPalette.Base,            c("#252526"))
    p.setColor(QtGui.QPalette.AlternateBase,   c("#2d2d30"))
    p.setColor(QtGui.QPalette.ToolTipBase,     c("#252526"))
    p.setColor(QtGui.QPalette.ToolTipText,     c("#cccccc"))
    p.setColor(QtGui.QPalette.Text,            c("#cccccc"))
    p.setColor(QtGui.QPalette.Button,          c("#3c3c3c"))
    p.setColor(QtGui.QPalette.ButtonText,      c("#cccccc"))
    p.setColor(QtGui.QPalette.BrightText,      c("#ffffff"))
    p.setColor(QtGui.QPalette.Link,            c("#4ec9b0"))
    p.setColor(QtGui.QPalette.Highlight,       c("#264f78"))
    p.setColor(QtGui.QPalette.HighlightedText, c("#ffffff"))
    p.setColor(QtGui.QPalette.Light,           c("#3c3c3c"))
    p.setColor(QtGui.QPalette.Midlight,        c("#2d2d30"))
    p.setColor(QtGui.QPalette.Dark,            c("#141414"))
    p.setColor(QtGui.QPalette.Mid,             c("#282828"))
    p.setColor(QtGui.QPalette.Shadow,          c("#000000"))
    for role in (QtGui.QPalette.WindowText, QtGui.QPalette.Text,
                 QtGui.QPalette.ButtonText):
        p.setColor(QtGui.QPalette.Disabled, role, c("#5a5a5a"))
    return p


_DARK_QSS = """
/* ── Base ───────────────────────────────────────────────────── */
QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
}
QDialog  { background-color: #1e1e1e; }
QFrame   { background-color: #1e1e1e; color: #cccccc; }
QLabel   { background: transparent;   color: #cccccc; }

/* ── Menu bar ──────────────────────────────────────────────── */
QMenuBar {
    background-color: #2d2d30;
    color: #cccccc;
    spacing: 2px;
}
QMenuBar::item { padding: 4px 10px; border-radius: 3px; background: transparent; }
QMenuBar::item:selected { background-color: #3c3c3c; }
QMenuBar::item:pressed  { background-color: #333333; }

QMenu {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #454545;
}
QMenu::item { padding: 5px 28px 5px 20px; background: transparent; }
QMenu::item:selected  { background-color: #094771; color: #ffffff; }
QMenu::separator { height: 1px; background: #3c3c3c; margin: 3px 0; }

/* ── Status bar ─────────────────────────────────────────────── */
QStatusBar { background-color: #007acc; color: #ffffff; }
QStatusBar::item { border: none; }

/* ── Tab bar ────────────────────────────────────────────────── */
QTabBar { background: transparent; }
QTabBar::tab {
    background-color: #2d2d30;
    color: #9d9d9d;
    padding: 6px 18px;
    border: none;
    border-right: 1px solid #1e1e1e;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    border-top: 2px solid #007acc;
}
QTabBar::tab:hover:!selected { background-color: #3c3c3c; color: #cccccc; }
QTabWidget::pane { border: none; background-color: #1e1e1e; }

/* ── Buttons (neutral dark — modern segmented-control style) ── */
QPushButton {
    background-color: #2d2d30;
    color: #cccccc;
    border: 1px solid #454545;
    padding: 4px 14px;
    border-radius: 3px;
    min-width: 60px;
}
QPushButton:hover            { background-color: #3c3c3c; border-color: #6a6a6a; }
QPushButton:pressed          { background-color: #252526; border-color: #454545; }
QPushButton:checked          { background-color: #094771; border-color: #007acc; color: #ffffff; }
QPushButton:checked:hover    { background-color: #1177bb; border-color: #007acc; }
QPushButton:disabled         { background-color: #252526; color: #555555; border-color: #333333; }
QPushButton:default          { border-color: #007acc; }

/* ── Text inputs ────────────────────────────────────────────── */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #2d2d30;
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    selection-background-color: #264f78;
    padding: 2px 4px;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #007acc;
}

/* ── Spin box ───────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background-color: #2d2d30;
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    padding: 1px 4px;
    selection-background-color: #264f78;
}
QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #007acc; }
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #3c3c3c;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #505050;
}

/* ── Slider ─────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    background-color: #3c3c3c;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #007acc;
    width: 12px; height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::sub-page:horizontal { background-color: #007acc; border-radius: 2px; }

/* ── Combo box ──────────────────────────────────────────────── */
QComboBox {
    background-color: #2d2d30;
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    padding: 3px 8px;
}
QComboBox:focus { border: 1px solid #007acc; }
QComboBox::drop-down { border: none; width: 20px; background: transparent; }
QComboBox QAbstractItemView {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #454545;
    selection-background-color: #094771;
    outline: none;
}

/* ── Group box (GPI widget rows use QGroupBox as base) ───────── */
QGroupBox {
    background-color: #252526;
    border: 1px solid #333333;
    border-radius: 4px;
    margin-top: 18px;
    padding: 6px 4px 4px 4px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    top: 2px;
    padding: 2px 6px;
    color: #9cdcfe;
    background-color: #252526;
    border-radius: 2px;
}

/* ── List widget ────────────────────────────────────────────── */
QListWidget {
    background-color: #252526;
    color: #cccccc;
    border: none;
    outline: none;
}
QListWidget::item { padding: 6px 12px; border-radius: 2px; background: transparent; }
QListWidget::item:selected { background-color: #094771; color: #ffffff; }
QListWidget::item:hover:!selected { background-color: #2a2d2e; }

/* ── Scroll bars ────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 10px; margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #424242;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background-color: #686868; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 10px; margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #424242;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background-color: #686868; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

/* ── Splitter ───────────────────────────────────────────────── */
QSplitter::handle { background-color: #2d2d30; }

/* ── Check box ──────────────────────────────────────────────── */
QCheckBox { color: #cccccc; spacing: 6px; background: transparent; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #5c5c5c;
    border-radius: 2px;
    background-color: #2d2d30;
}
QCheckBox::indicator:checked { background-color: #007acc; border-color: #007acc; }
QCheckBox::indicator:disabled { border-color: #3c3c3c; background-color: #252526; }

/* ── Radio button ───────────────────────────────────────────── */
QRadioButton { color: #cccccc; spacing: 6px; background: transparent; }
QRadioButton::indicator {
    width: 14px; height: 14px;
    border: 1px solid #5c5c5c;
    border-radius: 7px;
    background-color: #2d2d30;
}
QRadioButton::indicator:checked { background-color: #007acc; border-color: #007acc; }

/* ── Toolbar ────────────────────────────────────────────────── */
QToolBar { background-color: #2d2d30; border: none; spacing: 2px; }
QToolButton {
    background-color: transparent; color: #cccccc;
    border: none; padding: 4px; border-radius: 2px;
}
QToolButton:hover   { background-color: #3c3c3c; }
QToolButton:pressed { background-color: #252526; }

/* ── Scroll area ────────────────────────────────────────────── */
QScrollArea { background-color: #1e1e1e; border: none; }
QScrollArea > QWidget > QWidget { background-color: #1e1e1e; }

/* ── Tooltip ────────────────────────────────────────────────── */
QToolTip {
    background-color: #252526; color: #cccccc;
    border: 1px solid #454545; padding: 4px;
}
"""

# Built-in named themes
THEMES = {
    "System":        ("", None, None),          # style-name, palette, stylesheet
    "Fusion Light":  ("Fusion", None, None),
    "Dark":          ("Fusion", _dark_palette, _DARK_QSS),
}


def apply_theme(name: str, persist: bool = True):
    """Apply a named theme to the running QApplication."""
    app = QtWidgets.QApplication.instance()
    if name not in THEMES:
        name = "System"
    style_name, palette_fn, qss = THEMES[name]

    if style_name:
        app.setStyle(QtWidgets.QStyleFactory.create(style_name))
    else:
        app.setStyle(QtWidgets.QStyleFactory.create(
            QtWidgets.QStyleFactory.keys()[0]))

    if palette_fn is not None:
        app.setPalette(palette_fn())
    else:
        app.setPalette(app.style().standardPalette())

    app.setStyleSheet(qss if qss else "")

    if persist:
        QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue("theme", name)


def load_saved_theme():
    """Read and apply the theme + all other settings saved from the previous session."""
    qs = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    # Theme
    name = qs.value("theme", "System")
    apply_theme(name, persist=False)

    # Paths & general — push into Config if values were previously saved
    if qs.contains("lib_paths"):
        raw = qs.value("lib_paths", "")
        Config._c_gpi_lib_path = [p.strip() for p in raw.splitlines() if p.strip()]
    if qs.contains("net_dir"):
        Config._c_networkDir = qs.value("net_dir")
    if qs.contains("data_dir"):
        Config._c_dataDir = qs.value("data_dir")
    if qs.contains("import_check"):
        Config._g_import_check = qs.value("import_check", type=bool)
    if qs.contains("follow_cwd"):
        Config._c_gpi_follow_cwd = qs.value("follow_cwd", type=bool)


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPI Settings")
        self.resize(750, 500)
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 12)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setHandleWidth(1)

        # Left category list
        self._cat = QtWidgets.QListWidget()
        self._cat.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._cat.setFixedWidth(155)
        self._cat.setSpacing(2)
        self._cat.addItems(["Appearance", "Paths", "General"])
        self._cat.currentRowChanged.connect(self._on_cat_changed)

        # Right stacked pages
        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._page_appearance())
        self._stack.addWidget(self._page_paths())
        self._stack.addWidget(self._page_general())

        splitter.addWidget(self._cat)
        splitter.addWidget(self._stack)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter)

        # Separator
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        root.addWidget(sep)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setContentsMargins(12, 0, 12, 0)
        btn_row.addStretch()
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        apply_btn = QtWidgets.QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        for b in (ok_btn, cancel_btn, apply_btn):
            b.setMinimumWidth(80)
            btn_row.addWidget(b)
        root.addLayout(btn_row)

        self._cat.setCurrentRow(0)

    def _on_cat_changed(self, row):
        self._stack.setCurrentIndex(row)

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def _page_appearance(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        lay.setAlignment(QtCore.Qt.AlignTop)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)

        lay.addWidget(self._section("Theme"))

        desc = QtWidgets.QLabel(
            "Choose the overall look of the GPI interface. "
            "\"Dark\" uses a VS Code-inspired dark palette.")
        desc.setWordWrap(True)
        desc.setEnabled(False)
        lay.addWidget(desc)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 6, 0, 0)
        self._theme_combo = QtWidgets.QComboBox()
        self._theme_combo.addItems(list(THEMES.keys()))
        self._theme_combo.currentTextChanged.connect(self._preview_theme)
        form.addRow("Theme:", self._theme_combo)
        lay.addLayout(form)

        lay.addSpacing(24)
        lay.addWidget(self._section("Display"))
        hidpi = QtWidgets.QLabel(
            "HiDPI / Retina scaling is always enabled (set at launch via "
            "QApplication attributes). The rounding policy is PassThrough "
            "so the canvas stays sharp at 125 %, 150 %, 200 %, etc.")
        hidpi.setWordWrap(True)
        hidpi.setEnabled(False)
        lay.addWidget(hidpi)

        lay.addStretch()
        return page

    def _page_paths(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        lay.setAlignment(QtCore.Qt.AlignTop)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)

        lay.addWidget(self._section("Node Library Paths"))
        lay.addWidget(QtWidgets.QLabel(
            "Directories scanned for GPI nodes (one path per line):"))
        self._lib_paths = QtWidgets.QPlainTextEdit()
        self._lib_paths.setMaximumHeight(110)
        self._lib_paths.setPlaceholderText(
            "e.g.  C:/Users/me/gpi_nodes")
        lay.addWidget(self._lib_paths)

        lay.addSpacing(16)
        lay.addWidget(self._section("Network Directory"))
        self._net_dir = self._dir_row(lay)

        lay.addSpacing(16)
        lay.addWidget(self._section("Data Directory"))
        self._data_dir = self._dir_row(lay)

        lay.addStretch()
        return page

    def _page_general(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        lay.setAlignment(QtCore.Qt.AlignTop)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)

        lay.addWidget(self._section("Startup"))
        self._import_check = QtWidgets.QCheckBox(
            "Check node imports on load")
        lay.addWidget(self._import_check)

        lay.addSpacing(20)
        lay.addWidget(self._section("Workspace"))
        self._follow_cwd = QtWidgets.QCheckBox(
            "Follow current working directory (GPI_FOLLOW_CWD)")
        lay.addWidget(self._follow_cwd)

        lay.addStretch()
        return page

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _section(self, title):
        return QtWidgets.QLabel(f"<b>{title}</b>")

    def _dir_row(self, parent_layout):
        row = QtWidgets.QHBoxLayout()
        edit = QtWidgets.QLineEdit()
        browse = QtWidgets.QPushButton("Browse…")
        browse.clicked.connect(lambda: self._pick_dir(edit))
        row.addWidget(edit)
        row.addWidget(browse)
        parent_layout.addLayout(row)
        return edit

    def _pick_dir(self, line_edit):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Directory", line_edit.text())
        if d:
            line_edit.setText(d)

    def _preview_theme(self, name):
        apply_theme(name)

    # ------------------------------------------------------------------
    # Load / Apply
    # ------------------------------------------------------------------

    @staticmethod
    def _qs():
        return QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    def _load(self):
        qs = self._qs()

        # Theme — read from QSettings, fall back to detecting the running style
        saved_theme = qs.value("theme", None)
        if saved_theme and saved_theme in THEMES:
            current = saved_theme
        elif is_dark_theme():
            current = "Dark"
        elif QtWidgets.QApplication.instance().style().objectName().lower() == "fusion":
            current = "Fusion Light"
        else:
            current = "System"
        idx = self._theme_combo.findText(current)
        self._theme_combo.setCurrentIndex(max(idx, 0))
        self._initial_theme = self._theme_combo.currentText()

        # Paths — QSettings overrides Config defaults
        self._lib_paths.setPlainText(
            qs.value("lib_paths", '\n'.join(Config.GPI_LIBRARY_PATH)))
        self._net_dir.setText(
            qs.value("net_dir", Config.GPI_NET_PATH))
        self._data_dir.setText(
            qs.value("data_dir", Config.GPI_DATA_PATH))

        # General
        self._import_check.setChecked(
            qs.value("import_check", Config.IMPORT_CHECK, type=bool))
        self._follow_cwd.setChecked(
            qs.value("follow_cwd", Config.GPI_FOLLOW_CWD, type=bool))

    def _apply(self):
        qs = self._qs()

        # Theme
        theme_name = self._theme_combo.currentText()
        apply_theme(theme_name)          # also saves "theme" key via persist=True
        self._initial_theme = theme_name

        # Paths
        paths = [p.strip() for p in
                 self._lib_paths.toPlainText().splitlines() if p.strip()]
        Config._c_gpi_lib_path = paths
        Config._c_networkDir = self._net_dir.text()
        Config._c_dataDir = self._data_dir.text()
        qs.setValue("lib_paths", '\n'.join(paths))
        qs.setValue("net_dir", self._net_dir.text())
        qs.setValue("data_dir", self._data_dir.text())

        # General
        Config._g_import_check = self._import_check.isChecked()
        Config._c_gpi_follow_cwd = self._follow_cwd.isChecked()
        qs.setValue("import_check", self._import_check.isChecked())
        qs.setValue("follow_cwd", self._follow_cwd.isChecked())

    def _on_ok(self):
        self._apply()
        self.accept()

    def reject(self):
        # Restore theme if user cancels after previewing
        if hasattr(self, '_initial_theme'):
            apply_theme(self._initial_theme)
        super().reject()
