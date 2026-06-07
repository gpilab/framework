import os
import sys
from gpi import QtCore, QtGui, QtWidgets
from .config import Config

_SETTINGS_ORG = "GPI"
_SETTINGS_APP = "GPI"


# ---------------------------------------------------------------------------
# Windows dark title bar (DWM)
# ---------------------------------------------------------------------------

def _dwm_set_dark(hwnd, dark: bool):
    """Toggle Windows 10/11 immersive dark mode on a native window handle."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        val = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            int(hwnd), DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def _apply_dark_titlebar_all(dark: bool):
    """Apply dark/light title bar to every existing top-level Qt window."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        hwnd = w.winId()
        if hwnd:
            _dwm_set_dark(hwnd, dark)


class _TitleBarFilter(QtCore.QObject):
    """QApplication event filter — applies dark title bar whenever a top-level
    window is shown (covers node panels and dialogs opened after startup)."""

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Show:
            if isinstance(obj, QtWidgets.QWidget) and obj.isWindow():
                hwnd = obj.winId()
                if hwnd:
                    _dwm_set_dark(hwnd, is_dark_theme())
        return False


_titlebar_filter: "_TitleBarFilter | None" = None


def _ensure_titlebar_filter():
    global _titlebar_filter
    app = QtWidgets.QApplication.instance()
    if app and _titlebar_filter is None:
        _titlebar_filter = _TitleBarFilter()
        app.installEventFilter(_titlebar_filter)


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


_GFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphics')
_CHECKMARK_URL = os.path.join(_GFX_DIR, 'checkmark.svg').replace('\\', '/')

_DARK_QSS_TEMPLATE = """
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
QCheckBox::indicator:checked { background-color: #007acc; border-color: #007acc; image: url(CHECKMARK_URL); }
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

_DARK_QSS = _DARK_QSS_TEMPLATE.replace('CHECKMARK_URL', _CHECKMARK_URL)

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

    dark = (name == "Dark")
    _ensure_titlebar_filter()       # start watching new windows
    _apply_dark_titlebar_all(dark)  # fix already-open windows

    if persist:
        QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue("theme", name)


def load_saved_theme():
    """Read and apply the theme + all other settings saved from the previous session."""
    qs = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    # Theme — apply_theme also installs the title-bar filter
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
# Association edit dialog
# ---------------------------------------------------------------------------

class _AssocEditDialog(QtWidgets.QDialog):
    """Add or edit a single file-type → node association."""

    def __init__(self, parent=None, ext='', node='', wdg='File Browser',
                 node_catalog=None):
        super().__init__(parent)
        self.setWindowTitle("File Association")
        self.setMinimumWidth(500)
        self._node_catalog = node_catalog

        form = QtWidgets.QFormLayout()

        # Extension
        self._ext_edit = QtWidgets.QLineEdit(ext)
        self._ext_edit.setPlaceholderText(".png")
        form.addRow("File extension:", self._ext_edit)

        # Node — text field + Browse button
        node_row = QtWidgets.QHBoxLayout()
        self._node_edit = QtWidgets.QLineEdit(node)
        self._node_edit.setPlaceholderText("e.g. gpi_core.fileIO.ReadImage")
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.clicked.connect(self._pick_node)
        node_row.addWidget(self._node_edit)
        node_row.addWidget(browse_btn)
        form.addRow("Node:", node_row)

        # Widget name
        self._wdg_edit = QtWidgets.QLineEdit(wdg)
        self._wdg_edit.setPlaceholderText("File Browser")
        form.addRow("Widget name:", self._wdg_edit)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(form)
        vbox.addSpacing(8)
        vbox.addWidget(btns)
        self.setLayout(vbox)

    def _pick_node(self):
        dlg = _NodePickerDialog(self, node_catalog=self._node_catalog)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            key, name = dlg.selected()
            self._node_edit.setText(key)

    def values(self):
        ext = self._ext_edit.text().strip()
        if ext and not ext.startswith('.'):
            ext = '.' + ext
        return (ext.lower(),
                self._node_edit.text().strip(),
                self._wdg_edit.text().strip() or 'File Browser')


class _NodePickerDialog(QtWidgets.QDialog):
    """Searchable list of all nodes loaded in the current GPI library."""

    def __init__(self, parent=None, node_catalog=None):
        super().__init__(parent)
        self.setWindowTitle("Pick Node")
        self.resize(480, 400)
        self._selected_key = ''
        self._selected_name = ''

        # Search bar
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Type to filter nodes…")
        self._search.textChanged.connect(self._filter)

        # Node list:  "name   (library.sub)"
        self._list = QtWidgets.QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemDoubleClicked.connect(self._on_double_click)

        # Populate from catalog
        self._entries = []  # list of (key, display_label)
        if node_catalog is not None:
            for item in sorted(node_catalog.values(), key=lambda x: x.name.lower()):
                key = item._id  # e.g. "gpi_core.fileIO.ReadImage"
                label = f"{item.name}    ({item.third}.{item.second})"
                self._entries.append((key, label))
        else:
            self._entries.append(('', '(No nodes loaded — open GPI first)'))
        self._populate(self._entries)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self._search)
        vbox.addWidget(self._list)
        vbox.addWidget(btns)
        self.setLayout(vbox)

    def _populate(self, entries):
        self._list.clear()
        for key, label in entries:
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, key)
            self._list.addItem(item)

    def _filter(self, text):
        text = text.lower()
        if not text:
            self._populate(self._entries)
            return
        filtered = [(k, l) for k, l in self._entries
                    if text in k.lower() or text in l.lower()]
        self._populate(filtered)

    def _on_double_click(self, item):
        self._select_item(item)
        self.accept()

    def _on_ok(self):
        items = self._list.selectedItems()
        if items:
            self._select_item(items[0])
        self.accept()

    def _select_item(self, item):
        self._selected_key = item.data(QtCore.Qt.UserRole) or ''
        self._selected_name = item.text()

    def selected(self):
        return self._selected_key, self._selected_name


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QtWidgets.QDialog):

    def __init__(self, parent=None, node_catalog=None):
        super().__init__(parent)
        self.setWindowTitle("GPI Settings")
        self.resize(800, 560)
        self._node_catalog = node_catalog  # Catalog of NodeCatalogItem objects (may be None)
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

        self._cat = QtWidgets.QListWidget()
        self._cat.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._cat.setFixedWidth(155)
        self._cat.setSpacing(2)
        self._cat.addItems(["Appearance", "Paths", "General",
                            "Build", "Associations"])
        self._cat.currentRowChanged.connect(self._on_cat_changed)

        self._stack = QtWidgets.QStackedWidget()
        self._stack.addWidget(self._page_appearance())
        self._stack.addWidget(self._page_paths())
        self._stack.addWidget(self._page_general())
        self._stack.addWidget(self._page_build())
        self._stack.addWidget(self._page_associations())

        splitter.addWidget(self._cat)
        splitter.addWidget(self._stack)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        root.addWidget(sep)

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
        page, lay = self._page_base()
        lay.addWidget(self._section("Theme"))
        desc = QtWidgets.QLabel(
            "Choose the overall look of GPI.  "
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
            "HiDPI / Retina scaling is enabled at launch (PassThrough rounding "
            "policy). No restart needed when switching themes.")
        hidpi.setWordWrap(True)
        hidpi.setEnabled(False)
        lay.addWidget(hidpi)
        lay.addStretch()
        return page

    def _page_paths(self):
        page, lay = self._page_base()
        lay.addWidget(self._section("Node Library Paths  (LIB_DIRS)"))
        lay.addWidget(QtWidgets.QLabel("One directory per line. GPI scans these for nodes."))
        self._lib_paths = QtWidgets.QPlainTextEdit()
        self._lib_paths.setMaximumHeight(100)
        self._lib_paths.setPlaceholderText("e.g.  C:/Users/me/gpi_nodes")
        lay.addWidget(self._lib_paths)

        lay.addSpacing(14)
        lay.addWidget(self._section("Network Directory  (NET_DIR)"))
        lay.addWidget(QtWidgets.QLabel("Default directory for network (.net) file dialogs."))
        self._net_dir = self._dir_row(lay)

        lay.addSpacing(14)
        lay.addWidget(self._section("Data Directory  (DATA_DIR)"))
        lay.addWidget(QtWidgets.QLabel("Default directory for data file dialogs."))
        self._data_dir = self._dir_row(lay)

        lay.addSpacing(14)
        lay.addWidget(self._section("Workspace"))
        self._follow_cwd = QtWidgets.QCheckBox(
            "Follow current working directory (FOLLOW_CWD)  —  "
            "file dialogs track wherever the user last navigated")
        lay.addWidget(self._follow_cwd)
        lay.addStretch()
        return page

    def _page_general(self):
        page, lay = self._page_base()
        lay.addWidget(self._section("Startup"))
        self._import_check = QtWidgets.QCheckBox(
            "Check node imports on load  (IMPORT_CHECK)  —  "
            "disable to speed up library scanning")
        lay.addWidget(self._import_check)
        lay.addStretch()
        return page

    def _page_build(self):
        page, lay = self._page_base()
        lay.addWidget(self._section("Extra Libraries  (LIBS)"))
        lay.addWidget(QtWidgets.QLabel("Library names to pass to the compiler (one per line, e.g. blas):"))
        self._make_libs = self._code_edit(lay, 60)

        lay.addSpacing(12)
        lay.addWidget(self._section("Library Search Paths  (MAKE LIB_DIRS)"))
        lay.addWidget(QtWidgets.QLabel("Directories containing the above libraries (one per line):"))
        self._make_lib_dirs = self._multidir_edit(lay, 60)

        lay.addSpacing(12)
        lay.addWidget(self._section("Include Paths  (INC_DIRS)"))
        lay.addWidget(QtWidgets.QLabel("Header search paths for C++ node compilation (one per line):"))
        self._make_inc_dirs = self._multidir_edit(lay, 60)

        lay.addSpacing(12)
        lay.addWidget(self._section("Compiler Flags  (CFLAGS)"))
        lay.addWidget(QtWidgets.QLabel("Extra flags passed to g++ (one per line, e.g. -D_MY_MACRO_=1):"))
        self._make_cflags = self._code_edit(lay, 60)
        lay.addStretch()
        return page

    def _page_associations(self):
        page, lay = self._page_base()
        lay.addWidget(self._section("File-type → Node Associations  (BIND_N)"))
        lay.addWidget(QtWidgets.QLabel(
            "When a file of a given extension is dropped onto the canvas, "
            "GPI opens it in the associated node automatically."))

        self._assoc_table = QtWidgets.QTableWidget(0, 3)
        self._assoc_table.setHorizontalHeaderLabels(["Extension", "Node", "Widget"])
        self._assoc_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self._assoc_table.horizontalHeader().setStretchLastSection(False)
        self._assoc_table.horizontalHeader().resizeSection(0, 90)
        self._assoc_table.horizontalHeader().resizeSection(2, 150)
        self._assoc_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._assoc_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._assoc_table.setAlternatingRowColors(True)
        self._assoc_table.verticalHeader().setVisible(False)
        self._assoc_table.doubleClicked.connect(self._assoc_edit)
        lay.addWidget(self._assoc_table)

        btn_row = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add…")
        add_btn.clicked.connect(self._assoc_add)
        edit_btn = QtWidgets.QPushButton("Edit…")
        edit_btn.clicked.connect(self._assoc_edit)
        rm_btn = QtWidgets.QPushButton("Remove")
        rm_btn.clicked.connect(self._assoc_remove)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        lay.addStretch()
        return page

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _page_base(self):
        page = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(page)
        lay.setAlignment(QtCore.Qt.AlignTop)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(8)
        return page, lay

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

    def _multidir_edit(self, parent_layout, height):
        """Multi-line edit with a Browse button that appends a directory."""
        row = QtWidgets.QHBoxLayout()
        edit = QtWidgets.QPlainTextEdit()
        edit.setMaximumHeight(height)
        browse = QtWidgets.QPushButton("Add…")
        browse.setMaximumWidth(60)
        browse.clicked.connect(lambda: self._append_dir(edit))
        row.addWidget(edit)
        row.addWidget(browse)
        parent_layout.addLayout(row)
        return edit

    def _code_edit(self, parent_layout, height):
        edit = QtWidgets.QPlainTextEdit()
        edit.setMaximumHeight(height)
        parent_layout.addWidget(edit)
        return edit

    def _pick_dir(self, line_edit):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Directory", line_edit.text())
        if d:
            line_edit.setText(os.path.normpath(d))

    def _append_dir(self, plain_edit):
        cur = plain_edit.toPlainText().strip()
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory", cur)
        if d:
            lines = [l for l in cur.splitlines() if l.strip()]
            lines.append(os.path.normpath(d))
            plain_edit.setPlainText('\n'.join(lines))

    def _preview_theme(self, name):
        apply_theme(name)

    # -- Associations helpers --

    def _assoc_add(self):
        dlg = _AssocEditDialog(self, node_catalog=self._node_catalog)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            ext, node, wdg = dlg.values()
            row = self._assoc_table.rowCount()
            self._assoc_table.insertRow(row)
            for col, val in enumerate([ext, node, wdg]):
                self._assoc_table.setItem(row, col, QtWidgets.QTableWidgetItem(val))

    def _assoc_edit(self):
        rows = sorted({i.row() for i in self._assoc_table.selectedItems()})
        if not rows:
            return
        r = rows[0]
        ext  = (self._assoc_table.item(r, 0) or QtWidgets.QTableWidgetItem()).text()
        node = (self._assoc_table.item(r, 1) or QtWidgets.QTableWidgetItem()).text()
        wdg  = (self._assoc_table.item(r, 2) or QtWidgets.QTableWidgetItem()).text()
        dlg = _AssocEditDialog(self, ext=ext, node=node, wdg=wdg,
                               node_catalog=self._node_catalog)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            ext, node, wdg = dlg.values()
            for col, val in enumerate([ext, node, wdg]):
                self._assoc_table.setItem(r, col, QtWidgets.QTableWidgetItem(val))

    def _assoc_remove(self):
        rows = sorted({i.row() for i in self._assoc_table.selectedItems()},
                      reverse=True)
        for r in rows:
            self._assoc_table.removeRow(r)

    def _assoc_rows(self):
        out = []
        for r in range(self._assoc_table.rowCount()):
            ext  = (self._assoc_table.item(r, 0) or QtWidgets.QTableWidgetItem()).text().strip()
            node = (self._assoc_table.item(r, 1) or QtWidgets.QTableWidgetItem()).text().strip()
            wdg  = (self._assoc_table.item(r, 2) or QtWidgets.QTableWidgetItem()).text().strip()
            if ext and node and wdg:
                out.append((ext, node, wdg))
        return out

    # ------------------------------------------------------------------
    # Load / Apply
    # ------------------------------------------------------------------

    @staticmethod
    def _qs():
        return QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    def _load(self):
        # -- Theme --
        qs = self._qs()
        saved_theme = qs.value("theme", None)
        if saved_theme and saved_theme in THEMES:
            current = saved_theme
        elif is_dark_theme():
            current = "Dark"
        elif QtWidgets.QApplication.instance().style().objectName().lower() == "fusion":
            current = "Fusion Light"
        else:
            current = "System"
        self._theme_combo.setCurrentIndex(max(self._theme_combo.findText(current), 0))
        self._initial_theme = self._theme_combo.currentText()

        # -- Paths --
        self._lib_paths.setPlainText('\n'.join(
            os.path.normpath(p) for p in Config.GPI_LIBRARY_PATH))
        self._net_dir.setText(os.path.normpath(Config.GPI_NET_PATH))
        self._data_dir.setText(os.path.normpath(Config.GPI_DATA_PATH))
        self._follow_cwd.setChecked(Config.GPI_FOLLOW_CWD)

        # -- General --
        self._import_check.setChecked(Config.IMPORT_CHECK)

        # -- Build --
        self._make_libs.setPlainText('\n'.join(Config.MAKE_LIBS))
        self._make_lib_dirs.setPlainText('\n'.join(Config.MAKE_LIB_DIRS))
        self._make_inc_dirs.setPlainText('\n'.join(Config.MAKE_INC_DIRS))
        self._make_cflags.setPlainText('\n'.join(Config.MAKE_CFLAGS))

        # -- Associations --
        from .associate import Bindings
        self._assoc_table.setRowCount(0)
        for item in Bindings.values():
            ext, node, wdg = item.asTuple()
            r = self._assoc_table.rowCount()
            self._assoc_table.insertRow(r)
            for col, val in enumerate([ext, node, wdg]):
                self._assoc_table.setItem(r, col, QtWidgets.QTableWidgetItem(val))

    def _apply(self):
        # -- Theme --
        theme_name = self._theme_combo.currentText()
        apply_theme(theme_name)
        self._initial_theme = theme_name

        def _lines(edit):
            return [l.strip() for l in edit.toPlainText().splitlines() if l.strip()]

        def _norm_lines(edit):
            return [os.path.normpath(l.strip())
                    for l in edit.toPlainText().splitlines() if l.strip()]

        # -- Paths --
        Config._c_gpi_lib_path  = _norm_lines(self._lib_paths)
        Config._c_networkDir    = os.path.normpath(self._net_dir.text()) if self._net_dir.text().strip() else ''
        Config._c_dataDir       = os.path.normpath(self._data_dir.text()) if self._data_dir.text().strip() else ''
        Config._c_gpi_follow_cwd = self._follow_cwd.isChecked()

        # -- General --
        Config._g_import_check  = self._import_check.isChecked()

        # -- Build --
        Config._make_libs      = _lines(self._make_libs)
        Config._make_lib_dirs  = _lines(self._make_lib_dirs)
        Config._make_inc_dirs  = _lines(self._make_inc_dirs)
        Config._make_cflags    = _lines(self._make_cflags)

        # -- Associations --
        from .associate import Bindings, BindCatalogItem
        Bindings._db.clear()
        for t in self._assoc_rows():
            Bindings.append(BindCatalogItem(t))

        # Persist everything via Config (single source of truth)
        Config.saveToQSettings()

    def _on_ok(self):
        self._apply()
        self.accept()

    def reject(self):
        if hasattr(self, '_initial_theme'):
            apply_theme(self._initial_theme)
        super().reject()
