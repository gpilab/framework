"""Dialog for scaffolding a new GPI node library on disk."""
import os
import re

from gpi import QtCore, QtGui, QtWidgets, VERSION
from .config import Config
from .logger import manager
from .theme import win32_set_dark_titlebar

log = manager.getLogger(__name__)

_VALID_ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _is_valid_id(name):
    return bool(_VALID_ID.match(name)) if name else False


class NewLibraryDialog(QtWidgets.QDialog):
    """Wizard-style dialog to scaffold a new GPI node library on disk."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Initialize GPI Library")
        self.setMinimumWidth(560)
        self.resize(620, 500)

        self._build_ui()
        self._connect_signals()
        self._update_preview()

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(20, 18, 20, 14)
        outer.setSpacing(12)

        note = QtWidgets.QLabel(
            "Create a new node library. GPI will scan it after creation. "
            "Names must be valid Python identifiers (letters, digits, underscores; no spaces)."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        outer.addWidget(note)

        form = QtWidgets.QFormLayout()
        form.setSpacing(10)

        # Base folder row
        base_row = QtWidgets.QWidget()
        base_h = QtWidgets.QHBoxLayout(base_row)
        base_h.setContentsMargins(0, 0, 0, 0)
        self.baseDirEdit = QtWidgets.QLineEdit()
        default_base = (Config.GPI_LIBRARY_PATH[0]
                        if Config.GPI_LIBRARY_PATH else os.path.expanduser('~'))
        self.baseDirEdit.setText(default_base)
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_btn.setFixedWidth(84)
        browse_btn.clicked.connect(self._browse_base)
        base_h.addWidget(self.baseDirEdit)
        base_h.addWidget(browse_btn)
        form.addRow("Base folder:", base_row)

        self.libNameEdit = QtWidgets.QLineEdit("mylib")
        form.addRow("Library name:", self.libNameEdit)

        self.catNameEdit = QtWidgets.QLineEdit("default")
        form.addRow("Category name:", self.catNameEdit)

        self.nodeNameEdit = QtWidgets.QLineEdit("MyNode")
        form.addRow("First node name:", self.nodeNameEdit)

        outer.addLayout(form)

        preview_label = QtWidgets.QLabel("Folder structure that will be created:")
        preview_label.setStyleSheet("font-weight: bold;")
        outer.addWidget(preview_label)

        self.previewText = QtWidgets.QTextEdit()
        self.previewText.setReadOnly(True)
        self.previewText.setMaximumHeight(130)
        font = QtGui.QFont("Courier New", 9)
        self.previewText.setFont(font)
        outer.addWidget(self.previewText)

        self.registerCheck = QtWidgets.QCheckBox(
            "Add base folder to GPI library paths (if not already registered)"
        )
        self.registerCheck.setChecked(True)
        outer.addWidget(self.registerCheck)

        self.statusLabel = QtWidgets.QLabel()
        self.statusLabel.setWordWrap(True)
        self.statusLabel.setStyleSheet("color: #e06060;")
        outer.addWidget(self.statusLabel)

        outer.addStretch()

        self.createBtn = QtWidgets.QPushButton("Create Library")
        self.createBtn.setDefault(True)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.createBtn.clicked.connect(self._create)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.createBtn)
        outer.addLayout(btn_row)

        self.setLayout(outer)

    def _connect_signals(self):
        self.baseDirEdit.textChanged.connect(self._update_preview)
        self.libNameEdit.textChanged.connect(self._update_preview)
        self.catNameEdit.textChanged.connect(self._update_preview)
        self.nodeNameEdit.textChanged.connect(self._update_preview)

    def _browse_base(self):
        start = self.baseDirEdit.text() or os.path.expanduser('~')
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Base Folder", start)
        if path:
            self.baseDirEdit.setText(os.path.normpath(path))

    def _get_inputs(self):
        return (
            self.baseDirEdit.text().strip(),
            self.libNameEdit.text().strip(),
            self.catNameEdit.text().strip(),
            self.nodeNameEdit.text().strip(),
        )

    def _validate(self):
        base, lib, cat, node = self._get_inputs()
        errors = []
        if not base:
            errors.append("Base folder is required.")
        if not _is_valid_id(lib):
            errors.append("Library name must be a valid Python identifier.")
        if not _is_valid_id(cat):
            errors.append("Category name must be a valid Python identifier.")
        if not _is_valid_id(node):
            errors.append("Node name must be a valid Python identifier.")
        return errors

    def _update_preview(self):
        base, lib, cat, node = self._get_inputs()
        errors = self._validate()
        if errors:
            self.statusLabel.setText("  ".join(errors))
            self.createBtn.setEnabled(False)
            self.previewText.setPlainText("")
            return

        self.statusLabel.setText("")
        self.createBtn.setEnabled(True)

        lines = [
            f"{base}/",
            f"└── {lib}/",
            f"    ├── __init__.py",
            f"    └── {cat}/",
            f"        ├── __init__.py",
            f"        └── GPI/",
            f"            └── {node}_GPI.py",
        ]
        self.previewText.setPlainText("\n".join(lines))

        already_registered = base in Config.GPI_LIBRARY_PATH
        self.registerCheck.setVisible(not already_registered)

    def _node_template(self, lib, cat, node):
        node_path = os.path.join(lib, cat, 'GPI', f'{node}_GPI.py')
        return (
            f"# GPI (v{VERSION}) auto-generated library file.\n"
            f"#\n"
            f"# FILE: {node_path}\n"
            f"#\n"
            f"# For node API examples (i.e. widgets and ports) look at the\n"
            f"# core.interfaces.Template node.\n"
            f"\n"
            f"import gpi\n"
            f"\n"
            f"\n"
            f"class ExternalNode(gpi.NodeAPI):\n"
            f"    '''About text goes here...\n"
            f"    '''\n"
            f"\n"
            f"    def initUI(self):\n"
            f"        # Widgets\n"
            f"        self.addWidget('PushButton', 'MyPushButton', toggle=True)\n"
            f"\n"
            f"        # IO Ports\n"
            f"        self.addInPort('in1', 'NPYarray')\n"
            f"        self.addOutPort('out1', 'NPYarray')\n"
            f"\n"
            f"        return 0\n"
            f"\n"
            f"    def compute(self):\n"
            f"\n"
            f"        data = self.getData('in1')\n"
            f"\n"
            f"        # algorithm code...\n"
            f"\n"
            f"        self.setData('out1', data)\n"
            f"\n"
            f"        return 0\n"
        )

    def _create(self):
        base, lib, cat, node = self._get_inputs()
        if self._validate():
            return

        lib_root = os.path.join(base, lib)
        cat_dir = os.path.join(lib_root, cat)
        gpi_dir = os.path.join(cat_dir, 'GPI')
        node_file = os.path.join(gpi_dir, f'{node}_GPI.py')
        lib_init = os.path.join(lib_root, '__init__.py')
        cat_init = os.path.join(cat_dir, '__init__.py')

        created = []
        skipped = []

        def make_dir(path):
            if os.path.exists(path):
                skipped.append(path)
            else:
                os.makedirs(path, exist_ok=True)
                created.append(path)

        def make_file(path, content=''):
            if os.path.exists(path):
                skipped.append(path)
            else:
                with open(path, 'w') as f:
                    f.write(content)
                created.append(path)

        try:
            make_dir(lib_root)
            make_dir(cat_dir)
            make_dir(gpi_dir)
            init_content = '# GPI auto-generated library file.\n'
            make_file(lib_init, init_content)
            make_file(cat_init, init_content)
            make_file(node_file, self._node_template(lib, cat, node))
        except OSError as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to create library:\n{e}")
            return

        if self.registerCheck.isVisible() and self.registerCheck.isChecked():
            if base not in Config.GPI_LIBRARY_PATH:
                Config._c_gpi_lib_path.append(base)
                Config.saveConfigFile()
                log.info(f"NewLibraryDialog: registered new library path: {base}")

        parts = []
        if created:
            parts.append("Created:\n" + "\n".join(f"  {p}" for p in created))
        if skipped:
            parts.append("Skipped (already exist):\n" + "\n".join(f"  {p}" for p in skipped))
        QtWidgets.QMessageBox.information(
            self, "Library Created",
            "Library scaffolded successfully!\n\n" + "\n\n".join(parts)
        )
        self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        win32_set_dark_titlebar(self, Config.APPEARANCE_STYLE != 'Classic')
