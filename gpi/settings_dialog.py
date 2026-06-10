import os
from gpi import QtCore, QtGui, QtWidgets, Signal
from .associate import Bindings, BindCatalogItem
from .config import Config
from .logger import manager
from .theme import apply_gpi_theme, win32_set_dark_titlebar

log = manager.getLogger(__name__)


class SettingsDialog(QtWidgets.QDialog):
    settings_applied = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPI Settings")
        self.setMinimumSize(580, 400)
        self.resize(640, 460)

        self._initial_style = Config.APPEARANCE_STYLE
        self._accepted = False

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.addTab(self._create_general_tab(), "General")
        self.tabWidget.addTab(self._create_appearance_tab(), "Appearance")
        self.tabWidget.addTab(self._create_paths_tab(), "Paths")
        self.tabWidget.addTab(self._create_build_tab(), "Build")
        self.tabWidget.addTab(self._create_associations_tab(), "Associations")

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok |
            QtWidgets.QDialogButtonBox.Cancel |
            QtWidgets.QDialogButtonBox.Apply
        )
        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self._on_reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self._apply)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    # ── General ──────────────────────────────────────────────────────────────

    def _create_general_tab(self):
        widget = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(20, 20, 20, 10)
        outer.setSpacing(14)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)

        self.importCheckBox = QtWidgets.QCheckBox()
        form.addRow("Import check on startup:", self.importCheckBox)

        note = QtWidgets.QLabel(
            "When enabled, GPI verifies each node can be imported before adding it to the "
            "library. Disabling this makes GPI start faster but may include broken nodes."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")

        outer.addLayout(form)
        outer.addWidget(note)
        outer.addStretch()
        widget.setLayout(outer)
        return widget

    # ── Appearance ───────────────────────────────────────────────────────────

    def _create_appearance_tab(self):
        widget = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(20, 20, 20, 10)
        outer.setSpacing(14)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)

        self.themeCombo = QtWidgets.QComboBox()
        self.themeCombo.addItems(['Dark', 'Classic'])
        self.themeCombo.currentTextChanged.connect(self._preview_theme)
        form.addRow("Theme:", self.themeCombo)

        note = QtWidgets.QLabel(
            "Dark: modern dark Fusion theme (default).\n"
            "Classic: light standard Fusion appearance.\n"
            "Changes are previewed live. Click OK or Apply to save."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")

        outer.addLayout(form)
        outer.addWidget(note)
        outer.addStretch()
        widget.setLayout(outer)
        return widget

    # ── Paths ─────────────────────────────────────────────────────────────────

    def _create_paths_tab(self):
        widget = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(20, 20, 20, 10)
        outer.setSpacing(10)

        libLabel = QtWidgets.QLabel("Node Library Paths:")
        libLabel.setStyleSheet("font-weight: bold;")
        outer.addWidget(libLabel)

        libRow = QtWidgets.QHBoxLayout()
        self.libPathList = QtWidgets.QListWidget()
        self.libPathList.setMinimumHeight(110)
        libRow.addWidget(self.libPathList)

        libBtns = QtWidgets.QVBoxLayout()
        addLibBtn = QtWidgets.QPushButton("Add...")
        addLibBtn.clicked.connect(self._add_lib_path)
        self.removeLibBtn = QtWidgets.QPushButton("Remove")
        self.removeLibBtn.clicked.connect(self._remove_lib_path)
        libBtns.addWidget(addLibBtn)
        libBtns.addWidget(self.removeLibBtn)
        libBtns.addStretch()
        libRow.addLayout(libBtns)
        outer.addLayout(libRow)

        outer.addSpacing(8)

        self.followCwdCheck = QtWidgets.QCheckBox(
            "File browsers follow the current working directory"
        )
        outer.addWidget(self.followCwdCheck)

        outer.addSpacing(4)

        form = QtWidgets.QFormLayout()
        form.setSpacing(8)

        self.netDirEdit = QtWidgets.QLineEdit()
        netRow = self._dir_row(self.netDirEdit)
        form.addRow("Network file directory:", netRow)

        self.dataDirEdit = QtWidgets.QLineEdit()
        dataRow = self._dir_row(self.dataDirEdit)
        form.addRow("Data file directory:", dataRow)

        outer.addLayout(form)
        outer.addStretch()
        widget.setLayout(outer)
        return widget

    def _dir_row(self, line_edit):
        row = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        btn = QtWidgets.QPushButton("Browse...")
        btn.clicked.connect(lambda: self._browse_dir(line_edit))
        h.addWidget(line_edit)
        h.addWidget(btn)
        return row

    # ── Build ─────────────────────────────────────────────────────────────────

    def _create_build_tab(self):
        widget = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(20, 20, 20, 10)
        outer.setSpacing(14)

        sep = os.pathsep
        note = QtWidgets.QLabel(
            "These options are passed to the compiler when building GPI node C++ extensions.\n"
            f"Use '{sep}' as a separator for multiple entries."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        outer.addWidget(note)

        form = QtWidgets.QFormLayout()
        form.setSpacing(10)

        self.makeLibsEdit = QtWidgets.QLineEdit()
        self.makeLibsEdit.setPlaceholderText(f"e.g. blas{sep}lapack")
        form.addRow("Libraries (-l):", self.makeLibsEdit)

        self.makeLibDirsEdit = QtWidgets.QLineEdit()
        self.makeLibDirsEdit.setPlaceholderText(f"e.g. /usr/lib{sep}/opt/lapack/lib")
        form.addRow("Library directories (-L):", self.makeLibDirsEdit)

        self.makeIncDirsEdit = QtWidgets.QLineEdit()
        self.makeIncDirsEdit.setPlaceholderText(f"e.g. /usr/include{sep}/opt/lapack/include")
        form.addRow("Include directories (-I):", self.makeIncDirsEdit)

        self.makeCflagsEdit = QtWidgets.QLineEdit()
        self.makeCflagsEdit.setPlaceholderText(f"e.g. -D_MY_MACRO_=1{sep}-D_ANOTHER_")
        form.addRow("Compiler flags (-D / other):", self.makeCflagsEdit)

        outer.addLayout(form)
        outer.addStretch()
        widget.setLayout(outer)
        return widget

    # ── Associations ──────────────────────────────────────────────────────────

    def _create_associations_tab(self):
        widget = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(20, 16, 20, 10)
        outer.setSpacing(10)

        note = QtWidgets.QLabel(
            "Map file extensions to nodes for drag-and-drop onto the canvas. "
            "Extension must include the dot (e.g. .npy). "
            "Node name uses the dotted module path (e.g. gpi_core.fileIO.ReadNPY)."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        outer.addWidget(note)

        self.assocTable = QtWidgets.QTableWidget(0, 3)
        self.assocTable.setHorizontalHeaderLabels(["Extension", "Node Name", "Widget Name"])
        hdr = self.assocTable.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.assocTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.assocTable.setAlternatingRowColors(True)
        self.assocTable.setMinimumHeight(200)
        outer.addWidget(self.assocTable)

        btnRow = QtWidgets.QHBoxLayout()
        addBtn = QtWidgets.QPushButton("Add Row")
        addBtn.clicked.connect(self._add_assoc_row)
        self.removeAssocBtn = QtWidgets.QPushButton("Remove Selected")
        self.removeAssocBtn.clicked.connect(self._remove_assoc_row)
        btnRow.addWidget(addBtn)
        btnRow.addWidget(self.removeAssocBtn)
        btnRow.addStretch()
        outer.addLayout(btnRow)

        widget.setLayout(outer)
        return widget

    # ── Load / Save ──────────────────────────────────────────────────────────

    def _load_settings(self):
        # General
        self.importCheckBox.setChecked(Config.IMPORT_CHECK)

        # Appearance
        theme = Config.APPEARANCE_STYLE or 'Dark'
        idx = self.themeCombo.findText(theme)
        self.themeCombo.setCurrentIndex(idx if idx >= 0 else 0)

        # Paths
        self.libPathList.clear()
        for p in Config.GPI_LIBRARY_PATH:
            self.libPathList.addItem(p)
        self.followCwdCheck.setChecked(Config.GPI_FOLLOW_CWD)
        self.netDirEdit.setText(Config.GPI_NET_PATH)
        self.dataDirEdit.setText(Config.GPI_DATA_PATH)

        # Build
        self.makeLibsEdit.setText(os.pathsep.join(Config.MAKE_LIBS))
        self.makeLibDirsEdit.setText(os.pathsep.join(Config.MAKE_LIB_DIRS))
        self.makeIncDirsEdit.setText(os.pathsep.join(Config.MAKE_INC_DIRS))
        self.makeCflagsEdit.setText(os.pathsep.join(Config.MAKE_CFLAGS))

        # Associations
        self._reload_assoc_table()

    def _reload_assoc_table(self):
        self.assocTable.setRowCount(0)
        for key in sorted(Bindings.keys()):
            ext, node, wdg = Bindings.get(key).asTuple()
            row = self.assocTable.rowCount()
            self.assocTable.insertRow(row)
            self.assocTable.setItem(row, 0, QtWidgets.QTableWidgetItem(ext))
            self.assocTable.setItem(row, 1, QtWidgets.QTableWidgetItem(node))
            self.assocTable.setItem(row, 2, QtWidgets.QTableWidgetItem(wdg))

    def _write_to_config(self):
        # General
        Config._g_import_check = self.importCheckBox.isChecked()

        # Appearance
        Config._appearance_style = self.themeCombo.currentText()

        # Paths
        Config._c_gpi_lib_path = [
            self.libPathList.item(i).text()
            for i in range(self.libPathList.count())
        ]
        Config._c_gpi_follow_cwd = self.followCwdCheck.isChecked()
        Config._c_networkDir = self.netDirEdit.text()
        Config._c_dataDir = self.dataDirEdit.text()

        # Build
        def _split(text):
            return [p.strip() for p in text.split(os.pathsep) if p.strip()]

        Config._make_libs = _split(self.makeLibsEdit.text())
        Config._make_lib_dirs = _split(self.makeLibDirsEdit.text())
        Config._make_inc_dirs = _split(self.makeIncDirsEdit.text())
        Config._make_cflags = _split(self.makeCflagsEdit.text())

        # Associations — replace Bindings entirely from the table
        Bindings._db.clear()
        for row in range(self.assocTable.rowCount()):
            ext  = (self.assocTable.item(row, 0) or QtWidgets.QTableWidgetItem('')).text().strip()
            node = (self.assocTable.item(row, 1) or QtWidgets.QTableWidgetItem('')).text().strip()
            wdg  = (self.assocTable.item(row, 2) or QtWidgets.QTableWidgetItem('')).text().strip()
            if ext and node and wdg:
                Bindings.append(BindCatalogItem((ext, node, wdg)))

    def _apply(self):
        self._write_to_config()
        Config.saveConfigFile()
        self._initial_style = Config.APPEARANCE_STYLE
        self.settings_applied.emit()

    def _on_accept(self):
        self._accepted = True
        self._apply()
        self.accept()

    def _on_reject(self):
        self._revert_theme()
        self.reject()

    def closeEvent(self, event):
        if not self._accepted:
            self._revert_theme()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        win32_set_dark_titlebar(self, Config.APPEARANCE_STYLE != 'Classic')

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _preview_theme(self, theme_name):
        if theme_name:
            apply_gpi_theme(QtWidgets.QApplication.instance(), theme_name)

    def _revert_theme(self):
        apply_gpi_theme(QtWidgets.QApplication.instance(), self._initial_style)

    def _add_assoc_row(self):
        row = self.assocTable.rowCount()
        self.assocTable.insertRow(row)
        self.assocTable.setItem(row, 0, QtWidgets.QTableWidgetItem('.ext'))
        self.assocTable.setItem(row, 1, QtWidgets.QTableWidgetItem(''))
        self.assocTable.setItem(row, 2, QtWidgets.QTableWidgetItem('File Browser'))
        self.assocTable.scrollToBottom()
        self.assocTable.editItem(self.assocTable.item(row, 0))

    def _remove_assoc_row(self):
        rows = sorted({idx.row() for idx in self.assocTable.selectedIndexes()}, reverse=True)
        for r in rows:
            self.assocTable.removeRow(r)

    def _add_lib_path(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Node Library Directory"
        )
        if path:
            self.libPathList.addItem(path)

    def _remove_lib_path(self):
        row = self.libPathList.currentRow()
        if row >= 0:
            self.libPathList.takeItem(row)

    def _browse_dir(self, line_edit):
        start = line_edit.text() or os.path.expanduser('~')
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Directory", start
        )
        if path:
            line_edit.setText(path)
