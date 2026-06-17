import os
import random
from gpi import QtCore, QtGui, QtWidgets, Signal
from .associate import Bindings, BindCatalogItem
from .config import Config
from .logger import manager
from .shortcuts import CANVAS_SHORTCUT_DEFAULTS, CanvasShortcuts
from .theme import apply_gpi_theme, win32_set_dark_titlebar

log = manager.getLogger(__name__)


class SettingsDialog(QtWidgets.QDialog):
    settings_applied = Signal()
    library_paths_changed = Signal()

    def __init__(self, parent=None, library=None, shortcuts=None, canvas_shortcuts=None):
        super().__init__(parent)
        self.setWindowTitle("GPI Settings")
        self.setMinimumSize(580, 400)
        self.resize(640, 580)

        self._initial_style = Config.APPEARANCE_STYLE
        self._accepted = False
        self._shortcuts = shortcuts              # node-deploy Shortcuts model
        self._canvas_shortcuts = canvas_shortcuts  # CanvasShortcuts model
        self._shortcut_rows = []                 # list of (key_edit, node_combo, row_widget)
        self._canvas_sc_key_edits = {}           # {action_id: QKeySequenceEdit}

        # Build sorted node key list from the live library for combo boxes.
        self._node_keys = []
        if library is not None:
            try:
                self._node_keys = sorted(library._known_GPI_nodes.keys(),
                                         key=lambda x: x.lower())
            except Exception:
                pass

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.tabBar().setUsesScrollButtons(True)
        self.tabWidget.setStyleSheet("""
            QTabBar QToolButton {
                background: #1a6496;
                border: 1px solid #0d4f7a;
                border-radius: 3px;
                min-width: 24px;
                min-height: 22px;
                padding: 0px 4px;
                color: white;
                font-weight: bold;
                font-size: 13px;
            }
            QTabBar QToolButton:hover {
                background: #2980b9;
                border-color: #1a6496;
            }
            QTabBar QToolButton:pressed {
                background: #145882;
            }
        """)
        self.tabWidget.addTab(self._create_appearance_tab(), "Appearance")
        self.tabWidget.addTab(self._create_paths_tab(), "Paths")
        self.tabWidget.addTab(self._create_build_tab(), "Build")
        self.tabWidget.addTab(self._create_associations_tab(), "Associations")
        self.tabWidget.addTab(self._create_shortcuts_tab(), "Shortcuts")

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok |
            QtWidgets.QDialogButtonBox.Cancel |
            QtWidgets.QDialogButtonBox.Apply
        )
        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self._on_reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self._apply)

        self._restoreDefaultsBtn = QtWidgets.QPushButton("Restore Defaults")
        self._restoreDefaultsBtn.setToolTip("Reset all settings to factory defaults")
        self._restoreDefaultsBtn.clicked.connect(self._restore_all_defaults)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self._restoreDefaultsBtn)
        btn_row.addStretch()
        btn_row.addWidget(self.buttonBox)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabWidget)
        layout.addLayout(btn_row)
        self.setLayout(layout)

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
        self.themeCombo.currentTextChanged.connect(self._update_layout_visibility)
        form.addRow("Theme:", self.themeCombo)

        self.layoutCombo = QtWidgets.QComboBox()
        self.layoutCombo.addItems(['Vertical', 'Horizontal'])
        form.addRow("Layout:", self.layoutCombo)
        self._appearance_form = form

        note = QtWidgets.QLabel(
            "Dark: modern dark Fusion theme (default).\n"
            "Classic: light standard Fusion appearance.\n"
            "Layout — Vertical: top-to-bottom flow (default).\n"
            "Layout — Horizontal: left-to-right flow; ports on node sides.\n"
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

    def _make_node_combo(self, current_value=''):
        """Return a searchable QComboBox pre-populated with all known nodes."""
        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.addItems(self._node_keys)
        idx = combo.findText(current_value, QtCore.Qt.MatchFixedString)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif current_value:
            # value from config not yet in library — add it so it's preserved
            combo.insertItem(0, current_value)
            combo.setCurrentIndex(0)
        completer = QtWidgets.QCompleter(self._node_keys, combo)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        try:
            completer.setFilterMode(QtCore.Qt.MatchContains)
        except AttributeError:
            pass
        combo.setCompleter(completer)
        return combo

    def _create_associations_tab(self):
        widget = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(20, 16, 20, 10)
        outer.setSpacing(10)

        note = QtWidgets.QLabel(
            "Map file extensions to nodes for drag-and-drop onto the canvas. "
            "Extension must include the dot (e.g. .npy). "
            "Select a node from the dropdown — type to filter by name."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        outer.addWidget(note)

        self.assocTable = QtWidgets.QTableWidget(0, 2)
        self.assocTable.setHorizontalHeaderLabels(["Extension", "Node"])
        hdr = self.assocTable.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.assocTable.verticalHeader().setDefaultSectionSize(28)
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

    # ── Shortcuts tab ─────────────────────────────────────────────────────────

    def _create_shortcuts_tab(self):
        widget = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(widget)
        outer.setContentsMargins(12, 12, 12, 8)
        outer.setSpacing(10)

        # ── Canvas shortcuts (editable) ────────────────────────────────────────
        canvas_group = QtWidgets.QGroupBox("Canvas Shortcuts")
        cg = QtWidgets.QVBoxLayout(canvas_group)
        cg.setContentsMargins(6, 8, 6, 8)
        cg.setSpacing(4)

        help_cs = QtWidgets.QLabel(
            "Click a key field then press the desired combination to reassign it."
        )
        help_cs.setWordWrap(True)
        help_cs.setStyleSheet("color: gray; font-size: 11px;")
        cg.addWidget(help_cs)

        cs_hdr = QtWidgets.QHBoxLayout()
        cs_hdr.addWidget(QtWidgets.QLabel("<b>Action</b>"), 1)
        cs_key_hdr = QtWidgets.QLabel(
            "<b>Key Combo</b> <span style='color:gray;font-weight:normal'>"
            "(click then press)</span>"
        )
        cs_key_hdr.setFixedWidth(210)
        cs_hdr.addWidget(cs_key_hdr)
        cg.addLayout(cs_hdr)

        self._canvas_sc_rows_widget = QtWidgets.QWidget()
        self._canvas_sc_rows_layout = QtWidgets.QVBoxLayout(self._canvas_sc_rows_widget)
        self._canvas_sc_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._canvas_sc_rows_layout.setSpacing(1)

        cs_scroll = QtWidgets.QScrollArea()
        cs_scroll.setWidget(self._canvas_sc_rows_widget)
        cs_scroll.setWidgetResizable(True)
        cs_scroll.setMinimumHeight(160)
        cs_scroll.setMaximumHeight(260)
        cs_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        cg.addWidget(cs_scroll)

        reset_btn = QtWidgets.QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_canvas_shortcuts)
        cg.addWidget(reset_btn, 0, QtCore.Qt.AlignLeft)

        outer.addWidget(canvas_group)

        # ── Node deploy shortcuts (editable) ──────────────────────────────────
        node_group = QtWidgets.QGroupBox("Node Deploy Shortcuts")
        ng = QtWidgets.QVBoxLayout(node_group)
        ng.setContentsMargins(6, 6, 6, 6)
        ng.setSpacing(6)

        help_lbl = QtWidgets.QLabel(
            "Assign a key combo to instantly place a node on the canvas.\n"
            "Tip: use Ctrl+Shift+<key> to avoid conflicts with canvas shortcuts."
        )
        help_lbl.setWordWrap(True)
        help_lbl.setStyleSheet("color: gray; font-size: 11px;")
        ng.addWidget(help_lbl)

        hdr = QtWidgets.QHBoxLayout()
        key_hdr = QtWidgets.QLabel(
            "<b>Key Combo</b> <span style='color:gray;font-weight:normal'>(click then press)</span>"
        )
        key_hdr.setFixedWidth(210)
        hdr.addWidget(key_hdr)
        hdr.addWidget(QtWidgets.QLabel("<b>Node</b>"))
        hdr.addSpacing(32)
        ng.addLayout(hdr)

        self._sc_rows_widget = QtWidgets.QWidget()
        self._sc_rows_layout = QtWidgets.QVBoxLayout(self._sc_rows_widget)
        self._sc_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._sc_rows_layout.setSpacing(3)
        self._sc_rows_layout.addStretch()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self._sc_rows_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(80)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        ng.addWidget(scroll, 1)

        add_btn = QtWidgets.QPushButton("+ Add Shortcut")
        add_btn.clicked.connect(lambda: self._add_shortcut_row())
        ng.addWidget(add_btn, 0, QtCore.Qt.AlignLeft)

        outer.addWidget(node_group, 1)
        return widget

    def _reload_canvas_shortcuts(self):
        """Populate canvas shortcut rows from the CanvasShortcuts model."""
        for i in reversed(range(self._canvas_sc_rows_layout.count())):
            item = self._canvas_sc_rows_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        self._canvas_sc_key_edits = {}

        if self._canvas_shortcuts is None:
            return

        for aid, label, seq in self._canvas_shortcuts.all_bindings():
            row_w = QtWidgets.QWidget()
            rl = QtWidgets.QHBoxLayout(row_w)
            rl.setContentsMargins(2, 1, 2, 1)
            rl.setSpacing(6)

            lbl = QtWidgets.QLabel(label)
            ks_edit = QtWidgets.QKeySequenceEdit()
            ks_edit.setFixedWidth(210)
            if seq:
                ks_edit.setKeySequence(QtGui.QKeySequence(seq))

            rl.addWidget(lbl, 1)
            rl.addWidget(ks_edit)
            self._canvas_sc_rows_layout.addWidget(row_w)
            self._canvas_sc_key_edits[aid] = ks_edit

    def _reset_canvas_shortcuts(self):
        if self._canvas_shortcuts is None:
            return
        self._canvas_shortcuts.reset_to_defaults()
        self._reload_canvas_shortcuts()

    def _add_shortcut_row(self, key='', node=''):
        row_w = QtWidgets.QWidget()
        rl = QtWidgets.QHBoxLayout(row_w)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)

        key_seq_edit = QtWidgets.QKeySequenceEdit()
        key_seq_edit.setFixedWidth(200)
        if key:
            key_seq_edit.setKeySequence(QtGui.QKeySequence(key))

        node_combo = self._make_node_combo(node)

        rm_btn = QtWidgets.QPushButton("✕")
        rm_btn.setFixedWidth(28)
        rm_btn.setFlat(True)
        entry = [None]  # mutable reference for the closure
        rm_btn.clicked.connect(lambda: self._remove_shortcut_row(row_w, entry[0]))

        rl.addWidget(key_seq_edit)
        rl.addWidget(node_combo, 1)
        rl.addWidget(rm_btn)

        insert_idx = self._sc_rows_layout.count() - 1
        self._sc_rows_layout.insertWidget(insert_idx, row_w)
        tup = (key_seq_edit, node_combo, row_w)
        entry[0] = tup
        self._shortcut_rows.append(tup)

    def _remove_shortcut_row(self, row_w, entry):
        row_w.setParent(None)
        if entry in self._shortcut_rows:
            self._shortcut_rows.remove(entry)

    def _reload_shortcuts(self):
        for _ke, _nc, rw in self._shortcut_rows:
            rw.setParent(None)
        self._shortcut_rows.clear()
        if self._shortcuts is not None:
            for key, node in self._shortcuts.parseShortcuts():
                self._add_shortcut_row(key, node)

    # ── Load / Save ──────────────────────────────────────────────────────────

    def _load_settings(self):
        # Appearance
        theme = Config.APPEARANCE_STYLE or 'Dark'
        idx = self.themeCombo.findText(theme)
        self.themeCombo.setCurrentIndex(idx if idx >= 0 else 0)

        layout_dir = Config.LAYOUT_DIRECTION or 'Vertical'
        idx = self.layoutCombo.findText(layout_dir)
        self.layoutCombo.setCurrentIndex(idx if idx >= 0 else 0)
        self._update_layout_visibility(theme)

        # Paths
        self.libPathList.clear()
        for p in Config.GPI_LIBRARY_PATH:
            self.libPathList.addItem(os.path.normpath(p))
        self.followCwdCheck.setChecked(Config.GPI_FOLLOW_CWD)
        self.netDirEdit.setText(os.path.normpath(Config.GPI_NET_PATH) if Config.GPI_NET_PATH else '')
        self.dataDirEdit.setText(os.path.normpath(Config.GPI_DATA_PATH) if Config.GPI_DATA_PATH else '')

        # Build
        self.makeLibsEdit.setText(os.pathsep.join(Config.MAKE_LIBS))
        self.makeLibDirsEdit.setText(os.pathsep.join(Config.MAKE_LIB_DIRS))
        self.makeIncDirsEdit.setText(os.pathsep.join(Config.MAKE_INC_DIRS))
        self.makeCflagsEdit.setText(os.pathsep.join(Config.MAKE_CFLAGS))

        # Associations
        self._reload_assoc_table()

        # Canvas shortcuts
        self._reload_canvas_shortcuts()

        # Node-deploy shortcuts
        self._reload_shortcuts()

    def _reload_assoc_table(self):
        self.assocTable.setRowCount(0)
        for key in sorted(Bindings.keys()):
            ext, node, _wdg = Bindings.get(key).asTuple()
            row = self.assocTable.rowCount()
            self.assocTable.insertRow(row)
            self.assocTable.setItem(row, 0, QtWidgets.QTableWidgetItem(ext))
            self.assocTable.setCellWidget(row, 1, self._make_node_combo(node))

    def _write_to_config(self):
        # Appearance
        Config._appearance_style = self.themeCombo.currentText()
        Config._layout_direction = self.layoutCombo.currentText()

        # Paths
        Config._c_gpi_lib_path = [
            os.path.normpath(self.libPathList.item(i).text())
            for i in range(self.libPathList.count())
        ]
        Config._c_gpi_follow_cwd = self.followCwdCheck.isChecked()
        Config._c_networkDir = os.path.normpath(self.netDirEdit.text()) if self.netDirEdit.text() else ''
        Config._c_dataDir = os.path.normpath(self.dataDirEdit.text()) if self.dataDirEdit.text() else ''

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
            ext_item = self.assocTable.item(row, 0)
            node_combo = self.assocTable.cellWidget(row, 1)
            ext = ext_item.text().strip() if ext_item else ''
            node = node_combo.currentText().strip() if node_combo else ''
            if ext and node:
                Bindings.append(BindCatalogItem((ext, node, 'File Browser')))

        # Canvas shortcuts — save configurable canvas bindings
        if self._canvas_shortcuts is not None and self._canvas_sc_key_edits:
            bindings = {}
            for aid, ks_edit in self._canvas_sc_key_edits.items():
                k = ks_edit.keySequence().toString(QtGui.QKeySequence.PortableText).strip()
                bindings[aid] = k
            self._canvas_shortcuts.save(bindings)

        # Node-deploy shortcuts
        if self._shortcuts is not None:
            pairs = []
            for key_seq_edit, node_combo, _rw in self._shortcut_rows:
                ks = key_seq_edit.keySequence()
                k = ks.toString(QtGui.QKeySequence.PortableText).strip()
                n = node_combo.currentText().strip()
                if k and n:
                    pairs.append((k, n))
            self._shortcuts.savePairs(pairs)

    def _restore_all_defaults(self):
        reply = QtWidgets.QMessageBox.question(
            self, "Restore Defaults",
            "Reset ALL settings to factory defaults?\n\n"
            "This will clear saved associations, shortcuts, paths, and appearance settings.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        Config.resetToDefaults()
        if self._canvas_shortcuts is not None:
            self._canvas_shortcuts.load()   # re-read now-empty overrides from Config
            self._canvas_shortcuts.changed.emit()
        if self._shortcuts is not None:
            self._shortcuts.shortcuts_changed.emit()
        self._load_settings()
        self.settings_applied.emit()

    def _apply(self):
        old_paths = set(Config.GPI_LIBRARY_PATH)
        self._write_to_config()
        Config.saveConfigFile()
        self._initial_style = Config.APPEARANCE_STYLE
        self.settings_applied.emit()
        if set(Config.GPI_LIBRARY_PATH) != old_paths:
            self.library_paths_changed.emit()

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

    def _update_layout_visibility(self, theme_name=None):
        if theme_name is None:
            theme_name = self.themeCombo.currentText()
        visible = (theme_name == 'Dark')
        self.layoutCombo.setVisible(visible)
        lbl = self._appearance_form.labelForField(self.layoutCombo)
        if lbl:
            lbl.setVisible(visible)

    def _preview_theme(self, theme_name):
        if theme_name:
            apply_gpi_theme(QtWidgets.QApplication.instance(), theme_name)

    def _revert_theme(self):
        apply_gpi_theme(QtWidgets.QApplication.instance(), self._initial_style)

    def _add_assoc_row(self):
        row = self.assocTable.rowCount()
        self.assocTable.insertRow(row)
        self.assocTable.setItem(row, 0, QtWidgets.QTableWidgetItem('.ext'))
        self.assocTable.setCellWidget(row, 1, self._make_node_combo(''))
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
            self.libPathList.addItem(os.path.normpath(path))

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
            line_edit.setText(os.path.normpath(path))
